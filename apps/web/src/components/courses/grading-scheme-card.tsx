'use client';

import { useMemo, useState } from 'react';
import {
  CheckCircle2,
  CircleAlert,
  Plus,
  Scale,
  ShieldCheck,
  Trash2,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { components } from '@/lib/api/generated/platform';
import { useReplaceGradingScheme } from '@/lib/courses/hooks';

type GradeCategory = components['schemas']['GradeCategory'];

export type GradedCourseActivity = {
  id: string;
  required: boolean;
  title: string;
};

type DraftCategory = {
  activityIds: string[];
  activityRequired: Record<string, boolean>;
  activityWeights: Record<string, number>;
  code: string;
  key: string;
  title: string;
  weight: number;
};

export function distributeBasisPoints(count: number): number[] {
  if (count < 1) return [];
  const floor = Math.floor(10_000 / count);
  const remainder = 10_000 - floor * count;
  return Array.from({ length: count }, (_, index) =>
    index < remainder ? floor + 1 : floor,
  );
}

function rebalance(category: DraftCategory): DraftCategory {
  const weights = distributeBasisPoints(category.activityIds.length);
  return {
    ...category,
    activityWeights: Object.fromEntries(
      category.activityIds.map((id, index) => [id, weights[index] ?? 0]),
    ),
  };
}

function initialCategories(
  activities: readonly GradedCourseActivity[],
  scheme: readonly GradeCategory[],
): DraftCategory[] {
  if (!scheme.length) {
    return activities.length
      ? [
          rebalance({
            activityIds: activities.map((activity) => activity.id),
            activityRequired: Object.fromEntries(
              activities.map((activity) => [activity.id, activity.required]),
            ),
            activityWeights: {},
            code: 'evaluaciones',
            key: 'evaluaciones-inicial',
            title: 'Evaluaciones',
            weight: 10_000,
          }),
        ]
      : [];
  }
  return scheme.map((category) => ({
    activityIds: category.activities.map((activity) => activity.activity_id),
    activityRequired: Object.fromEntries(
      category.activities.map((activity) => [
        activity.activity_id,
        activity.required,
      ]),
    ),
    activityWeights: Object.fromEntries(
      category.activities.map((activity) => [
        activity.activity_id,
        activity.weight_basis_points,
      ]),
    ),
    code: category.code,
    key: category.id,
    title: category.title,
    weight: category.weight_basis_points,
  }));
}

function percentage(value: number) {
  return value / 100;
}

function basisPoints(value: string) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.round(number * 100) : 0;
}

function validate(categories: readonly DraftCategory[]) {
  if (!categories.length) return 'Crea al menos una categoría.';
  if (categories.reduce((sum, category) => sum + category.weight, 0) !== 10_000)
    return 'Los pesos de las categorías deben sumar exactamente 100 %.';
  const codes = categories.map((category) => category.code.trim());
  if (
    codes.some((code) => !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(code)) ||
    new Set(codes).size !== codes.length
  )
    return 'Cada categoría necesita un código único en minúsculas y guiones.';
  for (const category of categories) {
    if (!category.title.trim()) return 'Cada categoría necesita un título.';
    if (!category.activityIds.length)
      return `La categoría «${category.title}» no contiene evaluaciones.`;
    const total = category.activityIds.reduce(
      (sum, id) => sum + (category.activityWeights[id] ?? 0),
      0,
    );
    if (total !== 10_000)
      return `Las evaluaciones de «${category.title}» deben sumar exactamente 100 %.`;
  }
  return '';
}

export function GradingSchemeCard({
  activities,
  courseSlug,
  onSaved,
  revisionId,
  revisionVersion,
  scheme,
  slug,
}: Readonly<{
  activities: readonly GradedCourseActivity[];
  courseSlug: string;
  onSaved: (lockVersion: number) => void;
  revisionId: string;
  revisionVersion: number;
  scheme: readonly GradeCategory[];
  slug: string;
}>) {
  const [categories, setCategories] = useState(() =>
    initialCategories(activities, scheme),
  );
  const [error, setError] = useState('');
  const mutation = useReplaceGradingScheme({ courseSlug, revisionId, slug });
  const assignedIds = useMemo(
    () => new Set(categories.flatMap((category) => category.activityIds)),
    [categories],
  );
  const unassigned = activities.filter(
    (activity) => !assignedIds.has(activity.id),
  );
  const configured = scheme.length > 0;

  function changeCategory(
    index: number,
    update: (category: DraftCategory) => DraftCategory,
  ) {
    setCategories((current) =>
      current.map((category, currentIndex) =>
        currentIndex === index ? update(category) : category,
      ),
    );
  }

  function toggleActivity(categoryIndex: number, activityId: string) {
    setCategories((current) => {
      const selected = current[categoryIndex]?.activityIds.includes(activityId);
      return current.map((category, index) => {
        const without = category.activityIds.filter((id) => id !== activityId);
        const activityIds =
          index === categoryIndex && !selected
            ? [...without, activityId]
            : without;
        if (activityIds.length === category.activityIds.length) return category;
        const activity = activities.find((item) => item.id === activityId);
        return rebalance({
          ...category,
          activityIds,
          activityRequired: {
            ...category.activityRequired,
            [activityId]: activity?.required ?? true,
          },
        });
      });
    });
  }

  async function save() {
    const validation = validate(categories);
    if (validation) {
      setError(validation);
      return;
    }
    setError('');
    try {
      const response = await mutation.mutateAsync({
        categories: categories.map((category) => ({
          activities: category.activityIds.map((activityId) => ({
            activity_id: activityId,
            required: category.activityRequired[activityId] ?? true,
            weight_basis_points: category.activityWeights[activityId] ?? 0,
          })),
          code: category.code.trim(),
          title: category.title.trim(),
          weight_basis_points: category.weight,
        })),
        expected_version: revisionVersion,
      });
      onSaved(response.revision_lock_version);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No fue posible guardar el esquema de calificación.',
      );
    }
  }

  return (
    <section
      aria-labelledby="grading-scheme-title"
      className="mt-5 rounded-xl border bg-card p-4 shadow-xs"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="rounded-lg bg-primary/10 p-2 text-primary">
            <Scale className="size-5" />
          </span>
          <div>
            <h3 className="font-semibold" id="grading-scheme-title">
              Cómo se calcula la nota global
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Pondera las evaluaciones que participan en la aprobación del
              curso.
            </p>
          </div>
        </div>
        <Badge
          className={configured ? 'bg-emerald-600 text-white' : ''}
          variant={configured ? 'default' : 'outline'}
        >
          {configured ? (
            <>
              <CheckCircle2 /> Configurado
            </>
          ) : (
            'Falta guardar'
          )}
        </Badge>
      </div>

      {!activities.length ? (
        <Alert className="mt-4">
          <CircleAlert />
          <AlertTitle>No hay evaluaciones calificables</AlertTitle>
          <AlertDescription>
            Añade una evaluación aprobada a la secuencia antes de exigir nota
            mínima.
          </AlertDescription>
        </Alert>
      ) : (
        <>
          {error ? (
            <Alert className="mt-4" variant="destructive">
              <AlertTitle>Revisa la ponderación</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
          <div className="mt-4 grid gap-3">
            {categories.map((category, categoryIndex) => {
              const internalTotal = category.activityIds.reduce(
                (sum, id) => sum + (category.activityWeights[id] ?? 0),
                0,
              );
              return (
                <article
                  className="rounded-xl border bg-muted/[0.04] p-3"
                  key={category.key}
                >
                  <div className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_12rem_auto]">
                    <div className="grid gap-3 sm:grid-cols-2">
                      <label className="academic-field">
                        Categoría
                        <input
                          aria-label={`Título de categoría ${categoryIndex + 1}`}
                          className="academic-control"
                          maxLength={120}
                          onChange={(event) =>
                            changeCategory(categoryIndex, (current) => ({
                              ...current,
                              title: event.target.value,
                            }))
                          }
                          value={category.title}
                        />
                      </label>
                      <label className="academic-field">
                        Código
                        <input
                          aria-label={`Código de categoría ${categoryIndex + 1}`}
                          className="academic-control"
                          maxLength={50}
                          onChange={(event) =>
                            changeCategory(categoryIndex, (current) => ({
                              ...current,
                              code: event.target.value,
                            }))
                          }
                          value={category.code}
                        />
                      </label>
                    </div>
                    <label className="academic-field">
                      Peso en la nota (%)
                      <input
                        aria-label={`Peso de categoría ${category.title}`}
                        className="academic-control"
                        max={100}
                        min={0.01}
                        onChange={(event) =>
                          changeCategory(categoryIndex, (current) => ({
                            ...current,
                            weight: basisPoints(event.target.value),
                          }))
                        }
                        step="0.01"
                        type="number"
                        value={percentage(category.weight)}
                      />
                    </label>
                    <Button
                      aria-label={`Eliminar categoría ${category.title}`}
                      disabled={categories.length === 1}
                      onClick={() =>
                        setCategories((current) =>
                          current.filter((_, index) => index !== categoryIndex),
                        )
                      }
                      size="icon-sm"
                      type="button"
                      variant="ghost"
                    >
                      <Trash2 />
                    </Button>
                  </div>
                  <div className="mt-3 grid gap-2">
                    {activities.map((activity) => {
                      const selected = category.activityIds.includes(
                        activity.id,
                      );
                      return (
                        <div
                          className="grid items-center gap-2 rounded-lg border bg-background p-2.5 sm:grid-cols-[minmax(0,1fr)_9rem_8rem]"
                          key={activity.id}
                        >
                          <label className="flex min-w-0 items-center gap-2 text-sm font-medium">
                            <input
                              checked={selected}
                              onChange={() =>
                                toggleActivity(categoryIndex, activity.id)
                              }
                              type="checkbox"
                            />
                            <span className="truncate">{activity.title}</span>
                          </label>
                          <label className="academic-field text-xs">
                            Peso interno (%)
                            <input
                              aria-label={`Peso de ${activity.title} en ${category.title}`}
                              className="academic-control"
                              disabled={!selected}
                              max={100}
                              min={0.01}
                              onChange={(event) =>
                                changeCategory(categoryIndex, (current) => ({
                                  ...current,
                                  activityWeights: {
                                    ...current.activityWeights,
                                    [activity.id]: basisPoints(
                                      event.target.value,
                                    ),
                                  },
                                }))
                              }
                              step="0.01"
                              type="number"
                              value={percentage(
                                category.activityWeights[activity.id] ?? 0,
                              )}
                            />
                          </label>
                          <label className="flex items-center gap-2 text-xs">
                            <input
                              checked={
                                category.activityRequired[activity.id] ?? true
                              }
                              disabled={!selected}
                              onChange={(event) =>
                                changeCategory(categoryIndex, (current) => ({
                                  ...current,
                                  activityRequired: {
                                    ...current.activityRequired,
                                    [activity.id]: event.target.checked,
                                  },
                                }))
                              }
                              type="checkbox"
                            />
                            Obligatoria
                          </label>
                        </div>
                      );
                    })}
                  </div>
                  <p className="mt-2 text-right text-xs text-muted-foreground">
                    Peso interno: {percentage(internalTotal).toFixed(2)} %
                  </p>
                </article>
              );
            })}
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <Button
              onClick={() =>
                setCategories((current) => [
                  ...current,
                  {
                    activityIds: [],
                    activityRequired: {},
                    activityWeights: {},
                    code: `categoria-${current.length + 1}`,
                    key: `nueva-${current.length}-${Date.now()}`,
                    title: `Categoría ${current.length + 1}`,
                    weight: 0,
                  },
                ])
              }
              size="sm"
              type="button"
              variant="outline"
            >
              <Plus /> Añadir categoría
            </Button>
            <div className="text-right text-xs text-muted-foreground">
              <p>
                Categorías:{' '}
                {percentage(
                  categories.reduce((sum, item) => sum + item.weight, 0),
                ).toFixed(2)}{' '}
                %
              </p>
              {unassigned.length ? (
                <p className="text-amber-700">
                  {unassigned.length} evaluación(es) fuera de la nota global.
                </p>
              ) : null}
            </div>
          </div>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t pt-4">
            <p className="flex items-center gap-2 text-xs text-muted-foreground">
              <ShieldCheck className="size-4" />
              PostgreSQL conserva la ponderación publicada; las notas sueltas no
              aprueban por sí solas el curso.
            </p>
            <Button disabled={mutation.isPending} onClick={save} type="button">
              {mutation.isPending
                ? 'Guardando…'
                : 'Guardar esquema de calificación'}
            </Button>
          </div>
        </>
      )}
    </section>
  );
}
