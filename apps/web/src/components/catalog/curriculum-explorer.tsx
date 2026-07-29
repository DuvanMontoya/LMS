'use client';

import Link from 'next/link';
import { useState } from 'react';

import { NamedEntityActions } from '@/components/catalog/named-entity-actions';
import type { components } from '@/lib/api/generated/platform';

type Area = components['schemas']['Area'];
type Discipline = components['schemas']['Discipline'];
type Subject = components['schemas']['Subject'];
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
  return (
    <>
      <div
        aria-label="Resumen curricular"
        className="mt-6 grid gap-3 sm:grid-cols-3"
      >
        <Count label="Áreas" value={areas.length} />
        <Count label="Disciplinas" value={disciplines.length} />
        <Count label="Asignaturas" value={subjects.length} />
      </div>
      <fieldset className="mt-6 flex flex-wrap gap-4 rounded-lg bg-slate-50 p-4">
        <legend className="px-1 text-sm font-medium text-slate-800">
          Explorar la estructura
        </legend>
        <label className="min-w-56 flex-1 text-sm font-medium text-slate-800">
          Buscar por nombre
          <input
            className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2"
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Área, disciplina o asignatura"
            type="search"
            value={search}
          />
        </label>
        <label className="text-sm font-medium text-slate-800">
          Estado
          <select
            className="mt-1 block rounded-lg border border-slate-300 bg-white px-3 py-2"
            onChange={(event) => setStatus(event.target.value as StatusFilter)}
            value={status}
          >
            <option value="all">Todos</option>
            <option value="active">Activos</option>
            {canManage ? <option value="archived">Archivados</option> : null}
          </select>
        </label>
      </fieldset>
      {visibleAreas.length === 0 ? (
        <p className="mt-5 text-slate-600">
          No hay coincidencias con los filtros seleccionados.
        </p>
      ) : (
        <ul className="mt-5 space-y-5">
          {visibleAreas.map((area) => {
            const areaMatches = matches(area);
            const areaDisciplines = disciplines.filter(
              (discipline) => discipline.area_id === area.id,
            );
            return (
              <li
                key={area.id}
                className="rounded-lg border border-slate-200 p-4"
              >
                <h3 className="font-semibold text-slate-950">
                  {area.name} <StatusLabel status={area.status} />
                </h3>
                {canManage ? (
                  <NamedEntityActions entity={area} kind="area" slug={slug} />
                ) : null}
                <ul className="mt-3 space-y-3 border-l border-slate-200 pl-4">
                  {areaDisciplines.map((discipline) => {
                    const disciplineMatches = matches(discipline);
                    const disciplineSubjects = subjects.filter(
                      (subject) => subject.discipline_id === discipline.id,
                    );
                    if (
                      !areaMatches &&
                      !disciplineMatches &&
                      !disciplineSubjects.some(matches)
                    ) {
                      return null;
                    }
                    return (
                      <li key={discipline.id}>
                        <p className="font-medium text-slate-800">
                          {discipline.name}{' '}
                          <StatusLabel status={discipline.status} />
                        </p>
                        {canManage ? (
                          <NamedEntityActions
                            entity={discipline}
                            kind="discipline"
                            slug={slug}
                          />
                        ) : null}
                        <ul className="mt-2 space-y-1 pl-4">
                          {disciplineSubjects
                            .filter(
                              (subject) =>
                                areaMatches ||
                                disciplineMatches ||
                                matches(subject),
                            )
                            .map((subject) => (
                              <li key={subject.id}>
                                <Link
                                  className="text-slate-900 underline"
                                  href={`/organizaciones/${slug}/curriculo/asignaturas/${subject.id}`}
                                >
                                  {subject.name}
                                </Link>{' '}
                                <StatusLabel status={subject.status} />
                                {canManage ? (
                                  <NamedEntityActions
                                    entity={subject}
                                    kind="subject"
                                    slug={slug}
                                  />
                                ) : null}
                              </li>
                            ))}
                        </ul>
                      </li>
                    );
                  })}
                </ul>
              </li>
            );
          })}
        </ul>
      )}
    </>
  );
}

function Count({ label, value }: Readonly<{ label: string; value: number }>) {
  return (
    <p className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
      <span className="block text-2xl font-semibold text-slate-950">
        {value}
      </span>
      {label}
    </p>
  );
}

function StatusLabel({ status }: Readonly<{ status: string }>) {
  return (
    <span className="text-sm font-normal text-slate-500">
      {status === 'archived' ? 'Archivado' : 'Activo'}
    </span>
  );
}
