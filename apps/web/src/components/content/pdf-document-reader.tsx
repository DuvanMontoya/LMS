'use client';

import { useEffect, useRef, useState } from 'react';

import type { PDFDocumentProxy } from 'pdfjs-dist';

const INITIAL_SCALE = 1;
const MIN_SCALE = 0.65;
const MAX_SCALE = 2.5;

function clampScale(value: number) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, Number(value.toFixed(2))));
}

function PdfPage({
  document,
  pageNumber,
  scale,
}: Readonly<{
  document: PDFDocumentProxy;
  pageNumber: number;
  scale: number;
}>) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let cancelled = false;
    let renderTask: { cancel: () => void; promise: Promise<void> } | null =
      null;

    async function render() {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const page = await document.getPage(pageNumber);
      if (cancelled) return;
      const viewport = page.getViewport({ scale });
      const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
      const context = canvas.getContext('2d', { alpha: false });
      if (!context) return;
      canvas.width = Math.ceil(viewport.width * pixelRatio);
      canvas.height = Math.ceil(viewport.height * pixelRatio);
      canvas.style.width = `${Math.ceil(viewport.width)}px`;
      canvas.style.height = `${Math.ceil(viewport.height)}px`;
      renderTask = page.render({
        canvas,
        canvasContext: context,
        transform: [pixelRatio, 0, 0, pixelRatio, 0, 0],
        viewport,
      });
      try {
        await renderTask.promise;
      } catch (error) {
        if (
          !cancelled &&
          !(
            error instanceof Error &&
            error.name === 'RenderingCancelledException'
          )
        ) {
          throw error;
        }
      }
    }

    void render();
    return () => {
      cancelled = true;
      renderTask?.cancel();
    };
  }, [document, pageNumber, scale]);

  return (
    <div className="flex min-h-32 justify-center px-3 py-3 sm:px-6 sm:py-5">
      <canvas
        aria-label={`Página ${pageNumber}`}
        className="max-w-none bg-white shadow-sm"
        ref={canvasRef}
      />
    </div>
  );
}

/** Canvas reader: no native-browser PDF chrome or embedded third-party frame. */
export function PdfDocumentReader({
  onError,
  source,
  title,
}: Readonly<{
  onError?: () => void;
  source: string;
  title: string;
}>) {
  const [document, setDocument] = useState<PDFDocumentProxy | null>(null);
  const [failed, setFailed] = useState(false);
  const [scale, setScale] = useState(INITIAL_SCALE);

  useEffect(() => {
    let active = true;
    let destroyLoadingTask: (() => Promise<void>) | null = null;

    async function load() {
      try {
        const pdfjs = await import('pdfjs-dist');
        pdfjs.GlobalWorkerOptions.workerSrc =
          '/vendor/pdfjs/pdf.worker.min.mjs';
        const task = pdfjs.getDocument({
          disableAutoFetch: false,
          disableStream: false,
          url: source,
          withCredentials: false,
        });
        destroyLoadingTask = () => task.destroy();
        const loadedDocument = await task.promise;
        if (!active) {
          await destroyLoadingTask();
          return;
        }
        setDocument(loadedDocument);
      } catch {
        if (!active) return;
        setFailed(true);
        onError?.();
      }
    }

    void load();
    return () => {
      active = false;
      void destroyLoadingTask?.();
    };
  }, [onError, source]);

  return (
    <section
      aria-busy={!document && !failed}
      aria-label={title}
      className="pdf-document-reader"
      onWheel={(event) => {
        if (!event.ctrlKey && !event.metaKey) return;
        event.preventDefault();
        setScale((current) =>
          clampScale(current + (event.deltaY < 0 ? 0.1 : -0.1)),
        );
      }}
      tabIndex={0}
    >
      {!document && !failed ? (
        <div aria-hidden="true" className="pdf-document-reader__skeleton" />
      ) : null}
      {document ? (
        <div className="pdf-document-reader__pages">
          {Array.from({ length: document.numPages }, (_, index) => (
            <PdfPage
              document={document}
              key={`${document.fingerprints[0]}-${index + 1}-${scale}`}
              pageNumber={index + 1}
              scale={scale}
            />
          ))}
        </div>
      ) : null}
      {failed ? (
        <p className="p-5 text-sm text-destructive" role="alert">
          No fue posible mostrar este documento.
        </p>
      ) : null}
      <span aria-live="polite" className="sr-only">
        {document
          ? `Documento de ${document.numPages} páginas. Zoom ${Math.round(scale * 100)} por ciento.`
          : ''}
      </span>
    </section>
  );
}
