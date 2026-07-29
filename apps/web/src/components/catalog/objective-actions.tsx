'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import {
  useSetObjectiveArchived,
  useUpdateObjective,
} from '@/lib/catalog/hooks';
import type { components } from '@/lib/api/generated/platform';

type Objective = components['schemas']['Objective'];

export function ObjectiveActions({
  objective,
  slug,
}: Readonly<{ objective: Objective; slug: string }>) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [statement, setStatement] = useState(objective.statement);
  const update = useUpdateObjective(slug);
  const archive = useSetObjectiveArchived(slug);
  const isArchived = objective.status === 'archived';

  async function save() {
    try {
      await update.mutateAsync({ objectiveId: objective.id, statement });
      setEditing(false);
      router.refresh();
    } catch {
      // The API message is rendered below without exposing transport details.
    }
  }

  async function setStatus() {
    if (!isArchived && !window.confirm(`¿Archivar ${objective.code}?`)) return;
    try {
      await archive.mutateAsync({
        objectiveId: objective.id,
        restore: isArchived,
      });
      router.refresh();
    } catch {
      // The API message is rendered below without exposing transport details.
    }
  }

  return (
    <section
      aria-label={`Acciones de ${objective.code}`}
      className="mt-4 space-y-3"
    >
      {editing ? (
        <>
          <label className="block text-sm font-medium">
            Editar enunciado de {objective.code}
            <textarea
              className="mt-1 block min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2"
              onChange={(event) => setStatement(event.target.value)}
              value={statement}
            />
          </label>
          <div className="flex gap-2">
            <button
              className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white disabled:opacity-60"
              disabled={update.isPending || !statement.trim()}
              onClick={save}
              type="button"
            >
              Guardar cambios
            </button>
            <button
              className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium"
              onClick={() => {
                setStatement(objective.statement);
                setEditing(false);
              }}
              type="button"
            >
              Cancelar
            </button>
          </div>
        </>
      ) : (
        <button
          className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium"
          onClick={() => setEditing(true)}
          type="button"
        >
          Editar objetivo
        </button>
      )}
      <button
        className="ml-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium disabled:opacity-60"
        disabled={archive.isPending}
        onClick={setStatus}
        type="button"
      >
        {isArchived ? 'Restaurar objetivo' : 'Archivar objetivo'}
      </button>
      <p aria-live="polite" className="text-sm text-slate-700">
        {update.error instanceof Error ? update.error.message : ''}
        {archive.error instanceof Error ? archive.error.message : ''}
      </p>
    </section>
  );
}
