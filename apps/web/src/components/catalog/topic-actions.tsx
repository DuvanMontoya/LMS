'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import {
  useMoveTopic,
  useSetTopicArchived,
  useUpdateTopic,
} from '@/lib/catalog/hooks';

export function TopicActions({
  slug,
  topic,
  topics,
}: Readonly<{
  slug: string;
  topic: {
    id: string;
    parentId?: string | undefined;
    status?: string;
    title: string;
  };
  topics: ReadonlyArray<{
    ancestorIds: readonly string[];
    id: string;
    parentId?: string | undefined;
    title: string;
  }>;
}>) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(topic.title);
  const [targetId, setTargetId] = useState('');
  const move = useMoveTopic(slug);
  const archive = useSetTopicArchived(slug);
  const update = useUpdateTopic(slug);
  const isArchived = topic.status === 'archived';
  const siblings = topics.filter(
    (candidate) => candidate.parentId === topic.parentId,
  );
  const siblingIndex = siblings.findIndex(
    (candidate) => candidate.id === topic.id,
  );
  const previousSibling = siblings[siblingIndex - 1];
  const nextSibling = siblings[siblingIndex + 1];
  const canTarget = (candidate: (typeof topics)[number]) =>
    candidate.id !== topic.id && !candidate.ancestorIds.includes(topic.id);

  async function moveTopic(
    targetId: string,
    position: 'left' | 'right' | 'last-child',
  ) {
    try {
      await move.mutateAsync({ position, targetId, topicId: topic.id });
      router.refresh();
    } catch {
      // The mutation state renders the safe server message in the live region.
    }
  }
  async function moveUnderTarget() {
    if (!targetId) return;
    await moveTopic(targetId, 'last-child');
  }
  async function changeArchive() {
    if (
      !isArchived &&
      !window.confirm(`¿Archivar ${topic.title} y sus descendientes?`)
    ) {
      return;
    }
    try {
      await archive.mutateAsync({ restore: isArchived, topicId: topic.id });
      router.refresh();
    } catch {
      // The mutation state renders the safe server message in the live region.
    }
  }
  async function saveTitle() {
    try {
      await update.mutateAsync({ title, topicId: topic.id });
      setEditing(false);
      router.refresh();
    } catch {
      // The mutation state renders the safe server message in the live region.
    }
  }
  return (
    <fieldset className="mt-2 flex flex-wrap items-end gap-2 rounded-lg border border-slate-200 p-2">
      <legend className="px-1 text-xs font-medium">
        Acciones de {topic.title}
      </legend>
      {editing ? (
        <label className="text-xs">
          Editar título de {topic.title}
          <input
            className="ml-1 rounded border border-slate-300 p-1"
            onChange={(event) => setTitle(event.target.value)}
            value={title}
          />
        </label>
      ) : (
        <button
          className="rounded border border-slate-300 px-2 py-1 text-sm"
          onClick={() => setEditing(true)}
          type="button"
        >
          Editar tema
        </button>
      )}
      {editing ? (
        <>
          <button
            className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
            disabled={update.isPending || !title.trim()}
            onClick={saveTitle}
            type="button"
          >
            Guardar tema
          </button>
          <button
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            onClick={() => {
              setTitle(topic.title);
              setEditing(false);
            }}
            type="button"
          >
            Cancelar
          </button>
        </>
      ) : null}
      <label className="text-xs">
        Mover bajo
        <select
          className="ml-1 rounded border border-slate-300 p-1"
          onChange={(event) => setTargetId(event.target.value)}
          value={targetId}
        >
          <option value="">Selecciona un tema</option>
          {topics.filter(canTarget).map((candidate) => (
            <option key={candidate.id} value={candidate.id}>
              {candidate.title}
            </option>
          ))}
        </select>
      </label>
      <button
        className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
        disabled={!targetId || move.isPending}
        onClick={moveUnderTarget}
        type="button"
      >
        Mover como hijo
      </button>
      <button
        className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
        disabled={!previousSibling || move.isPending}
        onClick={() => previousSibling && moveTopic(previousSibling.id, 'left')}
        type="button"
      >
        Subir
      </button>
      <button
        className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
        disabled={!nextSibling || move.isPending}
        onClick={() => nextSibling && moveTopic(nextSibling.id, 'right')}
        type="button"
      >
        Bajar
      </button>
      <button
        className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
        disabled={!topic.parentId || move.isPending}
        onClick={() => topic.parentId && moveTopic(topic.parentId, 'right')}
        type="button"
      >
        Reducir nivel
      </button>
      <button
        className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
        disabled={archive.isPending}
        onClick={changeArchive}
        type="button"
      >
        {isArchived ? 'Restaurar tema' : 'Archivar tema'}
      </button>
      <span aria-live="polite" className="text-sm text-slate-700">
        {move.error instanceof Error ? move.error.message : ''}
        {archive.error instanceof Error ? archive.error.message : ''}
        {update.error instanceof Error ? update.error.message : ''}
      </span>
    </fieldset>
  );
}
