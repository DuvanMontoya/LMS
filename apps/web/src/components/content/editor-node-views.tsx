'use client';

import { NodeViewWrapper, type ReactNodeViewProps } from '@tiptap/react';

import { CodeMirrorField } from './code-mirror-field';
import { MathJaxFormula } from './mathjax-formula';

export function AssetNodeView({
  deleteNode,
  node,
  updateAttributes,
}: ReactNodeViewProps) {
  const type = node.type.name;
  const image = type === 'imageAsset';
  const audio = type === 'audioAsset';
  const video = type === 'videoAsset';
  const download = type === 'documentAsset' || type === 'datasetAsset';
  const decorative = Boolean(node.attrs.decorative);
  return (
    <NodeViewWrapper className="my-4 rounded-lg border border-sky-200 bg-sky-50/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="font-semibold">
            {image
              ? 'Imagen'
              : audio
                ? 'Audio'
                : video
                  ? 'Video'
                  : type === 'documentAsset'
                    ? 'Documento'
                    : 'Dataset'}
          </p>
          <p className="font-mono text-xs text-muted-foreground">
            Versión fijada: {String(node.attrs.assetVersionId)}
          </p>
        </div>
        <button
          className="rounded border bg-background px-2 py-1 text-xs"
          onClick={deleteNode}
          type="button"
        >
          Quitar
        </button>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-2">
        {(audio || video) && (
          <label className="text-sm font-medium">
            Título
            <input
              className="mt-1 block w-full rounded border bg-background px-2 py-1.5"
              maxLength={300}
              onChange={(event) =>
                updateAttributes({ title: event.target.value })
              }
              value={String(node.attrs.title ?? '')}
            />
          </label>
        )}
        {download && (
          <label className="text-sm font-medium">
            Texto del enlace
            <input
              className="mt-1 block w-full rounded border bg-background px-2 py-1.5"
              maxLength={300}
              onChange={(event) =>
                updateAttributes({ label: event.target.value })
              }
              value={String(node.attrs.label ?? '')}
            />
          </label>
        )}
        {image && (
          <>
            <label className="flex items-center gap-2 text-sm font-medium">
              <input
                checked={decorative}
                onChange={(event) =>
                  updateAttributes({
                    altText: event.target.checked ? '' : node.attrs.altText,
                    decorative: event.target.checked,
                  })
                }
                type="checkbox"
              />
              Imagen decorativa
            </label>
            <label className="text-sm font-medium">
              Texto alternativo
              <input
                className="mt-1 block w-full rounded border bg-background px-2 py-1.5"
                disabled={decorative}
                maxLength={500}
                onChange={(event) =>
                  updateAttributes({ altText: event.target.value })
                }
                value={String(node.attrs.altText ?? '')}
              />
            </label>
          </>
        )}
        {(audio || video) && (
          <label className="text-sm font-medium sm:col-span-2">
            Transcripción
            <textarea
              className="mt-1 block min-h-24 w-full rounded border bg-background px-2 py-1.5"
              maxLength={100000}
              onChange={(event) =>
                updateAttributes({ transcript: event.target.value })
              }
              value={String(node.attrs.transcript ?? '')}
            />
          </label>
        )}
        {video && (
          <>
            <label className="flex items-center gap-2 text-sm font-medium">
              <input
                checked={Boolean(node.attrs.silent)}
                onChange={(event) =>
                  updateAttributes({ silent: event.target.checked })
                }
                type="checkbox"
              />
              Video sin audio
            </label>
            {!node.attrs.silent ? (
              <label className="text-sm font-medium">
                ID de versión WebVTT
                <input
                  className="mt-1 block w-full rounded border bg-background px-2 py-1.5 font-mono text-xs"
                  onChange={(event) =>
                    updateAttributes({
                      captionsAssetVersionId: event.target.value || null,
                    })
                  }
                  value={String(node.attrs.captionsAssetVersionId ?? '')}
                />
              </label>
            ) : null}
          </>
        )}
        <label className="text-sm font-medium sm:col-span-2">
          {download ? 'Descripción' : 'Pie de recurso'}
          <input
            className="mt-1 block w-full rounded border bg-background px-2 py-1.5"
            maxLength={10000}
            onChange={(event) =>
              updateAttributes({
                [download ? 'description' : 'caption']: event.target.value,
              })
            }
            value={String(
              node.attrs[download ? 'description' : 'caption'] ?? '',
            )}
          />
        </label>
      </div>
    </NodeViewWrapper>
  );
}

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
