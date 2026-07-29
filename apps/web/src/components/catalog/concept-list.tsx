'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { useSetConceptArchived, useUpdateConcept } from '@/lib/catalog/hooks';
import type { components } from '@/lib/api/generated/platform';

type Concept = components['schemas']['Concept'];

export function ConceptList({
  canManage,
  concepts,
  slug,
}: Readonly<{
  canManage: boolean;
  concepts: readonly Concept[];
  slug: string;
}>) {
  const router = useRouter();
  const setArchived = useSetConceptArchived(slug);
  const updateConcept = useUpdateConcept(slug);

  async function setStatus(concept: Concept) {
    try {
      await setArchived.mutateAsync({
        conceptId: concept.id,
        restore: concept.status === 'archived',
      });
      router.refresh();
    } catch {
      // The mutation state renders the safe API message in the list live region.
    }
  }

  return (
    <ul className="mt-6 divide-y rounded-xl border border-slate-200 bg-white">
      {concepts.length ? (
        concepts.map((concept) => (
          <ConceptRow
            canManage={canManage}
            concept={concept}
            key={concept.id}
            onSetStatus={setStatus}
            onUpdate={async (values) => {
              await updateConcept.mutateAsync(values);
              router.refresh();
            }}
            pending={setArchived.isPending || updateConcept.isPending}
          />
        ))
      ) : (
        <li className="p-4 text-slate-600">Aún no hay conceptos activos.</li>
      )}
      <li
        aria-live="polite"
        className="min-h-5 px-4 py-2 text-sm text-slate-700"
      >
        {setArchived.error instanceof Error ? setArchived.error.message : ''}
        {updateConcept.error instanceof Error
          ? updateConcept.error.message
          : ''}
      </li>
    </ul>
  );
}

function ConceptRow({
  canManage,
  concept,
  onSetStatus,
  onUpdate,
  pending,
}: Readonly<{
  canManage: boolean;
  concept: Concept;
  onSetStatus: (concept: Concept) => Promise<void>;
  onUpdate: (values: {
    conceptId: string;
    definition: string;
    name: string;
  }) => Promise<void>;
  pending: boolean;
}>) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(concept.name);
  const [definition, setDefinition] = useState(concept.definition);
  return (
    <li className="flex flex-wrap items-start justify-between gap-4 p-4">
      <div>
        <h2 className="font-semibold">{concept.name}</h2>
        <p className="mt-1 text-slate-700">{concept.definition}</p>
        <p className="mt-2 text-sm text-slate-600">
          {concept.status === 'archived' ? 'Archivado' : 'Activo'}
        </p>
        {canManage && editing ? (
          <div className="mt-3 space-y-2">
            <label className="block text-sm font-medium">
              Editar nombre de {concept.name}
              <input
                className="mt-1 block rounded border border-slate-300 px-2 py-1"
                onChange={(event) => setName(event.target.value)}
                value={name}
              />
            </label>
            <label className="block text-sm font-medium">
              Editar definición de {concept.name}
              <textarea
                className="mt-1 block min-h-20 rounded border border-slate-300 px-2 py-1"
                onChange={(event) => setDefinition(event.target.value)}
                value={definition}
              />
            </label>
            <button
              className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-60"
              disabled={pending || !name.trim() || !definition.trim()}
              onClick={async () => {
                try {
                  await onUpdate({ conceptId: concept.id, definition, name });
                  setEditing(false);
                } catch {
                  // The parent mutation exposes the safe API message.
                }
              }}
              type="button"
            >
              Guardar concepto
            </button>
            <button
              className="ml-2 rounded border border-slate-300 px-2 py-1 text-sm"
              onClick={() => {
                setName(concept.name);
                setDefinition(concept.definition);
                setEditing(false);
              }}
              type="button"
            >
              Cancelar
            </button>
          </div>
        ) : null}
      </div>
      {canManage ? (
        <div className="flex flex-wrap gap-2">
          <button
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium"
            onClick={() => setEditing(true)}
            type="button"
          >
            Editar concepto
          </button>
          <button
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium disabled:opacity-60"
            disabled={pending}
            onClick={() => onSetStatus(concept)}
            type="button"
          >
            {concept.status === 'archived' ? 'Restaurar' : 'Archivar'}
          </button>
        </div>
      ) : null}
    </li>
  );
}
