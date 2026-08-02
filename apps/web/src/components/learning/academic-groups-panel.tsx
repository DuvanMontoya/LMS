'use client';

import { LoaderCircle, Plus, UsersRound } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  MembershipSearchPicker,
  type MembershipOption,
} from '@/components/learning/membership-search-picker';
import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import type { AcademicGroupPage } from '@/lib/learning/server';

type Level = components['schemas']['AcademicGroupLevel'];
type GroupRole = components['schemas']['AcademicGroupRole'];
const levels: Array<[Level, string]> = [
  ['early_childhood', 'Primera infancia'],
  ['preschool', 'Preescolar'],
  ['transition', 'Transición'],
  ['primary_1', 'Primero'],
  ['primary_2', 'Segundo'],
  ['primary_3', 'Tercero'],
  ['primary_4', 'Cuarto'],
  ['primary_5', 'Quinto'],
  ['secondary_6', 'Sexto'],
  ['secondary_7', 'Séptimo'],
  ['secondary_8', 'Octavo'],
  ['secondary_9', 'Noveno'],
  ['secondary_10', 'Décimo'],
  ['secondary_11', 'Undécimo'],
  ['technical', 'Técnico o tecnológico'],
  ['higher_education', 'Educación superior'],
  ['continuing_education', 'Educación continua'],
  ['other', 'Otro'],
];

export function AcademicGroupsPanel({
  canManage,
  groups,
  slug,
}: Readonly<{
  canManage: boolean;
  groups: AcademicGroupPage['results'];
  slug: string;
}>) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const [name, setName] = useState('');
  const [section, setSection] = useState('');
  const [level, setLevel] = useState<Level>('secondary_11');
  const [academicYear, setAcademicYear] = useState(new Date().getFullYear());
  const [savingGroup, setSavingGroup] = useState('');
  const [rosters, setRosters] = useState<
    Record<string, Record<string, '' | GroupRole>>
  >(() =>
    Object.fromEntries(
      groups.map((group) => [
        group.id,
        Object.fromEntries(
          group.roster
            .filter((entry) => entry.status === 'active')
            .map((entry) => [entry.membership_id, entry.role]),
        ),
      ]),
    ),
  );
  const [rosterPeople, setRosterPeople] = useState<
    Record<string, Record<string, MembershipOption>>
  >(() =>
    Object.fromEntries(
      groups.map((group) => [
        group.id,
        Object.fromEntries(
          group.roster
            .filter((entry) => entry.status === 'active')
            .map((entry) => [
              entry.membership_id,
              { email: entry.email, id: entry.membership_id },
            ]),
        ),
      ]),
    ),
  );

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setError('');
    const { error: responseError, response } = await platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/academic-groups/',
      {
        params: { path: { slug } },
        body: {
          academic_year: academicYear,
          description: '',
          level,
          name: name.trim(),
          section: section.trim(),
        },
      },
    );
    setPending(false);
    if (!response.ok) {
      const detail = responseError as { detail?: string } | undefined;
      setError(detail?.detail ?? 'No fue posible crear el grupo.');
      return;
    }
    setName('');
    setSection('');
    router.refresh();
  }

  async function saveRoster(groupId: string) {
    setSavingGroup(groupId);
    setError('');
    const groupRoster = rosters[groupId] ?? {};
    const group = groups.find((item) => item.id === groupId);
    if (!group) return;
    const { error: responseError, response } = await platformBrowserClient.PUT(
      '/api/v1/organizations/{slug}/learning/academic-groups/{group_id}/roster/',
      {
        params: { path: { group_id: groupId, slug } },
        body: {
          expected_group_version: group.lock_version,
          members: Object.entries(groupRoster)
            .filter((entry): entry is [string, GroupRole] => Boolean(entry[1]))
            .map(([membershipId, role]) => ({
              membership_id: membershipId,
              role,
            })),
        },
      },
    );
    if (!response.ok) {
      const detail = responseError as { detail?: string } | undefined;
      setError(detail?.detail ?? 'No fue posible actualizar el grupo.');
      setSavingGroup('');
      return;
    }
    setSavingGroup('');
    router.refresh();
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[22rem_minmax(0,1fr)]">
      {canManage ? (
        <form
          className="academic-panel h-fit space-y-4 p-5"
          onSubmit={(event) => void create(event)}
        >
          <div>
            <p className="academic-kicker">Nueva agrupación</p>
            <h2 className="text-lg font-semibold">Crear grupo académico</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Un mismo grupo puede organizar docentes y estudiantes y vincularse
              a grupos de curso de varios cursos.
            </p>
          </div>
          <label className="grid gap-1.5 text-sm font-medium">
            Nombre
            <Input
              onChange={(event) => setName(event.target.value)}
              required
              value={name}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="grid gap-1.5 text-sm font-medium">
              Año
              <Input
                max={2200}
                min={2000}
                onChange={(event) =>
                  setAcademicYear(Number(event.target.value))
                }
                type="number"
                value={academicYear}
              />
            </label>
            <label className="grid gap-1.5 text-sm font-medium">
              Grupo/curso
              <Input
                onChange={(event) => setSection(event.target.value)}
                placeholder="A, B, 01…"
                value={section}
              />
            </label>
          </div>
          <label className="grid gap-1.5 text-sm font-medium">
            Nivel
            <select
              className="academic-control"
              onChange={(event) => setLevel(event.target.value as Level)}
              value={level}
            >
              {levels.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          {error ? (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
          <Button disabled={pending || !name.trim()} type="submit">
            {pending ? <LoaderCircle className="animate-spin" /> : <Plus />}
            Crear grupo
          </Button>
        </form>
      ) : null}
      <section className="grid gap-3" aria-label="Grupos académicos">
        {groups.map((group) => (
          <article className="academic-panel p-5" key={group.id}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">{group.name}</h2>
                <p className="text-sm text-muted-foreground">
                  {levels.find(([value]) => value === group.level)?.[1] ??
                    group.level}
                  {group.section ? ` · Grupo ${group.section}` : ''} ·{' '}
                  {group.academic_year}
                </p>
              </div>
              <Badge variant="secondary">
                {
                  group.roster.filter((member) => member.status === 'active')
                    .length
                }{' '}
                integrantes
              </Badge>
            </div>
            <div className="mt-4 flex flex-wrap gap-2 text-xs text-muted-foreground">
              <span>
                {
                  group.roster.filter(
                    (member) =>
                      member.role === 'learner' && member.status === 'active',
                  ).length
                }{' '}
                estudiantes
              </span>
              <span>·</span>
              <span>
                {
                  group.roster.filter(
                    (member) =>
                      member.role === 'instructor' &&
                      member.status === 'active',
                  ).length
                }{' '}
                docentes
              </span>
              <span>·</span>
              <span>
                {group.linked_cohort_count ?? 0} grupos de curso vinculados
              </span>
            </div>
            {canManage ? (
              <details className="mt-4 border-t pt-4">
                <summary className="cursor-pointer text-sm font-medium">
                  Administrar integrantes
                </summary>
                <div className="mt-3 grid gap-2">
                  <MembershipSearchPicker
                    ariaLabel={`Buscar integrante para ${group.name}`}
                    excludeIds={Object.keys(rosters[group.id] ?? {})}
                    onSelect={(member) => {
                      setRosters((current) => ({
                        ...current,
                        [group.id]: {
                          ...(current[group.id] ?? {}),
                          [member.id]: 'learner',
                        },
                      }));
                      setRosterPeople((current) => ({
                        ...current,
                        [group.id]: {
                          ...(current[group.id] ?? {}),
                          [member.id]: member,
                        },
                      }));
                    }}
                    slug={slug}
                  />
                  {Object.entries(rosters[group.id] ?? {}).length ? (
                    <div className="mt-3 grid gap-2 rounded-md border p-2 sm:grid-cols-2">
                      {Object.entries(rosters[group.id] ?? {}).map(
                        ([membershipId, role]) => {
                          const member = rosterPeople[group.id]?.[membershipId];
                          return (
                            <div
                              className="grid gap-2 rounded-md p-2 sm:grid-cols-[minmax(0,1fr)_10rem_auto] sm:items-center"
                              key={membershipId}
                            >
                              <span className="truncate text-sm">
                                {member?.email ?? membershipId}
                              </span>
                              <select
                                aria-label={`Participación de ${member?.email ?? membershipId}`}
                                className="academic-control"
                                onChange={(event) =>
                                  setRosters((current) => ({
                                    ...current,
                                    [group.id]: {
                                      ...(current[group.id] ?? {}),
                                      [membershipId]: event.target
                                        .value as GroupRole,
                                    },
                                  }))
                                }
                                value={role}
                              >
                                <option value="learner">Estudiante</option>
                                <option value="instructor">Docente</option>
                                <option value="assistant">Acompañante</option>
                              </select>
                              <Button
                                onClick={() => {
                                  setRosters((current) => {
                                    const nextGroup = {
                                      ...(current[group.id] ?? {}),
                                    };
                                    delete nextGroup[membershipId];
                                    return {
                                      ...current,
                                      [group.id]: nextGroup,
                                    };
                                  });
                                  setRosterPeople((current) => {
                                    const nextGroup = {
                                      ...(current[group.id] ?? {}),
                                    };
                                    delete nextGroup[membershipId];
                                    return {
                                      ...current,
                                      [group.id]: nextGroup,
                                    };
                                  });
                                }}
                                size="sm"
                                type="button"
                                variant="ghost"
                              >
                                Quitar
                              </Button>
                            </div>
                          );
                        },
                      )}
                    </div>
                  ) : null}
                  <Button
                    className="mt-2 justify-self-start"
                    disabled={savingGroup === group.id}
                    onClick={() => void saveRoster(group.id)}
                    size="sm"
                    type="button"
                    variant="outline"
                  >
                    {savingGroup === group.id ? (
                      <LoaderCircle className="animate-spin" />
                    ) : (
                      <UsersRound />
                    )}
                    Guardar integrantes
                  </Button>
                </div>
              </details>
            ) : null}
          </article>
        ))}
        {!groups.length ? (
          <div className="academic-panel border-dashed p-10 text-center">
            <UsersRound className="mx-auto mb-3 size-7 text-muted-foreground" />
            <h2 className="font-semibold">Aún no hay grupos académicos</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Crea el primer grupo para organizar una promoción, grado o grupo
              independiente.
            </p>
          </div>
        ) : null}
      </section>
    </div>
  );
}
