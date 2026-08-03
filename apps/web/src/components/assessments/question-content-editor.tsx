'use client';

import type { Editor, JSONContent } from '@tiptap/core';
import { NodeSelection, Selection } from '@tiptap/pm/state';
import { EditorContent, useEditor } from '@tiptap/react';
import {
  Bold,
  Eye,
  Heading2,
  Italic,
  List,
  ListOrdered,
  PencilLine,
  Quote,
  Redo2,
  Table2,
  Undo2,
} from 'lucide-react';
import { useState } from 'react';

import { AssetPickerDialog } from '@/components/assets/asset-picker-dialog';
import { AcademicDocument } from '@/components/content/academic-document';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { interactiveContentEditorExtensions } from '@/lib/content/editor/interactive-extensions';
import { findDuplicateNodeIds } from '@/lib/content/editor/extensions';
import type { LMSUnitAcademicDocumentVersion2 } from '@/lib/content/generated/unit-document-v2';
import {
  contentSafetyError,
  validateContentDocument,
} from '@/lib/content/schema/validator';
import { cn } from '@/lib/utils';

type QuestionContentEditorProps = Readonly<{
  ariaLabel: string;
  compact?: boolean;
  onChange: (document: LMSUnitAcademicDocumentVersion2) => void;
  slug: string;
  value: LMSUnitAcademicDocumentVersion2;
}>;

function insertionChain(editor: Editor) {
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

function ToolbarButton({
  active = false,
  children,
  disabled = false,
  label,
  onClick,
}: Readonly<{
  active?: boolean;
  children: React.ReactNode;
  disabled?: boolean;
  label: string;
  onClick: () => void;
}>) {
  return (
    <Button
      aria-label={label}
      aria-pressed={active}
      className={cn('size-8', active && 'bg-primary/10 text-primary')}
      disabled={disabled}
      onClick={onClick}
      size="icon-sm"
      type="button"
      variant="ghost"
    >
      {children}
    </Button>
  );
}

export function QuestionContentEditor({
  ariaLabel,
  compact = false,
  onChange,
  slug,
  value,
}: QuestionContentEditorProps) {
  const [mode, setMode] = useState<'edit' | 'preview'>('edit');
  const [error, setError] = useState('');
  const [tableOpen, setTableOpen] = useState(false);
  const [tableRows, setTableRows] = useState(3);
  const [tableColumns, setTableColumns] = useState(3);
  const [tableCaption, setTableCaption] = useState('');

  const editor = useEditor({
    content: value as JSONContent,
    enableContentCheck: true,
    editorProps: {
      attributes: { 'aria-label': ariaLabel, role: 'textbox' },
      handleDrop: (_view, event) => {
        if (!event.dataTransfer?.files.length) return false;
        setError(
          'Usa “Imagen o recurso” para subir el archivo o elegirlo desde Recursos.',
        );
        return true;
      },
      handlePaste: (_view, event) => {
        if (!event.clipboardData?.files.length) return false;
        setError(
          'Usa “Imagen o recurso” para cargarlo con accesibilidad y trazabilidad.',
        );
        return true;
      },
    },
    extensions: interactiveContentEditorExtensions,
    immediatelyRender: false,
    onUpdate: ({ editor: activeEditor }) => {
      const json = activeEditor.getJSON();
      const duplicates = findDuplicateNodeIds(json);
      if (duplicates.length) {
        setError('Hay identificadores de bloque duplicados.');
        return;
      }
      const validation = validateContentDocument(json);
      if (!validation.valid) {
        setError(validation.message);
        return;
      }
      const safetyError = contentSafetyError(validation.document);
      if (safetyError) {
        setError(safetyError);
        return;
      }
      setError('');
      onChange(validation.document);
    },
  });

  if (!editor) {
    return <p className="assessment-editor-loading">Preparando estudio…</p>;
  }

  return (
    <div className="assessment-rich-editor" data-compact={compact}>
      <div
        aria-label="Herramientas del documento"
        className="assessment-rich-editor__toolbar"
        role="toolbar"
      >
        <div>
          <ToolbarButton
            active={editor.isActive('bold')}
            label="Negrita"
            onClick={() => editor.chain().focus().toggleBold().run()}
          >
            <Bold />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive('italic')}
            label="Cursiva"
            onClick={() => editor.chain().focus().toggleItalic().run()}
          >
            <Italic />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive('heading', { level: 2 })}
            label="Encabezado"
            onClick={() =>
              editor.chain().focus().toggleHeading({ level: 2 }).run()
            }
          >
            <Heading2 />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive('bulletList')}
            label="Lista"
            onClick={() => editor.chain().focus().toggleBulletList().run()}
          >
            <List />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive('orderedList')}
            label="Lista numerada"
            onClick={() => editor.chain().focus().toggleOrderedList().run()}
          >
            <ListOrdered />
          </ToolbarButton>
          <ToolbarButton
            active={editor.isActive('blockquote')}
            label="Cita o contexto destacado"
            onClick={() => editor.chain().focus().toggleBlockquote().run()}
          >
            <Quote />
          </ToolbarButton>
        </div>
        <div>
          {!compact ? (
            <>
              <Button
                onClick={() => setTableOpen((current) => !current)}
                size="sm"
                type="button"
                variant="ghost"
              >
                <Table2 /> Tabla
              </Button>
              <AssetPickerDialog
                onInsert={(node) =>
                  insertionChain(editor).insertContent(node).run()
                }
                slug={slug}
                triggerLabel="Imagen o recurso"
              />
            </>
          ) : null}
        </div>
        <div className="ml-auto">
          <ToolbarButton
            disabled={!editor.can().undo()}
            label="Deshacer"
            onClick={() => editor.chain().focus().undo().run()}
          >
            <Undo2 />
          </ToolbarButton>
          <ToolbarButton
            disabled={!editor.can().redo()}
            label="Rehacer"
            onClick={() => editor.chain().focus().redo().run()}
          >
            <Redo2 />
          </ToolbarButton>
          <Button
            onClick={() =>
              setMode((current) => (current === 'edit' ? 'preview' : 'edit'))
            }
            size="sm"
            type="button"
            variant="outline"
          >
            {mode === 'edit' ? <Eye /> : <PencilLine />}
            {mode === 'edit' ? 'Previsualizar' : 'Editar'}
          </Button>
        </div>
      </div>

      {tableOpen && !compact ? (
        <section
          className="assessment-rich-editor__insert-panel assessment-rich-editor__table-panel"
          aria-label="Insertar tabla"
        >
          <label>
            Filas
            <Input
              max={20}
              min={2}
              onChange={(event) => setTableRows(event.target.valueAsNumber)}
              type="number"
              value={tableRows}
            />
          </label>
          <label>
            Columnas
            <Input
              max={10}
              min={1}
              onChange={(event) => setTableColumns(event.target.valueAsNumber)}
              type="number"
              value={tableColumns}
            />
          </label>
          <label>
            Descripción accesible
            <Input
              maxLength={300}
              onChange={(event) => setTableCaption(event.target.value)}
              value={tableCaption}
            />
          </label>
          <Button
            onClick={() => {
              if (!tableCaption.trim()) {
                setError('La tabla necesita una descripción accesible.');
                return;
              }
              insertionChain(editor)
                .insertTable({
                  cols: tableColumns,
                  rows: tableRows,
                  withHeaderRow: true,
                })
                .updateAttributes('table', { caption: tableCaption.trim() })
                .run();
              setTableOpen(false);
              setTableCaption('');
            }}
            type="button"
          >
            <Table2 /> Insertar tabla
          </Button>
        </section>
      ) : null}

      {mode === 'edit' ? (
        <EditorContent
          className="assessment-rich-editor__canvas"
          editor={editor}
        />
      ) : (
        <div className="assessment-rich-editor__preview">
          <AcademicDocument document={value} />
        </div>
      )}
      {error ? (
        <p className="assessment-rich-editor__error" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}
