'use client';

import {
  ArrowDown,
  ArrowUp,
  LoaderCircle,
  Plus,
  Save,
  Search,
  X,
} from 'lucide-react';
import { useDeferredValue, useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import type { components } from '@/lib/api/generated/platform';
import {
  useCatalogConceptSearch,
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
  const [search, setSearch] = useState('');
  const deferredSearch = useDeferredValue(search);
  const searchQuery = useCatalogConceptSearch(slug, deferredSearch);
  const indexedConcepts = useMemo(
    () =>
      new Map(
        [...concepts, ...(searchQuery.data ?? [])].map((concept) => [
          concept.id,
          concept,
        ]),
      ),
    [concepts, searchQuery.data],
  );
  const selected = selectedIds
    .map((id) => indexedConcepts.get(id))
    .filter((concept): concept is Concept => Boolean(concept));
  const available = (searchQuery.data ?? concepts.slice(0, 20)).filter(
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

  const editor = (
    <div className={embedded ? '' : 'border-t px-4 py-4'}>
      <label className="relative block max-w-md">
        <span className="sr-only">Buscar concepto para asociar</span>
        <Search className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" />
        <Input
          className="h-9 pl-9"
          onChange={(event) => setSearch(event.target.value)}
          placeholder="Buscar concepto institucional"
          value={search}
        />
      </label>
      <div
        className="mt-2 flex max-h-28 flex-wrap gap-1.5 overflow-y-auto"
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
        {searchQuery.isLoading ? (
          <span className="inline-flex items-center gap-2 px-2 text-xs text-muted-foreground">
            <LoaderCircle className="size-3.5 animate-spin" /> Buscando…
          </span>
        ) : null}
        {!searchQuery.isLoading && available.length === 0 ? (
          <span className="px-2 py-1 text-xs text-muted-foreground">
            No hay conceptos disponibles con este criterio.
          </span>
        ) : null}
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
    </div>
  );

  if (embedded) {
    return (
      <section
        aria-label={`Editor de conceptos del ${noun}`}
        className="border-t bg-muted/15 px-4 py-4"
      >
        <div className="mb-3 flex items-baseline justify-between gap-2">
          <h3 className="text-sm font-semibold">Conceptos del {noun}</h3>
          <span className="text-xs text-muted-foreground">
            {selected.length} asociados
          </span>
        </div>
        {editor}
      </section>
    );
  }

  return (
    <details
      aria-label={`Editor de conceptos del ${noun}`}
      className="mt-3 rounded-lg border bg-muted/10 open:bg-background"
    >
      <summary className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2.5 text-sm font-medium">
        <span>Conceptos asociados</span>
        <span className="text-xs font-normal text-muted-foreground">
          {selected.length}
        </span>
      </summary>
      {editor}
    </details>
  );
}
