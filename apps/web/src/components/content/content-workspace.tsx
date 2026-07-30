'use client';

import type { Editor, JSONContent } from '@tiptap/core';
import { NodeSelection, Selection } from '@tiptap/pm/state';
import { EditorContent, useEditor } from '@tiptap/react';
import {
  Braces,
  CheckCircle2,
  CircleAlert,
  Code2,
  Eye,
  Link2,
  List,
  ListOrdered,
  LoaderCircle,
  PencilLine,
  Quote,
  Save,
  Sigma,
  Table2,
  Undo2,
  Unlink,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { cn } from '@/lib/utils';

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

function revisionStatusLabel(value: string) {
  return (
    {
      approved: 'Aprobada',
      changes_requested: 'Cambios solicitados',
      draft: 'Borrador',
      in_review: 'En revisión',
    }[value] ?? value
  );
}

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
    <Button
      aria-pressed={active}
      className={cn(
        'h-7 rounded-md px-2 text-xs',
        active && 'border-primary/20 bg-primary/10 text-primary',
      )}
      disabled={disabled}
      onClick={onClick}
      size="sm"
      type="button"
      variant={active ? 'secondary' : 'ghost'}
    >
      {children}
    </Button>
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
  const [restoreTarget, setRestoreTarget] = useState<number>();

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
    setBusy(true);
    setError('');
    try {
      const next = await restoreContentVersion(path, number, currentVersion);
      const validation = validateContentDocument(next.content);
      if (!validation.valid)
        throw new Error('El servidor devolvió un documento incompatible.');
      onRestore(number, validation.document, next);
      setViewed(undefined);
      setRestoreTarget(undefined);
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : 'No fue posible restaurar.',
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <details className="rounded-md border bg-card p-4 shadow-[0_1px_2px_rgb(0_0_0_/_0.025)]">
      <summary className="cursor-pointer text-base font-semibold">
        Historial de versiones ({versions.length})
      </summary>
      {error ? (
        <p
          className="mt-3 rounded-md border border-destructive/20 bg-destructive/5 p-3 text-sm text-destructive"
          role="alert"
        >
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
                <p className="text-sm text-muted-foreground">
                  {version.created_by_display} ·{' '}
                  {new Intl.DateTimeFormat('es-CO', {
                    dateStyle: 'medium',
                    timeStyle: 'short',
                  }).format(new Date(version.created_at))}
                </p>
                <p className="text-sm text-muted-foreground">
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
                    className="rounded-md border border-primary/40 px-3 py-2 text-sm font-medium text-primary hover:bg-primary/5"
                    disabled={busy}
                    onClick={() => setRestoreTarget(version.number)}
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
        <p className="mt-3 text-muted-foreground">
          Todavía no hay versiones guardadas.
        </p>
      )}
      {viewed ? (
        <section
          aria-labelledby="historical-preview"
          className="mt-5 border-t pt-5"
        >
          <h3 className="text-lg font-semibold" id="historical-preview">
            Vista de la versión {viewed.number}
          </h3>
          <div className="mt-4 rounded-md bg-muted/30 p-5">
            <AcademicDocument document={viewed.document} />
          </div>
        </section>
      ) : null}
      <AlertDialog
        onOpenChange={(open) => {
          if (!open) setRestoreTarget(undefined);
        }}
        open={restoreTarget !== undefined}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Restaurar versión {restoreTarget}
            </AlertDialogTitle>
            <AlertDialogDescription>
              Se creará una versión nueva a partir de este historial y el
              contenido actual del editor será reemplazado.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={busy}>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={busy || restoreTarget === undefined}
              onClick={() => {
                if (restoreTarget !== undefined) void restore(restoreTarget);
              }}
            >
              {busy ? 'Restaurando…' : 'Restaurar versión'}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
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
      <p className="mt-6 rounded-md border bg-card p-5" role="status">
        Preparando el editor…
      </p>
    );

  async function loadServerVersion() {
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
        <div className="flex flex-wrap items-center gap-3 rounded-lg border bg-card px-3 py-2.5 shadow-xs">
          <div className="flex min-w-0 items-center gap-2">
            {dirtyState === 'Guardando' ? (
              <LoaderCircle className="size-4 animate-spin text-primary" />
            ) : dirtyState === 'Guardado' || dirtyState === 'Sin cambios' ? (
              <CheckCircle2 className="size-4 text-emerald-700" />
            ) : (
              <CircleAlert className="size-4 text-amber-700" />
            )}
            <span className="text-sm font-medium">{dirtyState}</span>
          </div>
          <Badge className="rounded" variant="outline">
            Versión {documentVersion}
          </Badge>
          <div className="ml-auto flex rounded-lg border bg-muted/20 p-0.5">
            <Button
              aria-pressed={mode === 'edit'}
              className="h-7 rounded-md"
              onClick={() => setMode('edit')}
              size="sm"
              type="button"
              variant={mode === 'edit' ? 'secondary' : 'ghost'}
            >
              <PencilLine />
              Editar
            </Button>
            <Button
              aria-pressed={mode === 'preview'}
              className="h-7 rounded-md"
              onClick={() => setMode('preview')}
              size="sm"
              type="button"
              variant={mode === 'preview' ? 'secondary' : 'ghost'}
            >
              <Eye />
              Vista previa
            </Button>
          </div>
        </div>
        {['Cambios sin guardar', 'Conflicto'].includes(dirtyState) ? (
          <Alert className="border-amber-600/20 bg-amber-500/5">
            <CircleAlert className="text-amber-700" />
            <AlertTitle>Cambios locales pendientes</AlertTitle>
            <AlertDescription>
              Guarda antes de salir para conservar esta versión.
            </AlertDescription>
          </Alert>
        ) : null}
        {message ? (
          <Alert className="border-emerald-600/20 bg-emerald-500/5">
            <CheckCircle2 className="text-emerald-700" />
            <AlertTitle>Contenido actualizado</AlertTitle>
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        ) : null}
        {error ? (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertTitle>No se pudo completar la operación</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
            {dirtyState === 'Conflicto' ? (
              <AlertDialog>
                <AlertDialogTrigger asChild>
                  <Button className="mt-3" size="sm" variant="outline">
                    Cargar versión del servidor
                  </Button>
                </AlertDialogTrigger>
                <AlertDialogContent>
                  <AlertDialogHeader>
                    <AlertDialogTitle>
                      Reemplazar cambios locales
                    </AlertDialogTitle>
                    <AlertDialogDescription>
                      Se cargará la versión más reciente del servidor y se
                      descartarán los cambios locales que aún no se guardaron.
                    </AlertDialogDescription>
                  </AlertDialogHeader>
                  <AlertDialogFooter>
                    <AlertDialogCancel>Cancelar</AlertDialogCancel>
                    <AlertDialogAction
                      onClick={() => void loadServerVersion()}
                      variant="destructive"
                    >
                      Cargar versión del servidor
                    </AlertDialogAction>
                  </AlertDialogFooter>
                </AlertDialogContent>
              </AlertDialog>
            ) : null}
          </Alert>
        ) : null}
      </div>

      {mode === 'edit' ? (
        <section className="mt-6" aria-label="Editor académico">
          <div
            aria-label="Herramientas de formato"
            className="sticky top-12 z-10 flex flex-wrap gap-1 rounded-lg border bg-card/95 p-2 shadow-sm backdrop-blur"
            role="toolbar"
          >
            <EditorButton
              active={editor.isActive('paragraph')}
              onClick={() => editor.chain().focus().setParagraph().run()}
            >
              Texto
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
                H{level}
              </EditorButton>
            ))}
            <EditorButton
              active={editor.isActive('bold')}
              onClick={() => editor.chain().focus().toggleBold().run()}
            >
              <strong aria-hidden="true">B</strong>
              Negrita
            </EditorButton>
            <EditorButton
              active={editor.isActive('italic')}
              onClick={() => editor.chain().focus().toggleItalic().run()}
            >
              <em aria-hidden="true">I</em>
              Cursiva
            </EditorButton>
            <EditorButton
              active={editor.isActive('code')}
              onClick={() => editor.chain().focus().toggleCode().run()}
            >
              <Code2 />
              Código inline
            </EditorButton>
            <EditorButton
              active={editor.isActive('link') || linkPanel}
              onClick={() => {
                const activeHref = editor.getAttributes('link').href;
                setLinkHref(typeof activeHref === 'string' ? activeHref : '');
                setLinkPanel((value) => !value);
              }}
            >
              <Link2 />
              Enlace
            </EditorButton>
            <EditorButton
              active={editor.isActive('bulletList')}
              onClick={() => editor.chain().focus().toggleBulletList().run()}
            >
              <List />
              Viñetas
            </EditorButton>
            <EditorButton
              active={editor.isActive('orderedList')}
              onClick={() => editor.chain().focus().toggleOrderedList().run()}
            >
              <ListOrdered />
              Numerada
            </EditorButton>
            <EditorButton
              active={editor.isActive('blockquote')}
              onClick={() => editor.chain().focus().toggleBlockquote().run()}
            >
              <Quote />
              Cita
            </EditorButton>
            <EditorButton
              active={pedagogyPanel}
              onClick={() => setPedagogyPanel((value) => !value)}
            >
              Bloque académico
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
              <Sigma />
              Fórmula
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
              <Sigma />
              Ecuación
            </EditorButton>
            <EditorButton
              active={codePanel}
              onClick={() => setCodePanel((value) => !value)}
            >
              <Braces />
              Código
            </EditorButton>
            <EditorButton
              active={tablePanel}
              onClick={() => setTablePanel((value) => !value)}
            >
              <Table2 />
              Tabla
            </EditorButton>
            <EditorButton
              disabled={!editor.can().chain().focus().undo().run()}
              onClick={() => editor.chain().focus().undo().run()}
            >
              <Undo2 />
              Deshacer
            </EditorButton>
            <EditorButton
              disabled={!editor.can().chain().focus().redo().run()}
              onClick={() => editor.chain().focus().redo().run()}
            >
              <Undo2 className="-scale-x-100" />
              Rehacer
            </EditorButton>
          </div>

          {linkPanel ? (
            <div className="mt-2 flex flex-col gap-3 rounded-lg border bg-muted/20 p-3 sm:flex-row sm:items-end">
              <div className="min-w-0 flex-1 space-y-1.5">
                <Label htmlFor="content-link">Dirección del enlace</Label>
                <Input
                  id="content-link"
                  onChange={(event) => setLinkHref(event.target.value)}
                  placeholder="https://sitio.edu/recurso"
                  type="url"
                  value={linkHref}
                />
              </div>
              <Button
                onClick={() => {
                  try {
                    if (!safeContentHref(linkHref)) throw new Error();
                    editor
                      .chain()
                      .focus()
                      .extendMarkRange('link')
                      .setLink({ href: linkHref })
                      .run();
                    setError('');
                    setLinkPanel(false);
                  } catch {
                    setError(
                      'El enlace debe usar http, https, una ruta interna o un fragmento seguro.',
                    );
                  }
                }}
                type="button"
              >
                <Link2 />
                Aplicar enlace
              </Button>
              {editor.isActive('link') ? (
                <Button
                  onClick={() => {
                    editor.chain().focus().unsetLink().run();
                    setLinkPanel(false);
                  }}
                  type="button"
                  variant="outline"
                >
                  <Unlink />
                  Quitar
                </Button>
              ) : null}
            </div>
          ) : null}

          {pedagogyPanel ? (
            <div className="mt-2 grid gap-3 rounded-lg border bg-muted/20 p-3 sm:grid-cols-3">
              <label className="text-sm font-medium">
                Tipo
                <select
                  className="mt-1.5 h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
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
              <label className="text-sm font-medium">
                Título opcional
                <Input
                  className="mt-1.5"
                  maxLength={300}
                  onChange={(event) => setPedagogyTitle(event.target.value)}
                  value={pedagogyTitle}
                />
              </label>
              <Button
                className="self-end"
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
              </Button>
            </div>
          ) : null}

          {mathPanel ? (
            <div className="mt-2 space-y-3 rounded-lg border bg-muted/20 p-4">
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
                <label className="block text-sm font-medium">
                  Etiqueta opcional
                  <Input
                    className="mt-1.5"
                    maxLength={120}
                    onChange={(event) => setMathLabel(event.target.value)}
                    value={mathLabel}
                  />
                </label>
              ) : null}
              <div className="rounded-lg border bg-card p-3">
                <p className="mb-2 text-sm font-medium">Vista previa segura</p>
                <MathJaxFormula display={mathDisplay} latex={mathLatex} />
              </div>
              <div className="flex gap-2">
                <Button onClick={applyMath} type="button">
                  <Sigma />
                  Aplicar matemática
                </Button>
                <Button
                  onClick={() => {
                    setMathPanel(false);
                    setMathPosition(undefined);
                  }}
                  type="button"
                  variant="outline"
                >
                  Cancelar
                </Button>
              </div>
            </div>
          ) : null}

          {codePanel ? (
            <div className="mt-2 grid gap-3 rounded-lg border bg-muted/20 p-3 sm:grid-cols-3">
              <label className="text-sm font-medium">
                Lenguaje
                <select
                  className="mt-1.5 h-8 w-full rounded-lg border border-input bg-background px-2.5 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
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
              <label className="text-sm font-medium">
                Descripción opcional
                <Input
                  className="mt-1.5"
                  maxLength={300}
                  onChange={(event) => setCodeCaption(event.target.value)}
                  value={codeCaption}
                />
              </label>
              <Button
                className="self-end"
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
                <Braces />
                Insertar bloque de código
              </Button>
            </div>
          ) : null}

          {tablePanel ? (
            <div className="mt-2 grid gap-3 rounded-lg border bg-muted/20 p-3 sm:grid-cols-4">
              <label className="text-sm font-medium">
                Filas
                <Input
                  className="mt-1.5"
                  max={20}
                  min={2}
                  onChange={(event) => setTableRows(event.target.valueAsNumber)}
                  type="number"
                  value={tableRows}
                />
              </label>
              <label className="text-sm font-medium">
                Columnas
                <Input
                  className="mt-1.5"
                  max={10}
                  min={1}
                  onChange={(event) =>
                    setTableColumns(event.target.valueAsNumber)
                  }
                  type="number"
                  value={tableColumns}
                />
              </label>
              <label className="text-sm font-medium">
                Descripción
                <Input
                  className="mt-1.5"
                  maxLength={300}
                  onChange={(event) => setTableCaption(event.target.value)}
                  required
                  value={tableCaption}
                />
              </label>
              <Button
                className="self-end"
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
                <Table2 />
                Insertar tabla
              </Button>
            </div>
          ) : null}

          {editor.isActive('table') ? (
            <div
              aria-label="Herramientas de tabla"
              className="mt-2 flex flex-wrap gap-1 rounded-lg border bg-card p-2"
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
            className="mt-2 min-h-[30rem] rounded-lg border border-input bg-card p-5 shadow-xs sm:p-6 [&_.tiptap]:min-h-[27rem] [&_.tiptap]:space-y-4 [&_.tiptap]:outline-none"
            editor={editor}
          />
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <Button
              disabled={
                incompatible ||
                dirtyState === 'Guardando' ||
                dirtyState === 'Sin cambios'
              }
              onClick={() => void save()}
              type="button"
            >
              {dirtyState === 'Guardando' ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <Save />
              )}
              {dirtyState === 'Guardando' ? 'Guardando…' : 'Guardar contenido'}
            </Button>
            <p className="text-xs text-muted-foreground">
              Atajo: Ctrl+S o Cmd+S. El guardado es explícito; no hay autosave.
            </p>
          </div>
        </section>
      ) : (
        <section
          aria-labelledby="content-preview"
          className="mt-6 rounded-md border bg-card p-6"
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
      <div className="flex flex-wrap items-center gap-2 border-b pb-4">
        <Badge className="rounded" variant="secondary">
          {revisionStatusLabel(revisionStatus)}
        </Badge>
        <Badge className="rounded" variant="outline">
          {current.word_count}{' '}
          {current.word_count === 1 ? 'palabra' : 'palabras'}
        </Badge>
      </div>

      {!validation.valid ? (
        <Alert className="mt-6" variant="destructive">
          <CircleAlert />
          <AlertTitle>Documento incompatible</AlertTitle>
          <AlertDescription>
            El contenido se conserva intacto en el backend. No se truncará ni se
            guardará desde esta pantalla hasta que exista una migración
            explícita de schema.
          </AlertDescription>
        </Alert>
      ) : current.editable ? (
        <EditableContent
          current={current}
          initialDocument={validation.document}
          path={path}
          versions={versions}
        />
      ) : (
        <>
          <Alert className="mt-5 border-amber-600/20 bg-amber-500/5">
            <CircleAlert className="text-amber-700" />
            <AlertTitle>Contenido en solo lectura</AlertTitle>
            <AlertDescription>
              Esta revisión ya no admite cambios.
            </AlertDescription>
          </Alert>
          <div className="mt-5 rounded-md border bg-card p-5 sm:p-7">
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
