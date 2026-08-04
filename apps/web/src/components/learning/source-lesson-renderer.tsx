'use client';

import { AlertTriangle, Download, FileCode2, FileText } from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import Markdown, { type Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';

import { LatexText } from '@/components/content/latex-text';
import { MathJaxFormula } from '@/components/content/mathjax-formula';
import { Button } from '@/components/ui/button';
import type { AssetAccessDescriptor } from '@/lib/assets/api';
import { formatBytes } from '@/lib/assets/labels';
import { parseLatexLesson } from '@/lib/content/source-document';

const MAX_SOURCE_BYTES = 10 * 1024 * 1024;

const markdownComponents: Components = {
  a: ({ children, ...props }) => (
    <a {...props} rel="noreferrer" target="_blank">
      {children}
    </a>
  ),
  code: ({ children, className, ...props }) => {
    const latex = String(children).replace(/\n$/, '');
    if (className?.includes('math-display'))
      return <MathJaxFormula display latex={latex} />;
    if (className?.includes('math-inline'))
      return <MathJaxFormula latex={latex} />;
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  img: ({ alt }) => (
    <span className="rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground">
      Imagen referenciada en Markdown: {alt || 'sin texto alternativo'}
    </span>
  ),
  pre: ({ children }) => <div className="my-5 overflow-x-auto">{children}</div>,
};

function sourceItem(descriptor: AssetAccessDescriptor) {
  return descriptor.source;
}

function LatexLesson({ source }: Readonly<{ source: string }>) {
  const document = useMemo(() => parseLatexLesson(source), [source]);
  return (
    <article className="mx-auto max-w-4xl px-5 py-8 sm:px-8 sm:py-12">
      {document.title ? (
        <header className="mb-10 border-b pb-7">
          <p className="text-xs font-semibold tracking-[0.18em] text-primary uppercase">
            Documento LaTeX
          </p>
          <h2 className="mt-3 text-3xl leading-tight font-semibold tracking-tight text-balance sm:text-4xl">
            {document.title}
          </h2>
          {document.author || document.date ? (
            <p className="mt-3 text-sm text-muted-foreground">
              {[document.author, document.date].filter(Boolean).join(' · ')}
            </p>
          ) : null}
        </header>
      ) : null}
      <div className="space-y-5 text-[1.02rem] leading-8 text-foreground/90">
        {document.blocks.map((block, index) => {
          const key = `${block.type}-${index}`;
          if (block.type === 'heading') {
            const classes =
              block.level <= 2
                ? 'mt-12 border-b pb-3 text-2xl font-semibold tracking-tight text-foreground'
                : block.level === 3
                  ? 'mt-9 text-xl font-semibold text-foreground'
                  : 'mt-7 rounded-lg border-l-4 border-primary bg-primary/5 px-4 py-3 text-base font-semibold text-foreground';
            const Heading =
              block.level <= 2 ? 'h2' : block.level === 3 ? 'h3' : 'h4';
            return (
              <Heading className={classes} key={key}>
                {block.text}
              </Heading>
            );
          }
          if (block.type === 'math')
            return (
              <div
                className="my-7 overflow-x-auto rounded-xl border bg-muted/15 px-4 py-5"
                key={key}
              >
                <MathJaxFormula display latex={block.latex} />
              </div>
            );
          if (block.type === 'list') {
            const List = block.ordered ? 'ol' : 'ul';
            return (
              <List className="ml-6 space-y-2 marker:text-primary" key={key}>
                {block.items.map((item, itemIndex) => (
                  <li
                    className={block.ordered ? 'list-decimal' : 'list-disc'}
                    key={`${key}-${itemIndex}`}
                  >
                    <LatexText value={item} />
                  </li>
                ))}
              </List>
            );
          }
          if (block.type === 'table')
            return (
              <div className="my-7 overflow-x-auto rounded-xl border" key={key}>
                <table className="w-full min-w-[36rem] border-collapse text-left text-sm leading-6">
                  <tbody>
                    {block.rows.map((row, rowIndex) => (
                      <tr
                        className={rowIndex ? 'border-t' : 'bg-muted/35'}
                        key={`${key}-${rowIndex}`}
                      >
                        {row.map((cell, cellIndex) => {
                          const Cell = rowIndex ? 'td' : 'th';
                          return (
                            <Cell
                              className="border-r px-3 py-2.5 align-top last:border-r-0"
                              key={`${key}-${rowIndex}-${cellIndex}`}
                              scope={rowIndex ? undefined : 'col'}
                            >
                              <LatexText value={cell} />
                            </Cell>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            );
          if (block.type === 'code')
            return (
              <figure className="my-7" key={key}>
                {block.caption ? (
                  <figcaption className="mb-2 text-sm font-medium text-muted-foreground">
                    {block.caption}
                  </figcaption>
                ) : null}
                <pre className="overflow-x-auto rounded-xl bg-slate-950 p-5 text-sm leading-6 text-slate-100">
                  <code data-language={block.language}>{block.code}</code>
                </pre>
              </figure>
            );
          if (block.type === 'visual')
            return (
              <aside
                className="my-7 flex gap-3 rounded-xl border border-amber-300/60 bg-amber-50 p-4 text-sm leading-6 text-amber-950"
                key={key}
              >
                <AlertTriangle className="mt-0.5 size-4 shrink-0" />
                <div>
                  <p className="font-semibold">
                    Gráfico definido por la fuente
                  </p>
                  <p>{block.caption}</p>
                  <p className="mt-1 text-amber-800">
                    Se conserva en el archivo original; esta vista web no
                    ejecuta ni compila TikZ.
                  </p>
                </div>
              </aside>
            );
          return (
            <p className="text-pretty" key={key}>
              <LatexText value={block.text} />
            </p>
          );
        })}
      </div>
    </article>
  );
}

function MarkdownLesson({ source }: Readonly<{ source: string }>) {
  return (
    <article className="source-markdown mx-auto max-w-4xl px-5 py-8 text-[1.02rem] leading-8 sm:px-8 sm:py-12 [&_a]:font-medium [&_a]:text-primary [&_a]:underline-offset-4 [&_a:hover]:underline [&_blockquote]:my-6 [&_blockquote]:border-l-4 [&_blockquote]:border-primary/40 [&_blockquote]:bg-muted/30 [&_blockquote]:px-5 [&_blockquote]:py-3 [&_h1]:mt-2 [&_h1]:mb-8 [&_h1]:text-4xl [&_h1]:font-semibold [&_h1]:tracking-tight [&_h2]:mt-12 [&_h2]:mb-4 [&_h2]:border-b [&_h2]:pb-3 [&_h2]:text-2xl [&_h2]:font-semibold [&_h3]:mt-9 [&_h3]:mb-3 [&_h3]:text-xl [&_h3]:font-semibold [&_hr]:my-10 [&_li]:my-1 [&_ol]:my-5 [&_ol]:ml-7 [&_ol]:list-decimal [&_p]:my-5 [&_pre_code]:block [&_pre_code]:min-w-max [&_pre_code]:rounded-xl [&_pre_code]:bg-slate-950 [&_pre_code]:p-5 [&_pre_code]:text-sm [&_pre_code]:leading-6 [&_pre_code]:text-slate-100 [&_strong]:font-semibold [&_table]:my-7 [&_table]:w-full [&_table]:border-collapse [&_td]:border [&_td]:p-3 [&_th]:border [&_th]:bg-muted/50 [&_th]:p-3 [&_ul]:my-5 [&_ul]:ml-7 [&_ul]:list-disc">
      <Markdown
        components={markdownComponents}
        remarkPlugins={[remarkGfm, remarkMath]}
        skipHtml
      >
        {source}
      </Markdown>
    </article>
  );
}

export function SourceLessonRenderer({
  descriptor,
  lessonKind,
  title,
}: Readonly<{
  descriptor: AssetAccessDescriptor;
  lessonKind: 'latex_source' | 'markdown_source';
  title: string;
}>) {
  const source = sourceItem(descriptor);
  const [text, setText] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    async function load() {
      if (!source || source.size_bytes > MAX_SOURCE_BYTES) {
        setError('El archivo fuente no cumple el límite de lectura de 10 MiB.');
        setLoading(false);
        return;
      }
      try {
        const response = await fetch(source.url, {
          cache: 'no-store',
          signal: controller.signal,
        });
        if (!response.ok) throw new Error('source_unavailable');
        const body = await response.text();
        if (new Blob([body]).size > MAX_SOURCE_BYTES)
          throw new Error('source_too_large');
        setText(body);
      } catch (cause) {
        if (!controller.signal.aborted) {
          setError(
            cause instanceof Error && cause.message === 'source_too_large'
              ? 'El archivo fuente supera el límite de lectura de 10 MiB.'
              : 'No fue posible leer el archivo privado para mostrar esta lección.',
          );
        }
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void load();
    return () => controller.abort();
  }, [source]);

  if (!source)
    return <p role="alert">La fuente no tiene una versión entregable.</p>;
  return (
    <section
      className="overflow-hidden rounded-2xl border bg-card shadow-sm"
      aria-busy={loading}
    >
      <header className="flex flex-wrap items-center justify-between gap-4 border-b bg-muted/20 px-5 py-4 sm:px-7">
        <div className="flex min-w-0 items-center gap-3">
          <div className="rounded-lg border bg-background p-2 text-primary">
            {lessonKind === 'latex_source' ? (
              <FileCode2 className="size-4" />
            ) : (
              <FileText className="size-4" />
            )}
          </div>
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold">{title}</p>
            <p className="text-xs text-muted-foreground">
              {lessonKind === 'latex_source'
                ? 'Vista web LaTeX'
                : 'Markdown renderizado'}{' '}
              · {formatBytes(source.size_bytes)}
            </p>
          </div>
        </div>
        <Button asChild size="sm" variant="outline">
          <a download href={source.url}>
            <Download data-icon="inline-start" />
            Descargar fuente
          </a>
        </Button>
      </header>
      {loading ? (
        <div className="p-10 text-center text-sm text-muted-foreground">
          Preparando la lectura…
        </div>
      ) : error ? (
        <div
          className="m-5 rounded-xl border border-destructive/20 bg-destructive/5 p-4 text-sm text-destructive"
          role="alert"
        >
          {error}
        </div>
      ) : lessonKind === 'latex_source' ? (
        <LatexLesson source={text} />
      ) : (
        <MarkdownLesson source={text} />
      )}
    </section>
  );
}
