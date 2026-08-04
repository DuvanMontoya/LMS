'use client';

import { FileText, Minus, Plus, RotateCcw } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';

import type { PDFDocumentProxy } from 'pdfjs-dist';

const INITIAL_SCALE = 1;
const MIN_SCALE = 0.65;
const MAX_SCALE = 2.5;

function clampScale(value: number) {
  return Math.min(MAX_SCALE, Math.max(MIN_SCALE, Number(value.toFixed(2))));
}

export function isExpectedPdfCancellation(error: unknown) {
  return (
    error instanceof Error &&
    (error.name === 'AbortError' ||
      error.name === 'RenderingCancelledException')
  );
}

export function pdfRenderScale(
  naturalWidth: number,
  availableWidth: number,
  zoom: number,
) {
  if (naturalWidth <= 0 || availableWidth <= 0) return zoom;
  return Math.min(1, availableWidth / naturalWidth) * zoom;
}

function PdfPage({
  document,
  availableWidth,
  pageNumber,
  scale,
  onError,
}: Readonly<{
  document: PDFDocumentProxy;
  availableWidth: number;
  onError: () => void;
  pageNumber: number;
  scale: number;
}>) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  const [nearViewport, setNearViewport] = useState(
    () =>
      typeof window !== 'undefined' &&
      typeof window.IntersectionObserver === 'undefined',
  );
  const [renderedHeight, setRenderedHeight] = useState<number | null>(null);

  useEffect(() => {
    const page = pageRef.current;
    if (!page) return;
    if (typeof IntersectionObserver === 'undefined') return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (!entries.some((entry) => entry.isIntersecting)) return;
        setNearViewport(true);
        observer.disconnect();
      },
      { rootMargin: '1000px 0px' },
    );
    observer.observe(page);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!nearViewport) return;
    let cancelled = false;
    let renderTask: { cancel: () => void; promise: Promise<void> } | null =
      null;

    async function render() {
      try {
        const canvas = canvasRef.current;
        if (!canvas) return;
        const page = await document.getPage(pageNumber);
        if (cancelled) return;
        const naturalViewport = page.getViewport({ scale: 1 });
        const viewport = page.getViewport({
          scale: pdfRenderScale(naturalViewport.width, availableWidth, scale),
        });
        const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
        const context = canvas.getContext('2d', { alpha: false });
        if (!context) return;
        canvas.width = Math.ceil(viewport.width * pixelRatio);
        canvas.height = Math.ceil(viewport.height * pixelRatio);
        canvas.style.width = `${Math.ceil(viewport.width)}px`;
        canvas.style.height = `${Math.ceil(viewport.height)}px`;
        setRenderedHeight(Math.ceil(viewport.height));
        renderTask = page.render({
          canvas,
          canvasContext: context,
          transform: [pixelRatio, 0, 0, pixelRatio, 0, 0],
          viewport,
        });
        await renderTask.promise;
      } catch (error) {
        if (cancelled || isExpectedPdfCancellation(error)) return;
        onError();
      }
    }

    void render();
    return () => {
      cancelled = true;
      renderTask?.cancel();
    };
  }, [availableWidth, document, nearViewport, onError, pageNumber, scale]);

  return (
    <div
      aria-label={`Página ${pageNumber}`}
      className="flex justify-center px-3 py-3 sm:px-6 sm:py-5"
      ref={pageRef}
      style={{
        minHeight:
          renderedHeight === null
            ? Math.max(160, Math.round(availableWidth * 1.36 * scale))
            : renderedHeight,
      }}
    >
      {nearViewport ? (
        <canvas
          aria-label={`Contenido de la página ${pageNumber}`}
          className="max-w-none bg-white shadow-sm"
          ref={canvasRef}
        />
      ) : (
        <div
          aria-hidden="true"
          className="pdf-document-reader__page-skeleton"
        />
      )}
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
  const [availableWidth, setAvailableWidth] = useState(0);
  const pagesRef = useRef<HTMLDivElement>(null);
  const handleError = useCallback(() => {
    setFailed(true);
    onError?.();
  }, [onError]);

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
      void destroyLoadingTask?.().catch(() => undefined);
    };
  }, [onError, source]);

  useEffect(() => {
    const pages = pagesRef.current;
    if (!pages || !document) return;

    const measure = () => {
      const horizontalPadding = window.matchMedia('(min-width: 640px)').matches
        ? 48
        : 24;
      const nextWidth = Math.max(
        1,
        Math.floor(pages.clientWidth - horizontalPadding),
      );
      setAvailableWidth((current) =>
        current === nextWidth ? current : nextWidth,
      );
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(pages);
    return () => observer.disconnect();
  }, [document]);

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
      {document && !failed ? (
        <>
          <header className="pdf-document-reader__toolbar">
            <div>
              <FileText />
              <span>
                <strong>{title}</strong>
                <small>
                  {document.numPages}{' '}
                  {document.numPages === 1 ? 'página' : 'páginas'}
                </small>
              </span>
            </div>
            <div aria-label="Zoom del documento" role="group">
              <Button
                aria-label="Reducir zoom"
                disabled={scale <= MIN_SCALE}
                onClick={() => setScale((current) => clampScale(current - 0.1))}
                size="icon-sm"
                type="button"
                variant="ghost"
              >
                <Minus />
              </Button>
              <span aria-live="polite">{Math.round(scale * 100)} %</span>
              <Button
                aria-label="Aumentar zoom"
                disabled={scale >= MAX_SCALE}
                onClick={() => setScale((current) => clampScale(current + 0.1))}
                size="icon-sm"
                type="button"
                variant="ghost"
              >
                <Plus />
              </Button>
              <Button
                aria-label="Restablecer zoom"
                disabled={scale === INITIAL_SCALE}
                onClick={() => setScale(INITIAL_SCALE)}
                size="icon-sm"
                type="button"
                variant="ghost"
              >
                <RotateCcw />
              </Button>
            </div>
          </header>
          <div className="pdf-document-reader__pages" ref={pagesRef}>
            {availableWidth > 0
              ? Array.from({ length: document.numPages }, (_, index) => (
                  <PdfPage
                    availableWidth={availableWidth}
                    document={document}
                    key={`${document.fingerprints[0]}-${index + 1}-${scale}-${availableWidth}`}
                    onError={handleError}
                    pageNumber={index + 1}
                    scale={scale}
                  />
                ))
              : null}
          </div>
        </>
      ) : null}
      {failed ? (
        <p className="p-5 text-sm text-destructive" role="alert">
          No fue posible mostrar este documento.
        </p>
      ) : null}
      <span aria-live="polite" className="sr-only">
        {document
          ? `Documento de ${document.numPages} páginas. Ajustado al ancho disponible. Zoom ${Math.round(scale * 100)} por ciento.`
          : ''}
      </span>
    </section>
  );
}
