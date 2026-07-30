'use client';

import { ArrowDown, ArrowUp, LoaderCircle, Plus, Save, X } from 'lucide-react';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
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
  embedded = false,
  slug,
}: Readonly<{
  concepts: readonly Concept[];
  embedded?: boolean;
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
      className={
        embedded
          ? 'border-t bg-muted/15 px-4 py-4'
          : 'mt-4 rounded-md border bg-muted/15 p-4'
      }
    >
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="text-sm font-semibold">Conceptos del {noun}</h3>
        <span className="text-xs text-muted-foreground">
          {selected.length} asociados
        </span>
      </div>
      <div
        className="mt-3 flex flex-wrap gap-1.5"
        aria-label={`Conceptos disponibles del ${noun}`}
        role="group"
      >
        {available.map((concept) => (
          <Button
            key={concept.id}
            onClick={() =>
              setSelectedIds((current) => [...current, concept.id])
            }
            size="sm"
            type="button"
            variant="outline"
          >
            <Plus />
            Añadir {concept.name}
          </Button>
        ))}
      </div>
      <ol
        className="mt-3 divide-y border-y"
        aria-label={`Orden de conceptos del ${noun}`}
      >
        {selected.map((concept, index) => (
          <li
            className="flex min-h-11 items-center gap-2 px-1.5 py-1.5"
            key={concept.id}
          >
            <span className="min-w-0 flex-1 text-sm font-medium">
              {concept.name}
            </span>
            <Button
              aria-label={`Subir ${concept.name}`}
              disabled={index === 0}
              onClick={() => move(concept.id, -1)}
              size="icon-sm"
              title="Subir"
              type="button"
              variant="ghost"
            >
              <ArrowUp />
            </Button>
            <Button
              aria-label={`Bajar ${concept.name}`}
              disabled={index === selected.length - 1}
              onClick={() => move(concept.id, 1)}
              size="icon-sm"
              title="Bajar"
              type="button"
              variant="ghost"
            >
              <ArrowDown />
            </Button>
            <Button
              aria-label={`Quitar ${concept.name}`}
              onClick={() =>
                setSelectedIds((current) =>
                  current.filter((id) => id !== concept.id),
                )
              }
              size="icon-sm"
              title="Quitar"
              type="button"
              variant="ghost"
            >
              <X />
            </Button>
          </li>
        ))}
      </ol>
      <Button
        className="mt-3"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate({ conceptIds: selectedIds, entityId })}
        size="sm"
        type="button"
      >
        {mutation.isPending ? (
          <LoaderCircle className="animate-spin" />
        ) : (
          <Save />
        )}
        Guardar conceptos
      </Button>
      <p
        aria-live="polite"
        className="min-h-5 pt-2 text-xs text-muted-foreground"
      >
        {mutation.isSuccess ? 'Asociaciones guardadas.' : ''}
        {mutation.error instanceof Error ? mutation.error.message : ''}
      </p>
    </section>
  );
}
