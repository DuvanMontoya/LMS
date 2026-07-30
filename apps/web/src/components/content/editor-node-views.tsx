'use client';

import { NodeViewWrapper, type ReactNodeViewProps } from '@tiptap/react';

import { CodeMirrorField } from './code-mirror-field';
import { MathJaxFormula } from './mathjax-formula';

export function AcademicCodeNodeView({
  node,
  updateAttributes,
}: ReactNodeViewProps) {
  return (
    <NodeViewWrapper className="my-4 rounded-xl border border-slate-300 bg-slate-50 p-3">
      <div className="mb-2 flex flex-wrap items-center gap-3">
        <label className="text-sm font-medium">
          Lenguaje
          <select
            className="ml-2 rounded border bg-white px-2 py-1"
            onChange={(event) =>
              updateAttributes({ language: event.target.value })
            }
            value={String(node.attrs.language)}
          >
            {[
              'plaintext',
              'python',
              'javascript',
              'typescript',
              'json',
              'sql',
              'latex',
            ].map((language) => (
              <option key={language} value={language}>
                {language}
              </option>
            ))}
          </select>
        </label>
        <label className="min-w-52 flex-1 text-sm font-medium">
          Descripción opcional
          <input
            className="ml-2 rounded border bg-white px-2 py-1"
            maxLength={300}
            onChange={(event) =>
              updateAttributes({ caption: event.target.value || null })
            }
            value={String(node.attrs.caption ?? '')}
          />
        </label>
      </div>
      <CodeMirrorField
        ariaLabel="Código académico"
        code={String(node.attrs.code)}
        language={String(node.attrs.language)}
        onChange={(code) => updateAttributes({ code })}
      />
    </NodeViewWrapper>
  );
}

export function InlineMathNodeView({ node }: ReactNodeViewProps) {
  return (
    <NodeViewWrapper as="span" className="rounded bg-sky-50 px-1">
      <MathJaxFormula latex={String(node.attrs.latex)} />
    </NodeViewWrapper>
  );
}

export function DisplayMathNodeView({ node }: ReactNodeViewProps) {
  return (
    <NodeViewWrapper className="my-4 rounded-lg border border-slate-200 p-3">
      <MathJaxFormula display latex={String(node.attrs.latex)} />
      {node.attrs.label ? (
        <p className="text-center text-sm text-slate-600">
          {String(node.attrs.label)}
        </p>
      ) : null}
    </NodeViewWrapper>
  );
}
