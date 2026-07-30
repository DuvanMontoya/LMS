import type { JSONContent } from '@tiptap/core';
import { renderToReactElement } from '@tiptap/static-renderer/pm/react';
import type { ReactNode } from 'react';

import { contentEditorExtensions } from '@/lib/content/editor/extensions';
import type { LMSUnitAcademicDocumentVersion1 } from '@/lib/content/generated/unit-document-v1';
import { safeContentHref } from '@/lib/content/schema/validator';

import { CopyCodeButton } from './copy-code-button';
import { MathJaxFormula } from './mathjax-formula';

const pedagogicalLabels: Record<string, string> = {
  corollary: 'Corolario',
  counterexample: 'Contraejemplo',
  definition: 'Definición',
  example: 'Ejemplo',
  lemma: 'Lema',
  proof: 'Demostración',
  proposition: 'Proposición',
  remark: 'Observación',
  summary: 'Resumen',
  theorem: 'Teorema',
  warning: 'Advertencia',
};

function semanticNodeProps(node: { attrs: Record<string, unknown> }) {
  const nodeId =
    typeof node.attrs.nodeId === 'string' ? node.attrs.nodeId : undefined;
  return nodeId ? { 'data-node-id': nodeId, id: `node-${nodeId}` } : undefined;
}

export function AcademicDocument({
  document,
}: Readonly<{ document: LMSUnitAcademicDocumentVersion1 }>) {
  return (
    <article className="academic-document" data-testid="academic-document">
      {renderToReactElement({
        content: document as JSONContent,
        extensions: contentEditorExtensions,
        options: {
          markMapping: {
            bold: ({ children }) => <strong>{children}</strong>,
            code: ({ children }) => (
              <code className="rounded bg-slate-100 px-1 py-0.5">
                {children}
              </code>
            ),
            italic: ({ children }) => <em>{children}</em>,
            link: ({ children, mark }) => {
              const href = safeContentHref(mark.attrs.href)
                ? mark.attrs.href
                : undefined;
              return href ? (
                <a
                  className="text-sky-700 underline underline-offset-2"
                  href={href}
                  rel="noopener noreferrer"
                >
                  {children}
                </a>
              ) : (
                <span>{children}</span>
              );
            },
          },
          nodeMapping: {
            blockquote: ({ children, node }) => (
              <blockquote
                {...semanticNodeProps(node)}
                className="border-l-4 border-slate-300 pl-4 text-slate-700"
              >
                {children}
              </blockquote>
            ),
            bulletList: ({ children, node }) => (
              <ul
                {...semanticNodeProps(node)}
                className="list-disc space-y-1 pl-6"
              >
                {children}
              </ul>
            ),
            codeBlock: ({ node }) => {
              const code = String(node.attrs.code ?? '');
              const caption =
                typeof node.attrs.caption === 'string'
                  ? node.attrs.caption
                  : undefined;
              return (
                <figure
                  {...semanticNodeProps(node)}
                  className="overflow-hidden rounded-xl border border-slate-700 bg-slate-950 text-slate-100"
                >
                  <div className="flex items-center justify-between gap-3 border-b border-slate-700 px-4 py-2">
                    <figcaption className="text-sm text-slate-300">
                      {caption || String(node.attrs.language)}
                    </figcaption>
                    <CopyCodeButton code={code} />
                  </div>
                  <pre className="overflow-x-auto p-4 text-sm">
                    <code>{code}</code>
                  </pre>
                </figure>
              );
            },
            displayMath: ({ node }) => (
              <figure
                {...semanticNodeProps(node)}
                className="rounded-lg border border-slate-200 bg-white px-4 py-2"
              >
                <MathJaxFormula
                  display
                  latex={String(node.attrs.latex ?? '')}
                />
                {node.attrs.label ? (
                  <figcaption className="text-center text-sm text-slate-500">
                    {String(node.attrs.label)}
                  </figcaption>
                ) : null}
              </figure>
            ),
            hardBreak: () => <br />,
            heading: ({ children, node }) => {
              const level = Number(node.attrs.level);
              if (level === 2)
                return (
                  <h2
                    {...semanticNodeProps(node)}
                    className="text-2xl font-semibold"
                    tabIndex={-1}
                  >
                    {children}
                  </h2>
                );
              if (level === 3)
                return (
                  <h3
                    {...semanticNodeProps(node)}
                    className="text-xl font-semibold"
                    tabIndex={-1}
                  >
                    {children}
                  </h3>
                );
              return (
                <h4
                  {...semanticNodeProps(node)}
                  className="text-lg font-semibold"
                  tabIndex={-1}
                >
                  {children}
                </h4>
              );
            },
            horizontalRule: () => <hr className="border-slate-300" />,
            inlineMath: ({ node }) => (
              <MathJaxFormula latex={String(node.attrs.latex ?? '')} />
            ),
            listItem: ({ children }) => <li>{children}</li>,
            orderedList: ({ children, node }) => (
              <ol
                {...semanticNodeProps(node)}
                className="list-decimal space-y-1 pl-6"
                start={Number(node.attrs.start ?? 1)}
              >
                {children}
              </ol>
            ),
            paragraph: ({ children, node }) => (
              <p
                {...semanticNodeProps(node)}
                className="leading-7 text-slate-800"
                tabIndex={-1}
              >
                {children}
              </p>
            ),
            pedagogicalBlock: ({ children, node }) => {
              const kind = String(node.attrs.kind);
              const title =
                typeof node.attrs.title === 'string'
                  ? node.attrs.title
                  : undefined;
              return (
                <aside
                  {...semanticNodeProps(node)}
                  className="rounded-xl border-l-4 border-sky-600 bg-sky-50 p-4"
                  data-pedagogical-kind={kind}
                >
                  <p className="font-semibold text-sky-950">
                    {title || pedagogicalLabels[kind] || kind}
                  </p>
                  <div className="mt-2 space-y-3">{children}</div>
                </aside>
              );
            },
            table: ({ children, node }) => (
              <figure {...semanticNodeProps(node)} className="overflow-x-auto">
                <table className="w-full border-collapse text-left">
                  {children}
                </table>
                {node.attrs.caption ? (
                  <figcaption className="mt-2 text-sm text-slate-600">
                    {String(node.attrs.caption)}
                  </figcaption>
                ) : null}
              </figure>
            ),
            tableCell: ({ children }) => (
              <td className="border border-slate-300 p-2 align-top">
                {children}
              </td>
            ),
            tableHeader: ({ children }) => (
              <th
                className="border border-slate-300 bg-slate-100 p-2 align-top font-semibold"
                scope="col"
              >
                {children}
              </th>
            ),
            tableRow: ({ children, node }) =>
              node.firstChild?.type.name === 'tableHeader' ? (
                <thead>
                  <tr>{children}</tr>
                </thead>
              ) : (
                <tbody>
                  <tr>{children}</tr>
                </tbody>
              ),
          },
          unhandledMark: ({ children }) => children as ReactNode,
          unhandledNode: ({ node }) => (
            <p role="alert">
              No es posible representar el nodo «{node.type.name}».
            </p>
          ),
        },
      })}
    </article>
  );
}
