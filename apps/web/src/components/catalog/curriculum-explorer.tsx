'use client';

import {
  ArrowRight,
  BookOpen,
  ChevronRight,
  Layers3,
  Network,
  Search,
} from 'lucide-react';
import Link from 'next/link';
import { useRef, useState } from 'react';

import { NamedEntityActions } from '@/components/catalog/named-entity-actions';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';
import type { components } from '@/lib/api/generated/platform';

type Area = components['schemas']['Area'];
type Discipline = components['schemas']['Discipline'];
type Subject = components['schemas']['Subject'];
type EntityKind = 'area' | 'discipline' | 'subject';
type Selection = { id: string; kind: EntityKind };
type StatusFilter = 'active' | 'archived' | 'all';

export function CurriculumExplorer({
  areas,
  canManage,
  disciplines,
  slug,
  subjects,
}: Readonly<{
  areas: readonly Area[];
  canManage: boolean;
  disciplines: readonly Discipline[];
  slug: string;
  subjects: readonly Subject[];
}>) {
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<StatusFilter>('all');
  const [selection, setSelection] = useState<Selection>(() => ({
    id: areas[0]?.id ?? '',
    kind: 'area',
  }));
  const inspectorRef = useRef<HTMLElement>(null);
  const normalizedSearch = search.trim().toLocaleLowerCase('es-CO');
  const matches = (item: { name: string; status: string }) =>
    (status === 'all' || item.status === status) &&
    (!normalizedSearch ||
      item.name.toLocaleLowerCase('es-CO').includes(normalizedSearch));
  const visibleAreas = areas.filter(
    (area) =>
      matches(area) ||
      disciplines.some(
        (discipline) =>
          discipline.area_id === area.id &&
          (matches(discipline) ||
            subjects.some(
              (subject) =>
                subject.discipline_id === discipline.id && matches(subject),
            )),
      ),
  );
  const selected = resolveSelection(selection, areas, disciplines, subjects);

  function selectEntity(nextSelection: Selection) {
    setSelection(nextSelection);
    if (window.matchMedia('(max-width: 1023px)').matches) {
      window.requestAnimationFrame(() => {
        inspectorRef.current?.scrollIntoView({
          behavior: 'smooth',
          block: 'start',
        });
      });
    }
  }

  return (
    <div
      className="overflow-hidden rounded-xl border bg-card shadow-sm"
      data-testid="curriculum-explorer"
    >
      <div className="grid border-b bg-muted/20 lg:grid-cols-[20rem_minmax(0,1fr)]">
        <div className="border-b p-3 lg:border-r lg:border-b-0">
          <div className="relative">
            <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              aria-label="Buscar por nombre"
              className="h-9 bg-background pl-9"
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Buscar en el currículo"
              type="search"
              value={search}
            />
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3">
          <Inventory
            label={areas.length === 1 ? 'área' : 'áreas'}
            value={areas.length}
          />
          <Inventory
            label={disciplines.length === 1 ? 'disciplina' : 'disciplinas'}
            value={disciplines.length}
          />
          <Inventory
            label={subjects.length === 1 ? 'asignatura' : 'asignaturas'}
            value={subjects.length}
          />
          <div className="ml-auto flex items-center gap-2">
            <Label className="text-xs text-muted-foreground" htmlFor="status">
              Estado
            </Label>
            <select
              className="h-8 rounded-md border border-input bg-background px-2 text-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
              id="status"
              onChange={(event) =>
                setStatus(event.target.value as StatusFilter)
              }
              value={status}
            >
              <option value="all">Todos</option>
              <option value="active">Activos</option>
              {canManage ? <option value="archived">Archivados</option> : null}
            </select>
          </div>
        </div>
      </div>

      <div className="grid lg:grid-cols-[20rem_minmax(0,1fr)]">
        <aside
          aria-label="Árbol curricular"
          className="border-b bg-muted/10 lg:border-r lg:border-b-0"
        >
          <div className="flex items-center justify-between border-b px-4 py-3">
            <p className="text-[0.6875rem] font-semibold tracking-[0.1em] text-muted-foreground uppercase">
              Mapa curricular
            </p>
            <span className="text-[0.6875rem] text-muted-foreground">
              Área · disciplina · asignatura
            </span>
          </div>
          {visibleAreas.length ? (
            <div className="max-h-[22rem] overflow-y-auto p-2 lg:max-h-[34rem]">
              {visibleAreas.map((area) => {
                const areaMatches = matches(area);
                const children = disciplines.filter(
                  (discipline) => discipline.area_id === area.id,
                );
                return (
                  <div className="mb-1" key={area.id}>
                    <TreeItem
                      active={
                        selection.kind === 'area' && selection.id === area.id
                      }
                      depth={0}
                      icon={Layers3}
                      label={area.name}
                      onSelect={() =>
                        selectEntity({ id: area.id, kind: 'area' })
                      }
                      status={area.status}
                    />
                    {children.map((discipline) => {
                      const disciplineMatches = matches(discipline);
                      const disciplineSubjects = subjects.filter(
                        (subject) =>
                          subject.discipline_id === discipline.id &&
                          (areaMatches ||
                            disciplineMatches ||
                            matches(subject)),
                      );
                      if (
                        !areaMatches &&
                        !disciplineMatches &&
                        disciplineSubjects.length === 0
                      )
                        return null;
                      return (
                        <div key={discipline.id}>
                          <TreeItem
                            active={
                              selection.kind === 'discipline' &&
                              selection.id === discipline.id
                            }
                            depth={1}
                            icon={Network}
                            label={discipline.name}
                            onSelect={() =>
                              selectEntity({
                                id: discipline.id,
                                kind: 'discipline',
                              })
                            }
                            status={discipline.status}
                          />
                          {disciplineSubjects.map((subject) => (
                            <TreeItem
                              active={
                                selection.kind === 'subject' &&
                                selection.id === subject.id
                              }
                              depth={2}
                              icon={BookOpen}
                              key={subject.id}
                              label={subject.name}
                              onSelect={() =>
                                selectEntity({
                                  id: subject.id,
                                  kind: 'subject',
                                })
                              }
                              status={subject.status}
                            />
                          ))}
                        </div>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="p-8 text-center">
              <Search className="mx-auto size-5 text-muted-foreground" />
              <p className="mt-3 text-sm font-medium">Sin coincidencias</p>
              <p className="mt-1 text-xs text-muted-foreground">
                Ajusta el nombre o el estado.
              </p>
            </div>
          )}
        </aside>

        <section
          aria-live="polite"
          className="min-w-0 scroll-mt-20"
          data-testid="curriculum-inspector"
          ref={inspectorRef}
        >
          {selected ? (
            <EntityInspector
              areas={areas}
              canManage={canManage}
              disciplines={disciplines}
              entity={selected.entity}
              kind={selected.kind}
              onSelect={selectEntity}
              slug={slug}
              subjects={subjects}
            />
          ) : (
            <div className="grid min-h-[30rem] place-items-center p-8 text-center">
              <div>
                <Layers3 className="mx-auto size-6 text-muted-foreground" />
                <p className="mt-3 font-medium">
                  Selecciona un elemento curricular
                </p>
                <p className="mt-1 text-sm text-muted-foreground">
                  Consulta su contexto, relaciones y acciones disponibles.
                </p>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function EntityInspector({
  areas,
  canManage,
  disciplines,
  entity,
  kind,
  onSelect,
  slug,
  subjects,
}: Readonly<{
  areas: readonly Area[];
  canManage: boolean;
  disciplines: readonly Discipline[];
  entity: Area | Discipline | Subject;
  kind: EntityKind;
  onSelect: (selection: Selection) => void;
  slug: string;
  subjects: readonly Subject[];
}>) {
  const area =
    kind === 'area'
      ? (entity as Area)
      : kind === 'discipline'
        ? areas.find((item) => item.id === (entity as Discipline).area_id)
        : areas.find(
            (item) =>
              item.id ===
              disciplines.find(
                (discipline) =>
                  discipline.id === (entity as Subject).discipline_id,
              )?.area_id,
          );
  const discipline =
    kind === 'discipline'
      ? (entity as Discipline)
      : kind === 'subject'
        ? disciplines.find(
            (item) => item.id === (entity as Subject).discipline_id,
          )
        : undefined;
  const related =
    kind === 'area'
      ? disciplines.filter((item) => item.area_id === (entity as Area).id)
      : kind === 'discipline'
        ? subjects.filter(
            (item) => item.discipline_id === (entity as Discipline).id,
          )
        : [];
  const kindLabel =
    kind === 'area'
      ? 'Área de conocimiento'
      : kind === 'discipline'
        ? 'Disciplina'
        : 'Asignatura';
  const EntityIcon =
    kind === 'area' ? Layers3 : kind === 'discipline' ? Network : BookOpen;

  return (
    <div>
      <header className="border-b px-5 py-4 sm:px-6 sm:py-5">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start">
          <div className="flex min-w-0 flex-1 items-start gap-3">
            <div className="mt-0.5 grid size-10 shrink-0 place-items-center rounded-lg border bg-muted/30 text-primary shadow-xs">
              <EntityIcon className="size-4" />
            </div>
            <div className="min-w-0">
              <p className="text-[0.6875rem] font-semibold tracking-[0.1em] text-primary uppercase">
                {kindLabel}
              </p>
              <div className="mt-1.5 flex flex-wrap items-center gap-2.5">
                <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">
                  {entity.name}
                </h2>
                <StatusLabel status={entity.status} />
              </div>
              <p className="mt-1.5 max-w-3xl text-sm leading-6 text-muted-foreground">
                {entity.description ||
                  'Esta entidad no tiene una descripción institucional.'}
              </p>
            </div>
          </div>
          {canManage ? (
            <NamedEntityActions entity={entity} kind={kind} slug={slug} />
          ) : null}
        </div>
      </header>

      <div className="p-5 sm:p-6">
        <div className="flex items-baseline justify-between gap-3">
          <h3 className="text-sm font-semibold">
            {kind === 'subject'
              ? 'Ruta curricular'
              : kind === 'area'
                ? 'Disciplinas'
                : 'Asignaturas'}
          </h3>
          {kind !== 'subject' && related.length ? (
            <span className="text-xs text-muted-foreground">
              Selecciona para explorar
            </span>
          ) : null}
        </div>
        {kind === 'subject' ? (
          <Hierarchy area={area} discipline={discipline} entity={entity} />
        ) : related.length ? (
          <ul className="mt-3 grid gap-2 sm:grid-cols-2 2xl:grid-cols-3">
            {related.map((item) => {
              const itemKind =
                kind === 'area'
                  ? ('discipline' as const)
                  : ('subject' as const);
              return (
                <li key={item.id}>
                  <button
                    className="group flex min-h-14 w-full items-center gap-3 rounded-lg border bg-background px-3 py-2.5 text-left shadow-xs transition-[border-color,box-shadow,color] hover:border-primary/35 hover:text-primary hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    onClick={() => onSelect({ id: item.id, kind: itemKind })}
                    type="button"
                  >
                    {kind === 'area' ? (
                      <Network className="size-4 text-muted-foreground group-hover:text-primary" />
                    ) : (
                      <BookOpen className="size-4 text-muted-foreground group-hover:text-primary" />
                    )}
                    <span className="min-w-0 flex-1 text-sm font-medium">
                      {item.name}
                    </span>
                    <StatusLabel status={item.status} />
                    <ChevronRight className="size-4 text-muted-foreground" />
                  </button>
                </li>
              );
            })}
          </ul>
        ) : (
          <p className="mt-3 rounded-lg border border-dashed bg-muted/10 px-4 py-5 text-sm text-muted-foreground">
            No hay entidades vinculadas en este nivel.
          </p>
        )}

        {kind === 'subject' ? (
          <Button asChild className="mt-4">
            <Link
              href={`/organizaciones/${slug}/curriculo/asignaturas/${entity.id}`}
            >
              Abrir asignatura
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        ) : null}
      </div>
    </div>
  );
}

function Hierarchy({
  area,
  discipline,
  entity,
}: Readonly<{
  area?: Area | undefined;
  discipline?: Discipline | undefined;
  entity: Area | Discipline | Subject;
}>) {
  return (
    <ol className="mt-3 flex flex-wrap items-center gap-2 rounded-lg border bg-muted/15 px-4 py-3 text-sm">
      <li className="font-medium">{area?.name ?? 'Área no disponible'}</li>
      <li aria-hidden="true">
        <ChevronRight className="size-4 text-muted-foreground" />
      </li>
      <li className="font-medium">
        {discipline?.name ?? 'Disciplina no disponible'}
      </li>
      <li aria-hidden="true">
        <ChevronRight className="size-4 text-muted-foreground" />
      </li>
      <li className="font-semibold text-primary">{entity.name}</li>
    </ol>
  );
}

function Inventory({
  label,
  value,
}: Readonly<{ label: string; value: number }>) {
  return (
    <p className="text-xs text-muted-foreground">
      <span className="mr-1.5 font-mono font-semibold text-foreground">
        {value}
      </span>
      {label}
    </p>
  );
}

function resolveSelection(
  selection: Selection,
  areas: readonly Area[],
  disciplines: readonly Discipline[],
  subjects: readonly Subject[],
) {
  if (selection.kind === 'area') {
    const entity = areas.find((item) => item.id === selection.id);
    return entity ? { entity, kind: selection.kind } : null;
  }
  if (selection.kind === 'discipline') {
    const entity = disciplines.find((item) => item.id === selection.id);
    return entity ? { entity, kind: selection.kind } : null;
  }
  const entity = subjects.find((item) => item.id === selection.id);
  return entity ? { entity, kind: selection.kind } : null;
}

function StatusLabel({ status }: Readonly<{ status: string }>) {
  return (
    <Badge
      className="h-5 rounded px-1.5 font-normal"
      variant={status === 'archived' ? 'outline' : 'secondary'}
    >
      {statusText(status)}
    </Badge>
  );
}

function TreeItem({
  active,
  depth,
  icon: Icon,
  label,
  onSelect,
  status,
}: Readonly<{
  active: boolean;
  depth: 0 | 1 | 2;
  icon: typeof Layers3;
  label: string;
  onSelect: () => void;
  status: string;
}>) {
  return (
    <button
      aria-pressed={active}
      className={cn(
        'flex h-9 w-full items-center gap-2 rounded-md pr-2 text-left text-sm transition-colors hover:bg-muted focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
        depth === 0 && 'pl-2 font-semibold',
        depth === 1 && 'pl-7 font-medium',
        depth === 2 && 'pl-12 text-muted-foreground',
        active && 'bg-primary text-primary-foreground hover:bg-primary',
      )}
      onClick={onSelect}
      type="button"
    >
      <Icon
        className={cn(
          'size-3.5 shrink-0',
          active ? 'text-primary-foreground' : 'text-muted-foreground',
        )}
      />
      <span className="min-w-0 flex-1 truncate">{label}</span>
      {status === 'archived' ? (
        <span className="size-1.5 rounded-full bg-muted-foreground" />
      ) : null}
    </button>
  );
}

function statusText(status: string) {
  return status === 'archived' ? 'Archivado' : 'Activo';
}
