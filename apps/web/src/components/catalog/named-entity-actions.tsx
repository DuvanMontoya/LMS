'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import {
  useSetNamedEntityArchived,
  useUpdateNamedEntity,
} from '@/lib/catalog/hooks';

type NamedEntityKind = 'area' | 'discipline' | 'subject';

export function NamedEntityActions({
  entity,
  kind,
  slug,
}: Readonly<{
  entity: { id: string; name: string; status: string };
  kind: NamedEntityKind;
  slug: string;
}>) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(entity.name);
  const update = useUpdateNamedEntity(slug);
  const archive = useSetNamedEntityArchived(slug);
  const noun =
    kind === 'area'
      ? 'área'
      : kind === 'discipline'
        ? 'disciplina'
        : 'asignatura';
  const isArchived = entity.status === 'archived';

  async function save() {
    try {
      await update.mutateAsync({ entityId: entity.id, kind, name });
      setEditing(false);
      router.refresh();
    } catch {
      // The API message below is safer than exposing transport details.
    }
  }

  async function setStatus() {
    if (!isArchived && !window.confirm(`¿Archivar ${noun} ${entity.name}?`))
      return;
    try {
      await archive.mutateAsync({
        entityId: entity.id,
        kind,
        restore: isArchived,
      });
      router.refresh();
    } catch {
      // The API message below is safer than exposing transport details.
    }
  }

  return (
    <section
      aria-label={`Acciones de ${entity.name}`}
      className="mt-2 space-y-2"
    >
      {editing ? (
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-sm font-medium">
            Editar nombre de {entity.name}
            <input
              className="mt-1 block rounded border border-slate-300 px-2 py-1"
              onChange={(event) => setName(event.target.value)}
              value={name}
            />
          </label>
          <button
            className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-60"
            disabled={update.isPending || !name.trim()}
            onClick={save}
            type="button"
          >
            Guardar nombre
          </button>
          <button
            className="rounded border border-slate-300 px-2 py-1 text-sm"
            onClick={() => {
              setName(entity.name);
              setEditing(false);
            }}
            type="button"
          >
            Cancelar
          </button>
        </div>
      ) : (
        <button
          className="rounded border border-slate-300 px-2 py-1 text-sm"
          onClick={() => setEditing(true)}
          type="button"
        >
          Editar {noun}
        </button>
      )}
      <button
        className="ml-2 rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-60"
        disabled={archive.isPending}
        onClick={setStatus}
        type="button"
      >
        {isArchived ? `Restaurar ${noun}` : `Archivar ${noun}`}
      </button>
      <p aria-live="polite" className="text-sm text-slate-700">
        {update.error instanceof Error ? update.error.message : ''}
        {archive.error instanceof Error ? archive.error.message : ''}
      </p>
    </section>
  );
}
