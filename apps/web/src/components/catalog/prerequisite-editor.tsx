'use client';

import { ArrowRight, LoaderCircle, Plus, Save, Search, X } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  useCatalogConceptSearch,
  useReplaceConceptPrerequisites,
  useReplaceSubjectPrerequisites,
} from '@/lib/catalog/hooks';
import type { components } from '@/lib/api/generated/platform';

type EntityKind = 'concept' | 'subject';
type Item = Pick<components['schemas']['Concept'], 'id' | 'name'>;
type Link = components['schemas']['SubjectPrerequisite'];

export function PrerequisiteEditor({
  dependentItems,
  entity,
  initialLinks,
  items,
  slug,
  target,
}: Readonly<{
  dependentItems: readonly Item[];
  entity: EntityKind;
  initialLinks: readonly Link[];
  items: readonly Item[];
  slug: string;
  target: Item;
}>) {
  const router = useRouter();
  const conceptMutation = useReplaceConceptPrerequisites(slug);
  const subjectMutation = useReplaceSubjectPrerequisites(slug);
  const mutation = entity === 'concept' ? conceptMutation : subjectMutation;
  const [links, setLinks] = useState<Link[]>([...initialLinks]);
  const [search, setSearch] = useState('');
  const conceptSearch = useCatalogConceptSearch(slug, search);
  const selectedIds = useMemo(
    () => new Set(links.map((link) => link.prerequisite_id)),
    [links],
  );
  const candidates = useMemo(() => {
    const normalized = search.trim().toLocaleLowerCase('es');
    if (!normalized) return [];
    const source = entity === 'concept' ? (conceptSearch.data ?? []) : items;
    return source
      .filter(
        (item) =>
          item.id !== target.id &&
          !selectedIds.has(item.id) &&
          item.name.toLocaleLowerCase('es').includes(normalized),
      )
      .slice(0, 12);
  }, [conceptSearch.data, entity, items, search, selectedIds, target.id]);
  const itemById = new Map(
    [...items, ...(conceptSearch.data ?? [])].map((item) => [item.id, item]),
  );

  function updateLink(prerequisiteId: string, values: Partial<Link>) {
    setLinks((current) =>
      current.map((link) =>
        link.prerequisite_id === prerequisiteId ? { ...link, ...values } : link,
      ),
    );
  }

  async function save() {
    try {
      if (entity === 'concept') {
        await conceptMutation.mutateAsync({
          entityId: target.id,
          prerequisites: links,
        });
      } else {
        await subjectMutation.mutateAsync({
          prerequisites: links,
          subjectId: target.id,
        });
      }
      router.refresh();
    } catch {
      // The mutation exposes the safe API message in the live region.
    }
  }

  return (
    <section className="rounded-xl border bg-background shadow-xs">
      <header className="flex flex-col gap-2 border-b px-4 py-4 sm:flex-row sm:items-start sm:justify-between sm:px-5">
        <div>
          <p className="text-[0.6875rem] font-semibold tracking-[0.1em] text-primary uppercase">
            {entity === 'concept' ? 'Grafo conceptual' : 'Ruta académica'}
          </p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight">
            Prerrequisitos de {target.name}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            {links.length} dependencias directas · {dependentItems.length}{' '}
            relaciones inversas
          </p>
        </div>
        <Button
          disabled={mutation.isPending}
          onClick={() => void save()}
          size="sm"
          type="button"
        >
          {mutation.isPending ? (
            <LoaderCircle className="animate-spin" />
          ) : (
            <Save />
          )}
          Guardar cambios
        </Button>
      </header>

      <div className="grid gap-5 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(18rem,0.42fr)] lg:p-5">
        <div>
          <div className="flex items-center justify-between gap-2">
            <h3 className="text-sm font-semibold">Requiere</h3>
            <span className="text-xs text-muted-foreground">
              {links.length} seleccionados
            </span>
          </div>
          <div className="mt-2 grid gap-2">
            {links.length ? (
              links.map((link) => {
                const item = itemById.get(link.prerequisite_id);
                return (
                  <article
                    className="rounded-lg border bg-muted/10 p-3"
                    key={link.prerequisite_id}
                  >
                    <div className="flex items-center gap-2">
                      <span className="min-w-0 flex-1 text-sm font-semibold">
                        {item?.name ?? 'Entidad no disponible'}
                      </span>
                      <Button
                        aria-label={`Quitar ${item?.name ?? 'prerrequisito'}`}
                        onClick={() =>
                          setLinks((current) =>
                            current.filter(
                              (candidate) =>
                                candidate.prerequisite_id !==
                                link.prerequisite_id,
                            ),
                          )
                        }
                        size="icon-sm"
                        title="Quitar"
                        type="button"
                        variant="ghost"
                      >
                        <X />
                      </Button>
                    </div>
                    <div className="mt-2 grid gap-2 sm:grid-cols-[10rem_1fr]">
                      <label className="academic-field">
                        Tipo
                        <select
                          className="academic-control h-9"
                          onChange={(event) =>
                            updateLink(link.prerequisite_id, {
                              kind: event.target.value as Link['kind'],
                            })
                          }
                          value={link.kind}
                        >
                          <option value="required">Obligatorio</option>
                          <option value="recommended">Recomendado</option>
                        </select>
                      </label>
                      <label className="academic-field">
                        Justificación
                        <Input
                          className="h-9"
                          onChange={(event) =>
                            updateLink(link.prerequisite_id, {
                              rationale: event.target.value,
                            })
                          }
                          placeholder="Por qué se necesita"
                          value={link.rationale ?? ''}
                        />
                      </label>
                    </div>
                  </article>
                );
              })
            ) : (
              <div className="rounded-lg border border-dashed px-4 py-7 text-center text-sm text-muted-foreground">
                No tiene prerrequisitos directos.
              </div>
            )}
          </div>

          <div className="mt-4 rounded-lg border p-3">
            <label className="relative block">
              <span className="sr-only">Buscar prerrequisito para añadir</span>
              <Search className="pointer-events-none absolute top-2.5 left-3 size-4 text-muted-foreground" />
              <Input
                className="h-9 pl-9"
                onChange={(event) => setSearch(event.target.value)}
                placeholder={`Buscar ${entity === 'concept' ? 'concepto' : 'asignatura'} para añadir`}
                value={search}
              />
            </label>
            {search.trim() ? (
              <div className="mt-2 grid max-h-52 gap-1 overflow-y-auto">
                {candidates.length ? (
                  candidates.map((item) => (
                    <button
                      className="flex min-h-9 items-center justify-between rounded-md px-2 text-left text-sm hover:bg-muted"
                      key={item.id}
                      onClick={() => {
                        setLinks((current) => [
                          ...current,
                          {
                            kind: 'required',
                            prerequisite_id: item.id,
                          },
                        ]);
                      }}
                      type="button"
                    >
                      {item.name}
                      <Plus className="size-4 text-primary" />
                    </button>
                  ))
                ) : (
                  <p className="px-2 py-3 text-xs text-muted-foreground">
                    Sin coincidencias disponibles.
                  </p>
                )}
              </div>
            ) : (
              <p className="mt-2 text-xs text-muted-foreground">
                Escribe para buscar. No se muestran cientos de opciones sin
                intención.
              </p>
            )}
          </div>
        </div>

        <aside className="rounded-lg border bg-muted/15 p-4">
          <h3 className="text-sm font-semibold">Es requisito de</h3>
          <p className="mt-1 text-xs text-muted-foreground">
            Dependencias inversas calculadas desde el grafo actual.
          </p>
          <ul className="mt-3 grid gap-2">
            {dependentItems.length ? (
              dependentItems.map((item) => (
                <li
                  className="flex items-center gap-2 rounded-md bg-background px-3 py-2 text-sm font-medium shadow-xs"
                  key={item.id}
                >
                  <ArrowRight className="size-4 text-primary" />
                  {item.name}
                </li>
              ))
            ) : (
              <li className="text-sm text-muted-foreground">
                Sin dependencias inversas.
              </li>
            )}
          </ul>
        </aside>
      </div>
      <p
        aria-live="polite"
        className="min-h-5 border-t px-5 py-2 text-xs text-muted-foreground"
      >
        {mutation.isSuccess ? 'Prerrequisitos guardados.' : ''}
        {mutation.error instanceof Error ? mutation.error.message : ''}
      </p>
    </section>
  );
}
