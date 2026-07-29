'use client';

import { useState } from 'react';

import type { components } from '@/lib/api/generated/platform';
import {
  useReplaceObjectiveConcepts,
  useReplaceTopicConcepts,
} from '@/lib/catalog/hooks';

type Concept = components['schemas']['Concept'];
type Entity = 'objective' | 'topic';

export function ConceptAssociationEditor({
  concepts,
  entity,
  entityId,
  initialIds,
  slug,
}: Readonly<{
  concepts: readonly Concept[];
  entity: Entity;
  entityId: string;
  initialIds: readonly string[];
  slug: string;
}>) {
  const topicMutation = useReplaceTopicConcepts(slug);
  const objectiveMutation = useReplaceObjectiveConcepts(slug);
  const mutation = entity === 'topic' ? topicMutation : objectiveMutation;
  const [selectedIds, setSelectedIds] = useState<string[]>([...initialIds]);
  const selected = selectedIds
    .map((id) => concepts.find((concept) => concept.id === id))
    .filter((concept): concept is Concept => Boolean(concept));
  const available = concepts.filter(
    (concept) => !selectedIds.includes(concept.id),
  );
  const noun = entity === 'topic' ? 'tema' : 'objetivo';

  function move(id: string, offset: number) {
    setSelectedIds((current) => {
      const index = current.indexOf(id);
      const destination = index + offset;
      if (destination < 0 || destination >= current.length) return current;
      const next = [...current];
      const moved = next[index];
      const displaced = next[destination];
      if (!moved || !displaced) return current;
      next[index] = displaced;
      next[destination] = moved;
      return next;
    });
  }

  return (
    <section
      aria-label={`Editor de conceptos del ${noun}`}
      className="mt-5 rounded-xl border border-slate-200 bg-slate-50 p-4"
    >
      <h3 className="font-semibold">Conceptos del {noun}</h3>
      <p className="mt-1 text-sm text-slate-700">
        Añade conceptos y ordena cómo se presentan en este {noun}.
      </p>
      <div
        className="mt-3 flex flex-wrap gap-2"
        aria-label={`Conceptos disponibles del ${noun}`}
        role="group"
      >
        {available.map((concept) => (
          <button
            className="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm"
            key={concept.id}
            onClick={() =>
              setSelectedIds((current) => [...current, concept.id])
            }
            type="button"
          >
            Añadir {concept.name}
          </button>
        ))}
      </div>
      <ol
        className="mt-3 space-y-2"
        aria-label={`Orden de conceptos del ${noun}`}
      >
        {selected.map((concept, index) => (
          <li
            className="flex items-center gap-2 rounded-lg bg-white p-2"
            key={concept.id}
          >
            <span className="min-w-0 flex-1 text-sm font-medium">
              {concept.name}
            </span>
            <button
              aria-label={`Subir ${concept.name}`}
              className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-40"
              disabled={index === 0}
              onClick={() => move(concept.id, -1)}
              type="button"
            >
              ↑
            </button>
            <button
              aria-label={`Bajar ${concept.name}`}
              className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-40"
              disabled={index === selected.length - 1}
              onClick={() => move(concept.id, 1)}
              type="button"
            >
              ↓
            </button>
            <button
              aria-label={`Quitar ${concept.name}`}
              className="rounded border border-slate-300 px-2 py-1 text-sm"
              onClick={() =>
                setSelectedIds((current) =>
                  current.filter((id) => id !== concept.id),
                )
              }
              type="button"
            >
              Quitar
            </button>
          </li>
        ))}
      </ol>
      <button
        className="mt-4 rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate({ conceptIds: selectedIds, entityId })}
        type="button"
      >
        Guardar conceptos
      </button>
      <p aria-live="polite" className="min-h-5 pt-2 text-sm text-slate-700">
        {mutation.isSuccess ? 'Asociaciones guardadas.' : ''}
        {mutation.error instanceof Error ? mutation.error.message : ''}
      </p>
    </section>
  );
}
