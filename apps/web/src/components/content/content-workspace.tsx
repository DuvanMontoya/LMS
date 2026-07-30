'use client';

import type { Editor, JSONContent } from '@tiptap/core';
import { NodeSelection, Selection } from '@tiptap/pm/state';
import { EditorContent, useEditor } from '@tiptap/react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import type { components } from '@/lib/api/generated/platform';
import {
  ContentConflictError,
  type ContentPath,
  fetchContentVersion,
  fetchCurrentContent,
  restoreContentVersion,
  saveContent,
} from '@/lib/content/api';
import { findDuplicateNodeIds } from '@/lib/content/editor/extensions';
import { interactiveContentEditorExtensions } from '@/lib/content/editor/interactive-extensions';
import type { LMSUnitAcademicDocumentVersion1 } from '@/lib/content/generated/unit-document-v1';
import {
  contentSafetyError,
  safeContentHref,
  validateContentDocument,
} from '@/lib/content/schema/validator';

import { AcademicDocument } from './academic-document';
import { MathJaxFormula } from './mathjax-formula';
import { MathLiveField } from './math-live-field';

type ContentCurrent = components['schemas']['ContentCurrent'];
type ContentVersion = components['schemas']['ContentVersionSummary'];
type DirtyState =
  | 'Sin cambios'
  | 'Cambios sin guardar'
  | 'Guardando'
  | 'Guardado'
  | 'Conflicto'
  | 'Error';

const pedagogicalKinds = [
  ['definition', 'Definición'],
  ['theorem', 'Teorema'],
  ['lemma', 'Lema'],
  ['proposition', 'Proposición'],
  ['corollary', 'Corolario'],
  ['proof', 'Demostración'],
  ['example', 'Ejemplo'],
  ['counterexample', 'Contraejemplo'],
  ['remark', 'Observación'],
  ['warning', 'Advertencia'],
  ['summary', 'Resumen'],
] as const;

function blockInsertionChain(editor: Editor) {
  const chain = editor.chain().focus();
  return editor.state.selection instanceof NodeSelection
    ? chain.command(({ tr }) => {
        tr.setSelection(
          Selection.near(tr.doc.resolve(editor.state.selection.to), 1),
        );
        return true;
      })
    : chain;
}

function EditorButton({
  active = false,
  children,
  disabled = false,
  onClick,
}: Readonly<{
  active?: boolean;
  children: React.ReactNode;
  disabled?: boolean;
  onClick: () => void;
}>) {
  return (
    <button
      aria-pressed={active}
      className={`rounded-md border px-3 py-2 text-sm font-medium ${
        active
          ? 'border-sky-700 bg-sky-50 text-sky-900'
          : 'border-slate-300 bg-white text-slate-800'
      }`}
      disabled={disabled}
      onClick={onClick}
      type="button"
    >
      {children}
    </button>
  );
}

function VersionHistory({
  canRestore,
  currentVersion,
  onRestore,
  path,
  versions,
}: Readonly<{
  canRestore: boolean;
  currentVersion: number;
  onRestore: (
    number: number,
    document: LMSUnitAcademicDocumentVersion1,
    next: ContentCurrent,
  ) => void;
  path: ContentPath;
  versions: ContentVersion[];
}>) {
  const [viewed, setViewed] = useState<{
    document: LMSUnitAcademicDocumentVersion1;
    number: number;
  }>();
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function view(number: number) {
    setBusy(true);
    setError('');
    try {
      const detail = await fetchContentVersion(path, number);
      const validation = validateContentDocument(detail.content);
      if (!validation.valid)
        throw new Error(
          'La versión histórica no es compatible con el schema del editor.',
        );
      setViewed({ document: validation.document, number });
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'No fue posible abrir.',
      );
    } finally {
      setBusy(false);
    }
  }

  async function restore(number: number) {
    if (
      !window.confirm(
        `Restaurar la versión ${number} creará una versión nueva y reemplazará el editor actual. ¿Continuar?`,
      )
    )
      return;
    setBusy(true);
    setError('');
    try {
      const next = await restoreContentVersion(path, number, currentVersion);
      const validation = validateContentDocument(next.content);
      if (!validation.valid)
        throw new Error('El servidor devolvió un documento incompatible.');
      onRestore(number, validation.document, next);
      setViewed(undefined);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'No fue posible restaurar.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="rounded-xl border border-slate-200 bg-white p-4">
      <summary className="cursor-pointer text-lg font-semibold">
        Historial de versiones ({versions.length})
      </summary>
      {error ? (
        <p className="mt-3 rounded-lg bg-red-50 p-3 text-red-800" role="alert">
          {error}
        </p>
      ) : null}
      {versions.length ? (
        <ol className="mt-4 divide-y divide-slate-200">
          {versions.map((version) => (
            <li
              className="flex flex-wrap items-center justify-between gap-3 py-3"
              key={version.number}
            >
              <div>
                <p className="font-medium">
                  Versión {version.number}
                  {version.is_current ? ' · actual' : ''}
                </p>
                <p className="text-sm text-slate-600">
                  {version.created_by_display} ·{' '}
                  {new Intl.DateTimeFormat('es-CO', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  }).format(new Date(version.created_at))}
                </p>
                <p className="text-sm text-slate-600">
                  {version.word_count} palabras · {version.character_count}{' '}
                  caracteres · {version.node_count} nodos
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  className="rounded border px-3 py-2 text-sm"
                  disabled={busy}
                  onClick={() => view(version.number)}
                  type="button"
                >
                  Ver
                </button>
                {canRestore ? (
                  <button
                    className="rounded border border-sky-700 px-3 py-2 text-sm text-sky-800"
                    disabled={busy}
                    onClick={() => restore(version.number)}
                    type="button"
                  >
                    Restaurar
                  </button>
                ) : null}
              </div>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 text-slate-600">
          Todavía no hay versiones guardadas.
        </p>
      )}
      {viewed ? (
        <section
          aria-labelledby="historical-preview"
          className="mt-5 border-t border-slate-200 pt-5"
        >
          <h3 className="text-lg font-semibold" id="historical-preview">
            Vista de la versión {viewed.number}
          </h3>
          <div className="mt-4 rounded-xl bg-slate-50 p-5">
            <AcademicDocument document={viewed.document} />
          </div>
        </section>
      ) : null}
    </details>
  );
}

function EditableContent({
  current,
  initialDocument,
  path,
  versions,
}: Readonly<{
  current: ContentCurrent;
  initialDocument: LMSUnitAcademicDocumentVersion1;
  path: ContentPath;
  versions: ContentVersion[];
}>) {
  const router = useRouter();
  const [documentVersion, setDocumentVersion] = useState(
    current.document_version,
  );
  const [dirtyState, setDirtyState] = useState<DirtyState>('Sin cambios');
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [incompatible, setIncompatible] = useState(false);
  const [mode, setMode] = useState<'edit' | 'preview'>('edit');
  const [linkPanel, setLinkPanel] = useState(false);
  const [linkHref, setLinkHref] = useState('');
  const [pedagogyPanel, setPedagogyPanel] = useState(false);
  const [pedagogyKind, setPedagogyKind] = useState('definition');
  const [pedagogyTitle, setPedagogyTitle] = useState('');
  const [mathPanel, setMathPanel] = useState(false);
  const [mathDisplay, setMathDisplay] = useState(false);
  const [mathLatex, setMathLatex] = useState('');
  const [mathLabel, setMathLabel] = useState('');
  const [mathPosition, setMathPosition] = useState<number>();
  const [codePanel, setCodePanel] = useState(false);
  const [codeLanguage, setCodeLanguage] = useState('plaintext');
  const [codeCaption, setCodeCaption] = useState('');
  const [tablePanel, setTablePanel] = useState(false);
  const [tableRows, setTableRows] = useState(3);
  const [tableColumns, setTableColumns] = useState(3);
  const [tableCaption, setTableCaption] = useState('');
  const [currentForHistory, setCurrentForHistory] = useState(current);
  const [previewDocument, setPreviewDocument] = useState(initialDocument);

  const editor = useEditor({
    content: initialDocument as JSONContent,
    enableContentCheck: true,
    editorProps: {
      attributes: {
        'aria-label': 'Contenido académico de la unidad',
        role: 'textbox',
      },
      handleDrop: (_view, event) => {
        if (!event.dataTransfer?.files.length) return false;
        setError(
          'No se admiten archivos ni imágenes en el documento semántico.',
        );
        return true;
      },
      handlePaste: (_view, event) => {
        const clipboardData = event.clipboardData;
        if (!clipboardData) return false;
        if (clipboardData.files.length) {
          setError('No se admiten archivos pegados en el documento semántico.');
          return true;
        }
        const html = clipboardData.getData('text/html');
        if (
          /<(script|style|iframe|img|svg|video|audio|object|embed|math)\b/i.test(
            html,
          )
        )
          setMessage(
            'Se descartó estructura no compatible del contenido pegado; sólo se conservó formato semántico admitido.',
          );
        return false;
      },
    },
    extensions: interactiveContentEditorExtensions,
    immediatelyRender: false,
    onContentError: () => {
      setIncompatible(true);
      setError(
        'El documento no es compatible con el schema del editor. Se conserva intacto en el servidor y no puede guardarse desde esta pantalla.',
      );
    },
    onSelectionUpdate: ({ editor: activeEditor }) => {
      const selection = activeEditor.state.selection;
      const node = activeEditor.state.doc.nodeAt(selection.from);
      if (!node || !['inlineMath', 'displayMath'].includes(node.type.name))
        return;
      setMathPosition(selection.from);
      setMathDisplay(node.type.name === 'displayMath');
      setMathLatex(String(node.attrs.latex ?? ''));
      setMathLabel(String(node.attrs.label ?? ''));
      setMathPanel(true);
    },
    onUpdate: ({ editor: activeEditor, transaction }) => {
      const validation = validateContentDocument(activeEditor.getJSON());
      if (validation.valid) setPreviewDocument(validation.document);
      if (transaction.getMeta('addToHistory') === false) return;
      setDirtyState('Cambios sin guardar');
      setMessage('');
    },
  });

  const save = useCallback(async () => {
    if (!editor || incompatible || dirtyState === 'Guardando') return;
    setError('');
    setMessage('');
    const json = editor.getJSON();
    const duplicates = findDuplicateNodeIds(json);
    if (duplicates.length) {
      setDirtyState('Error');
      setError(
        'Hay identificadores de bloque duplicados. Duplica de nuevo el bloque o vuelve a cargar la versión del servidor.',
      );
      return;
    }
    const validation = validateContentDocument(json);
    if (!validation.valid) {
      setDirtyState('Error');
      setError(`No se puede guardar: ${validation.message}`);
      return;
    }
    const safetyError = contentSafetyError(validation.document);
    if (safetyError) {
      setDirtyState('Error');
      setError(`No se puede guardar: ${safetyError}`);
      return;
    }
    setDirtyState('Guardando');
    try {
      const next = await saveContent(path, {
        content: validation.document,
        expected_document_version: documentVersion,
        schema_version: 1,
      });
      setDocumentVersion(next.document_version);
      setCurrentForHistory(next);
      setPreviewDocument(validation.document);
      setDirtyState('Guardado');
      setMessage(
        next.no_op
          ? 'El contenido ya coincidía con la versión actual; no se creó una versión duplicada.'
          : `Contenido guardado como versión ${next.document_version}.`,
      );
      router.refresh();
    } catch (cause) {
      if (cause instanceof ContentConflictError) {
        setDirtyState('Conflicto');
        setError(
          'Otra persona guardó una versión más reciente. Tu contenido local se conserva y no se reintentará ni sobrescribirá automáticamente.',
        );
      } else {
        setDirtyState('Error');
        setError(
          cause instanceof Error
            ? cause.message
            : 'No fue posible guardar el contenido.',
        );
      }
    }
  }, [dirtyState, documentVersion, editor, incompatible, path, router]);

  useEffect(() => {
    const listener = (event: BeforeUnloadEvent) => {
      if (dirtyState === 'Cambios sin guardar' || dirtyState === 'Conflicto')
        event.preventDefault();
    };
    window.addEventListener('beforeunload', listener);
    return () => window.removeEventListener('beforeunload', listener);
  }, [dirtyState]);

  useEffect(() => {
    const listener = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 's') {
        event.preventDefault();
        void save();
      }
    };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, [save]);

  if (!editor)
    return (
      <p className="mt-6 rounded-xl border p-5" role="status">
        Preparando el editor…
      </p>
    );

  async function loadServerVersion() {
    if (
      !window.confirm(
        'Cargar la versión del servidor reemplazará los cambios locales no guardados. ¿Continuar?',
      )
    )
      return;
    setError('');
    try {
      const next = await fetchCurrentContent(path);
      const validation = validateContentDocument(next.content);
      if (!validation.valid)
        throw new Error('La versión del servidor no es compatible.');
      editor!.commands.setContent(validation.document as JSONContent, {
        emitUpdate: false,
        errorOnInvalidContent: true,
      });
      setDocumentVersion(next.document_version);
      setCurrentForHistory(next);
      setPreviewDocument(validation.document);
      setDirtyState('Sin cambios');
      setMessage(`Se cargó la versión ${next.document_version} del servidor.`);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'No fue posible cargar.',
      );
    }
  }

  function applyMath() {
    const latex = mathLatex.trim();
    if (!latex || latex.length > 10_000) {
      setError('La fórmula debe contener entre 1 y 10 000 caracteres.');
      return;
    }
    const mathSafetyError = contentSafetyError({
      attrs: { latex },
      type: mathDisplay ? 'displayMath' : 'inlineMath',
    });
    if (mathSafetyError) {
      setError(mathSafetyError);
      return;
    }
    if (
      mathDisplay &&
      mathLabel.trim() &&
      !/^[A-Za-z0-9][A-Za-z0-9_.:-]*$/.test(mathLabel.trim())
    ) {
      setError(
        'La etiqueta matemática debe comenzar con letra o número y usar sólo letras ASCII, números, punto, guion, guion bajo o dos puntos.',
      );
      return;
    }
    const attrs = {
      label: mathDisplay ? mathLabel.trim() || null : undefined,
      latex,
      nodeId: crypto.randomUUID(),
    };
    if (mathPosition !== undefined) {
      editor!.commands.command(({ state, tr }) => {
        const node = state.doc.nodeAt(mathPosition);
        if (!node || !['inlineMath', 'displayMath'].includes(node.type.name))
          return false;
        tr.setNodeMarkup(mathPosition, undefined, {
          ...node.attrs,
          label: mathDisplay ? mathLabel.trim() || null : undefined,
          latex,
        });
        return true;
      });
    } else {
      const chain = mathDisplay
        ? blockInsertionChain(editor!)
        : editor!.chain().focus();
      chain
        .insertContent({
          attrs,
          type: mathDisplay ? 'displayMath' : 'inlineMath',
        })
        .run();
    }
    setMathPanel(false);
    setMathPosition(undefined);
  }

  return (
    <>
      <div aria-live="polite" className="mt-6 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white p-4">
          <div>
            <p className="text-sm text-slate-600">Estado guardado</p>
            <p className="font-semibold">{dirtyState}</p>
          </div>
          <p className="text-sm text-slate-600">
            Versión actual: {documentVersion}
          </p>
          <div className="flex rounded-lg border border-slate-300 p-1">
            <button
              aria-pressed={mode === 'edit'}
              className="rounded px-3 py-2 text-sm"
              onClick={() => setMode('edit')}
              type="button"
            >
              Editar
            </button>
            <button
              aria-pressed={mode === 'preview'}
              className="rounded px-3 py-2 text-sm"
              onClick={() => setMode('preview')}
              type="button"
            >
              Vista previa
            </button>
          </div>
        </div>
        {['Cambios sin guardar', 'Conflicto'].includes(dirtyState) ? (
          <p className="rounded-lg bg-amber-50 p-3 text-amber-950">
            Hay cambios locales que todavía no están guardados.
          </p>
        ) : null}
        {message ? (
          <p className="rounded-lg bg-emerald-50 p-3 text-emerald-900">
            {message}
          </p>
        ) : null}
        {error ? (
          <div className="rounded-lg bg-red-50 p-3 text-red-900" role="alert">
            <p>{error}</p>
            {dirtyState === 'Conflicto' ? (
              <button
                className="mt-3 rounded border border-red-700 px-3 py-2 font-medium"
                onClick={loadServerVersion}
                type="button"
              >
                Cargar versión del servidor
              </button>
            ) : null}
          </div>
        ) : null}
      </div>

      {mode === 'edit' ? (
        <section className="mt-6" aria-label="Editor académico">
          <div
            aria-label="Herramientas de formato"
            className="flex flex-wrap gap-2 rounded-t-xl border border-b-0 border-slate-300 bg-slate-50 p-3"
            role="toolbar"
          >
            <EditorButton
              active={editor.isActive('paragraph')}
              onClick={() => editor.chain().focus().setParagraph().run()}
            >
              Párrafo
            </EditorButton>
            {[2, 3, 4].map((level) => (
              <EditorButton
                active={editor.isActive('heading', { level })}
                key={level}
                onClick={() =>
                  editor
                    .chain()
                    .focus()
                    .setHeading({ level: level as 2 | 3 | 4 })
                    .run()
                }
              >
                Título nivel {level}
              </EditorButton>
            ))}
            <EditorButton
              active={editor.isActive('bold')}
              onClick={() => editor.chain().focus().toggleBold().run()}
            >
              Negrita
            </EditorButton>
            <EditorButton
              active={editor.isActive('italic')}
              onClick={() => editor.chain().focus().toggleItalic().run()}
            >
              Cursiva
            </EditorButton>
            <EditorButton
              active={editor.isActive('code')}
              onClick={() => editor.chain().focus().toggleCode().run()}
            >
              Código inline
            </EditorButton>
            <EditorButton onClick={() => setLinkPanel((value) => !value)}>
              Enlace
            </EditorButton>
            <EditorButton
              active={editor.isActive('bulletList')}
              onClick={() => editor.chain().focus().toggleBulletList().run()}
            >
              Lista con viñetas
            </EditorButton>
            <EditorButton
              active={editor.isActive('orderedList')}
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
            >
              Lista numerada
            </EditorButton>
            <EditorButton
              active={editor.isActive('blockquote')}
              onClick={() => editor.chain().focus().toggleBlockquote().run()}
            >
              Cita
            </EditorButton>
            <EditorButton onClick={() => setPedagogyPanel((value) => !value)}>
              Bloque pedagógico
            </EditorButton>
            <EditorButton
              onClick={() => {
                setMathPosition(undefined);
                setMathDisplay(false);
                setMathLatex('');
                setMathLabel('');
                setMathPanel(true);
              }}
            >
              Matemática inline
            </EditorButton>
            <EditorButton
              onClick={() => {
                setMathPosition(undefined);
                setMathDisplay(true);
                setMathLatex('');
                setMathLabel('');
                setMathPanel(true);
              }}
            >
              Matemática display
            </EditorButton>
            <EditorButton onClick={() => setCodePanel((value) => !value)}>
              Bloque de código
            </EditorButton>
            <EditorButton onClick={() => setTablePanel((value) => !value)}>
              Tabla
            </EditorButton>
            <EditorButton
              disabled={!editor.can().chain().focus().undo().run()}
              onClick={() => editor.chain().focus().undo().run()}
            >
              Deshacer
            </EditorButton>
            <EditorButton
              disabled={!editor.can().chain().focus().redo().run()}
              onClick={() => editor.chain().focus().redo().run()}
            >
              Rehacer
            </EditorButton>
          </div>

          {linkPanel ? (
            <div className="border-x border-slate-300 bg-white p-3">
              <label className="font-medium">
                URL segura
                <input
                  className="ml-3 min-w-72 rounded border px-3 py-2"
                  onChange={(event) => setLinkHref(event.target.value)}
                  placeholder="https://…"
                  type="url"
                  value={linkHref}
                />
              </label>
              <button
                className="ml-3 rounded border px-3 py-2"
                onClick={() => {
                  try {
                    if (!safeContentHref(linkHref)) throw new Error();
                    editor
                      .chain()
                      .focus()
                      .extendMarkRange('link')
                      .setLink({ href: linkHref })
                      .run();
                    setLinkPanel(false);
                  } catch {
                    setError(
                      'El enlace debe usar http, https, una ruta interna o un fragmento seguro.',
                    );
                  }
                }}
                type="button"
              >
                Aplicar enlace
              </button>
            </div>
          ) : null}

          {pedagogyPanel ? (
            <div className="grid gap-3 border-x border-slate-300 bg-white p-3 sm:grid-cols-3">
              <label className="font-medium">
                Tipo
                <select
                  className="mt-1 w-full rounded border px-3 py-2"
                  onChange={(event) => setPedagogyKind(event.target.value)}
                  value={pedagogyKind}
                >
                  {pedagogicalKinds.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="font-medium">
                Título opcional
                <input
                  className="mt-1 w-full rounded border px-3 py-2"
                  maxLength={300}
                  onChange={(event) => setPedagogyTitle(event.target.value)}
                  value={pedagogyTitle}
                />
              </label>
              <button
                className="self-end rounded bg-slate-950 px-4 py-2 font-medium text-white"
                onClick={() => {
                  blockInsertionChain(editor)
                    .insertContent({
                      attrs: {
                        kind: pedagogyKind,
                        nodeId: crypto.randomUUID(),
                        title: pedagogyTitle.trim() || null,
                      },
                      content: [
                        {
                          attrs: { nodeId: crypto.randomUUID() },
                          type: 'paragraph',
                        },
                      ],
                      type: 'pedagogicalBlock',
                    })
                    .run();
                  setPedagogyPanel(false);
                }}
                type="button"
              >
                Insertar bloque
              </button>
            </div>
          ) : null}

          {mathPanel ? (
            <div className="space-y-3 border-x border-slate-300 bg-white p-4">
              <div className="flex flex-wrap gap-4">
                <label>
                  <input
                    checked={!mathDisplay}
                    name="math-kind"
                    onChange={() => setMathDisplay(false)}
                    type="radio"
                  />{' '}
                  En línea
                </label>
                <label>
                  <input
                    checked={mathDisplay}
                    name="math-kind"
                    onChange={() => setMathDisplay(true)}
                    type="radio"
                  />{' '}
                  En bloque
                </label>
              </div>
              <MathLiveField onChange={setMathLatex} value={mathLatex} />
              {mathDisplay ? (
                <label className="block font-medium">
                  Etiqueta opcional
                  <input
                    className="mt-1 w-full rounded border px-3 py-2"
                    maxLength={120}
                    onChange={(event) => setMathLabel(event.target.value)}
                    value={mathLabel}
                  />
                </label>
              ) : null}
              <div className="rounded-lg bg-slate-50 p-3">
                <p className="mb-2 text-sm font-medium">Vista previa segura</p>
                <MathJaxFormula display={mathDisplay} latex={mathLatex} />
              </div>
              <div className="flex gap-2">
                <button
                  className="rounded bg-slate-950 px-4 py-2 text-white"
                  onClick={applyMath}
                  type="button"
                >
                  Aplicar matemática
                </button>
                <button
                  className="rounded border px-4 py-2"
                  onClick={() => {
                    setMathPanel(false);
                    setMathPosition(undefined);
                  }}
                  type="button"
                >
                  Cancelar
                </button>
              </div>
            </div>
          ) : null}

          {codePanel ? (
            <div className="grid gap-3 border-x border-slate-300 bg-white p-3 sm:grid-cols-3">
              <label className="font-medium">
                Lenguaje
                <select
                  className="mt-1 w-full rounded border px-3 py-2"
                  onChange={(event) => setCodeLanguage(event.target.value)}
                  value={codeLanguage}
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
                    <option key={language}>{language}</option>
                  ))}
                </select>
              </label>
              <label className="font-medium">
                Descripción opcional
                <input
                  className="mt-1 w-full rounded border px-3 py-2"
                  maxLength={300}
                  onChange={(event) => setCodeCaption(event.target.value)}
                  value={codeCaption}
                />
              </label>
              <button
                className="self-end rounded bg-slate-950 px-4 py-2 text-white"
                onClick={() => {
                  blockInsertionChain(editor)
                    .insertContent({
                      attrs: {
                        caption: codeCaption.trim() || null,
                        code: '',
                        language: codeLanguage,
                        nodeId: crypto.randomUUID(),
                      },
                      type: 'codeBlock',
                    })
                    .run();
                  setCodePanel(false);
                }}
                type="button"
              >
                Insertar bloque de código
              </button>
            </div>
          ) : null}

          {tablePanel ? (
            <div className="grid gap-3 border-x border-slate-300 bg-white p-3 sm:grid-cols-4">
              <label className="font-medium">
                Filas
                <input
                  className="mt-1 w-full rounded border px-3 py-2"
                  max={20}
                  min={2}
                  onChange={(event) => setTableRows(event.target.valueAsNumber)}
                  type="number"
                  value={tableRows}
                />
              </label>
              <label className="font-medium">
                Columnas
                <input
                  className="mt-1 w-full rounded border px-3 py-2"
                  max={10}
                  min={1}
                  onChange={(event) =>
                    setTableColumns(event.target.valueAsNumber)
                  }
                  type="number"
                  value={tableColumns}
                />
              </label>
              <label className="font-medium">
                Descripción
                <input
                  className="mt-1 w-full rounded border px-3 py-2"
                  maxLength={300}
                  onChange={(event) => setTableCaption(event.target.value)}
                  required
                  value={tableCaption}
                />
              </label>
              <button
                className="self-end rounded bg-slate-950 px-4 py-2 text-white"
                onClick={() => {
                  if (!tableCaption.trim()) {
                    setError('La tabla requiere una descripción.');
                    return;
                  }
                  blockInsertionChain(editor)
                    .insertTable({
                      cols: tableColumns,
                      rows: tableRows,
                      withHeaderRow: true,
                    })
                    .updateAttributes('table', {
                      caption: tableCaption.trim(),
                    })
                    .run();
                  setTablePanel(false);
                }}
                type="button"
              >
                Insertar tabla
              </button>
            </div>
          ) : null}

          {editor.isActive('table') ? (
            <div
              aria-label="Herramientas de tabla"
              className="flex flex-wrap gap-2 border-x border-slate-300 bg-white p-3"
              role="toolbar"
            >
              <EditorButton
                onClick={() => editor.chain().focus().addRowAfter().run()}
              >
                Añadir fila
              </EditorButton>
              <EditorButton
                onClick={() => editor.chain().focus().deleteRow().run()}
              >
                Eliminar fila
              </EditorButton>
              <EditorButton
                onClick={() => editor.chain().focus().addColumnAfter().run()}
              >
                Añadir columna
              </EditorButton>
              <EditorButton
                onClick={() => editor.chain().focus().deleteColumn().run()}
              >
                Eliminar columna
              </EditorButton>
              <EditorButton
                onClick={() => editor.chain().focus().toggleHeaderRow().run()}
              >
                Cambiar primera fila a encabezados
              </EditorButton>
            </div>
          ) : null}

          <EditorContent
            className="min-h-[30rem] rounded-b-xl border border-slate-300 bg-white p-6 shadow-sm [&_.tiptap]:min-h-[27rem] [&_.tiptap]:space-y-4 [&_.tiptap]:outline-none"
            editor={editor}
          />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              className="rounded-lg bg-sky-700 px-5 py-3 font-semibold text-white disabled:opacity-50"
              disabled={
                incompatible ||
                dirtyState === 'Guardando' ||
                dirtyState === 'Sin cambios'
              }
              onClick={() => void save()}
              type="button"
            >
              {dirtyState === 'Guardando' ? 'Guardando…' : 'Guardar contenido'}
            </button>
            <p className="text-sm text-slate-600">
              Atajo: Ctrl+S o Cmd+S. El guardado es explícito; no hay autosave.
            </p>
          </div>
        </section>
      ) : (
        <section
          aria-labelledby="content-preview"
          className="mt-6 rounded-xl border border-slate-200 bg-white p-6"
        >
          <h2 className="sr-only" id="content-preview">
            Vista previa
          </h2>
          <AcademicDocument document={previewDocument} />
        </section>
      )}

      <div className="mt-8">
        <VersionHistory
          canRestore
          currentVersion={currentForHistory.document_version}
          onRestore={(_number, document, next) => {
            editor.commands.setContent(document as JSONContent, {
              emitUpdate: false,
              errorOnInvalidContent: true,
            });
            setDocumentVersion(next.document_version);
            setCurrentForHistory(next);
            setPreviewDocument(document);
            setDirtyState('Guardado');
            setMessage(
              `Versión restaurada como versión ${next.document_version}.`,
            );
            router.refresh();
          }}
          path={path}
          versions={versions}
        />
      </div>
    </>
  );
}

export function ContentWorkspace({
  courseSlug,
  current,
  organizationSlug,
  revisionId,
  revisionStatus,
  unitId,
  versions,
}: Readonly<{
  courseSlug: string;
  current: ContentCurrent;
  organizationSlug: string;
  revisionId: string;
  revisionStatus: string;
  unitId: string;
  versions: ContentVersion[];
}>) {
  const validation = validateContentDocument(current.content);
  const path = { courseSlug, organizationSlug, revisionId, unitId };

  return (
    <section aria-labelledby="content-workspace" className="mt-6">
      <h2 className="sr-only" id="content-workspace">
        Espacio de trabajo de contenido
      </h2>
      <div className="flex flex-wrap gap-3 text-sm">
        <span className="rounded-full bg-slate-100 px-3 py-1.5">
          Estado de revisión: {revisionStatus}
        </span>
        <span className="rounded-full bg-slate-100 px-3 py-1.5">
          Schema: v{current.schema_version}
        </span>
        <span className="rounded-full bg-slate-100 px-3 py-1.5">
          {current.word_count} palabras
        </span>
      </div>

      {!validation.valid ? (
        <div
          className="mt-6 rounded-xl border border-red-300 bg-red-50 p-5 text-red-950"
          role="alert"
        >
          <h3 className="font-semibold">Documento incompatible</h3>
          <p className="mt-2">
            El contenido se conserva intacto en el backend. No se truncará ni se
            guardará desde esta pantalla hasta que exista una migración
            explícita de schema.
          </p>
        </div>
      ) : current.editable ? (
        <EditableContent
          current={current}
          initialDocument={validation.document}
          path={path}
          versions={versions}
        />
      ) : (
        <>
          <p className="mt-6 rounded-lg bg-amber-50 p-3 text-amber-950">
            Esta revisión está en modo de solo lectura. El editor, la barra de
            herramientas, el guardado y la restauración están deshabilitados.
          </p>
          <div className="mt-6 rounded-xl border border-slate-200 bg-white p-6">
            <AcademicDocument document={validation.document} />
          </div>
          <div className="mt-8">
            <VersionHistory
              canRestore={false}
              currentVersion={current.document_version}
              onRestore={() => undefined}
              path={path}
              versions={versions}
            />
          </div>
        </>
      )}
    </section>
  );
}
