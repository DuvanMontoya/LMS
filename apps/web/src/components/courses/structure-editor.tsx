'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useRef, useState } from 'react';
import {
  Archive,
  ArchiveRestore,
  BookOpenText,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  ClipboardCheck,
  Clock3,
  Network,
  Plus,
  Video,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { components } from '@/lib/api/generated/platform';
import {
  RevisionConflictError,
  useBindActivity,
  useCreateActivity,
  useCreateModule,
  useCreateUnit,
  useReorderStructure,
  useReplaceUnitAlignment,
  useSetStructureArchived,
  useUpdateStructure,
} from '@/lib/courses/hooks';

type Outline = components['schemas']['Outline'];
type Objective = components['schemas']['Objective'];
type Topic = components['schemas']['Topic'];
const contentStatusLabels: Record<string, string> = {
  empty: 'Contenido vacío',
  missing: 'Sin contenido',
  ready: 'Contenido listo',
};

function statusLabel(value: string) {
  return (
    {
      active: 'Activo',
      approved: 'aprobada',
      archived: 'Archivado',
      changes_requested: 'con cambios solicitados',
      draft: 'en borrador',
      in_review: 'en revisión',
    }[value] ?? value
  );
}

export function StructureEditor({
  assessmentVersions,
  canManage,
  courseSlug,
  objectives,
  outline,
  slug,
  topics,
}: Readonly<{
  assessmentVersions: Array<{ id: string; label: string }>;
  canManage: boolean;
  courseSlug: string;
  objectives: Objective[];
  outline: Outline;
  slug: string;
  topics: Topic[];
}>) {
  const router = useRouter();
  const editable = ['draft', 'changes_requested'].includes(
    outline.revision.authoring_status,
  );
  const [modules, setModules] = useState([...outline.modules]);
  const [version, setVersion] = useState(outline.revision.lock_version);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const moduleTitle = useRef<HTMLInputElement>(null);
  const path = { courseSlug, revisionId: outline.revision.id, slug };
  const createModule = useCreateModule(path);
  const createActivity = useCreateActivity(path);
  const bindActivity = useBindActivity(path);
  const createUnit = useCreateUnit(path);
  const updateStructure = useUpdateStructure(path);
  const reorder = useReorderStructure(path);
  const archive = useSetStructureArchived(path);
  const unitAlignment = useReplaceUnitAlignment(path);

  function failed(cause: unknown) {
    setError(
      cause instanceof Error ? cause.message : 'No fue posible guardar.',
    );
    if (cause instanceof RevisionConflictError) {
      setMessage(
        'Actualiza la página cuando estés listo para reconciliar cambios.',
      );
    }
  }

  async function addModule(formData: FormData) {
    setError('');
    try {
      await createModule.mutateAsync({
        expected_version: version,
        title: String(formData.get('module-title') ?? ''),
      });
      setVersion((current) => current + 1);
      setMessage('Módulo creado.');
      moduleTitle.current?.form?.reset();
      router.refresh();
    } catch (cause) {
      failed(cause);
      moduleTitle.current?.focus();
    }
  }

  async function addUnit(moduleId: string, formData: FormData) {
    setError('');
    try {
      await createUnit.mutateAsync({
        body: {
          expected_version: version,
          title: String(formData.get('unit-title') ?? ''),
        },
        moduleId,
      });
      setVersion((current) => current + 1);
      setMessage('Unidad creada.');
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  async function addActivity(moduleId: string, formData: FormData) {
    setError('');
    const activityType = String(formData.get('activity-type')) as
      'assessment' | 'live_class';
    const threshold = formData.get('activity-threshold')
      ? Number(formData.get('activity-threshold')) * 100
      : null;
    const duration = formData.get('activity-duration')
      ? Number(formData.get('activity-duration'))
      : null;
    const assessmentVersionId = String(
      formData.get('assessment-version') ?? '',
    );
    if (activityType === 'assessment' && !assessmentVersionId) {
      setError('Selecciona una versión aprobada de evaluación.');
      return;
    }
    try {
      const created = await createActivity.mutateAsync({
        body: {
          activity_type: activityType,
          completion_method:
            activityType === 'live_class' ? 'attendance' : 'pass',
          estimated_duration_minutes: duration,
          expected_version: version,
          minimum_attendance_basis_points:
            activityType === 'live_class' ? threshold : null,
          minimum_grade_basis_points:
            activityType === 'assessment' ? threshold : null,
          required: formData.get('activity-required') === 'on',
          summary: String(formData.get('activity-summary') ?? ''),
          title: String(formData.get('activity-title') ?? ''),
        },
        moduleId,
      });
      const binding = await bindActivity.mutateAsync(
        activityType === 'assessment'
          ? {
              activityId: created.id,
              body: {
                assessment_version_id: assessmentVersionId,
                expected_revision_version: created.lock_version,
              },
              kind: 'assessment',
            }
          : {
              activityId: created.id,
              body: {
                expected_revision_version: created.lock_version,
                minimum_attendance_minutes:
                  duration && threshold
                    ? Math.max(1, Math.ceil((duration * threshold) / 10000))
                    : duration,
                minimum_attended_occurrences: 1,
              },
              kind: 'live_class',
            },
      );
      setVersion(binding.revision_lock_version);
      setMessage('Actividad curricular y binding operativo creados.');
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  async function editModule(moduleId: string, formData: FormData) {
    setError('');
    try {
      await updateStructure.mutateAsync({
        body: {
          description: String(formData.get('module-description') ?? ''),
          expected_version: version,
          title: String(formData.get('module-title') ?? ''),
        },
        id: moduleId,
        kind: 'module',
      });
      setVersion((current) => current + 1);
      setMessage('Módulo actualizado.');
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  async function editUnit(unitId: string, formData: FormData) {
    setError('');
    try {
      await updateStructure.mutateAsync({
        body: {
          estimated_duration_minutes: formData.get('unit-duration')
            ? Number(formData.get('unit-duration'))
            : null,
          expected_version: version,
          summary: String(formData.get('unit-summary') ?? ''),
          title: String(formData.get('unit-title') ?? ''),
        },
        id: unitId,
        kind: 'unit',
      });
      setVersion((current) => current + 1);
      setMessage('Unidad actualizada.');
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  async function moveModule(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= modules.length) return;
    const next = [...modules];
    const moving = next[index];
    const displaced = next[target];
    if (!moving || !displaced) return;
    next[index] = displaced;
    next[target] = moving;
    try {
      const result = await reorder.mutateAsync({
        body: {
          expected_version: version,
          ordered_ids: next
            .filter((item) => item.status === 'active')
            .map((item) => item.id),
        },
      });
      setModules(next);
      setVersion(result.lock_version);
      setMessage(`«${moving.title}» ahora está en la posición ${target + 1}.`);
    } catch (cause) {
      failed(cause);
    }
  }

  async function moveUnit(
    moduleIndex: number,
    unitIndex: number,
    delta: number,
  ) {
    const courseModule = modules[moduleIndex];
    if (!courseModule) return;
    const units = [...courseModule.units];
    const target = unitIndex + delta;
    if (target < 0 || target >= units.length) return;
    const moving = units[unitIndex];
    const displaced = units[target];
    if (!moving || !displaced) return;
    units[unitIndex] = displaced;
    units[target] = moving;
    try {
      const result = await reorder.mutateAsync({
        body: {
          expected_version: version,
          ordered_ids: units
            .filter((item) => item.status === 'active')
            .map((item) => item.id),
        },
        moduleId: courseModule.id,
      });
      const nextModules = [...modules];
      nextModules[moduleIndex] = { ...courseModule, units };
      setModules(nextModules);
      setVersion(result.lock_version);
      setMessage(`«${moving.title}» ahora está en la posición ${target + 1}.`);
    } catch (cause) {
      failed(cause);
    }
  }

  async function setArchived(
    id: string,
    kind: 'module' | 'unit',
    restore: boolean,
  ) {
    try {
      await archive.mutateAsync({
        expectedVersion: version,
        id,
        kind,
        restore,
      });
      setVersion((current) => current + 1);
      setMessage(
        restore ? 'Elemento restaurado al final.' : 'Elemento archivado.',
      );
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  async function saveUnitAlignment(
    unitId: string,
    kind: 'objectives' | 'topics',
    formData: FormData,
  ) {
    try {
      const ids = formData.getAll(kind).map(String);
      const result = await unitAlignment.mutateAsync(
        kind === 'topics'
          ? {
              body: { expected_version: version, topic_ids: ids },
              kind,
              unitId,
            }
          : {
              body: {
                expected_version: version,
                learning_objective_ids: ids,
              },
              kind,
              unitId,
            },
      );
      setVersion(result.lock_version);
      setMessage(
        kind === 'topics'
          ? 'Temas de la unidad actualizados.'
          : 'Objetivos de la unidad actualizados.',
      );
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  return (
    <section aria-labelledby="course-structure">
      <div aria-live="polite" className="mb-4 space-y-2">
        {message ? (
          <Alert className="border-emerald-600/20 bg-emerald-500/5">
            <CheckCircle2 className="text-emerald-700" />
            <AlertTitle>Estructura actualizada</AlertTitle>
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        ) : null}
        {error ? (
          <Alert variant="destructive">
            <CircleAlert />
            <AlertTitle>No se pudo guardar</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
      </div>
      <h2 className="sr-only" id="course-structure">
        Estructura del curso
      </h2>
      {!editable ? (
        <Alert className="border-amber-600/20 bg-amber-500/5">
          <CircleAlert className="text-amber-700" />
          <AlertTitle>Solo lectura</AlertTitle>
          <AlertDescription>
            La revisión está {statusLabel(outline.revision.authoring_status)}.
          </AlertDescription>
        </Alert>
      ) : null}
      {canManage && editable ? (
        <form
          action={addModule}
          className="mt-5 flex flex-wrap gap-3 rounded-lg border bg-muted/20 p-3"
        >
          <label className="academic-field min-w-64 flex-1">
            Título del nuevo módulo
            <input
              className="academic-control"
              maxLength={200}
              name="module-title"
              ref={moduleTitle}
              required
            />
          </label>
          <Button className="self-end" type="submit">
            <Plus />
            Añadir módulo
          </Button>
        </form>
      ) : null}
      {modules.length ? (
        <ol className="mt-5 space-y-4">
          {modules.map((module, moduleIndex) => (
            <li
              className="overflow-hidden rounded-lg border bg-card shadow-xs"
              key={module.id}
            >
              <div className="flex flex-wrap items-start justify-between gap-3 border-b bg-muted/20 px-5 py-4">
                <div>
                  <p className="text-[0.6875rem] font-semibold tracking-wider text-muted-foreground uppercase">
                    Módulo {module.position ?? 'archivado'}
                  </p>
                  <h3 className="mt-1 text-base font-semibold">
                    {module.title}
                  </h3>
                  <p className="mt-1 text-xs text-muted-foreground">
                    {statusLabel(module.status)} · {module.units.length}{' '}
                    {module.units.length === 1 ? 'unidad' : 'unidades'}
                  </p>
                </div>
                {canManage && editable ? (
                  <div className="flex flex-wrap gap-2">
                    <Button
                      aria-label={`Mover «${module.title}» una posición arriba`}
                      disabled={moduleIndex === 0 || module.status !== 'active'}
                      onClick={() => moveModule(moduleIndex, -1)}
                      size="icon-sm"
                      title="Mover arriba"
                      type="button"
                      variant="outline"
                    >
                      <ChevronUp />
                    </Button>
                    <Button
                      aria-label={`Mover «${module.title}» una posición abajo`}
                      disabled={
                        moduleIndex === modules.length - 1 ||
                        module.status !== 'active'
                      }
                      onClick={() => moveModule(moduleIndex, 1)}
                      size="icon-sm"
                      title="Mover abajo"
                      type="button"
                      variant="outline"
                    >
                      <ChevronDown />
                    </Button>
                    <Button
                      aria-label={`${module.status === 'archived' ? 'Restaurar' : 'Archivar'} módulo «${module.title}»`}
                      onClick={() =>
                        setArchived(
                          module.id,
                          'module',
                          module.status === 'archived',
                        )
                      }
                      size="icon-sm"
                      title={
                        module.status === 'archived' ? 'Restaurar' : 'Archivar'
                      }
                      type="button"
                      variant="outline"
                    >
                      {module.status === 'archived' ? (
                        <ArchiveRestore />
                      ) : (
                        <Archive />
                      )}
                    </Button>
                  </div>
                ) : null}
              </div>
              {canManage && editable && module.status === 'active' ? (
                <details className="border-b bg-muted/10 px-5 py-3">
                  <summary
                    aria-label={`Editar módulo «${module.title}»`}
                    className="cursor-pointer text-sm font-medium"
                  >
                    Editar información
                  </summary>
                  <form
                    action={(formData) => editModule(module.id, formData)}
                    className="mt-3 grid gap-3"
                  >
                    <label className="academic-field">
                      Título
                      <input
                        className="academic-control"
                        defaultValue={module.title}
                        maxLength={200}
                        name="module-title"
                        required
                      />
                    </label>
                    <label className="academic-field">
                      Descripción
                      <textarea
                        className="academic-control min-h-20"
                        defaultValue={module.description}
                        maxLength={3000}
                        name="module-description"
                      />
                    </label>
                    <Button
                      className="w-fit"
                      size="sm"
                      type="submit"
                      variant="outline"
                    >
                      Guardar cambios
                    </Button>
                  </form>
                </details>
              ) : null}
              <section className="border-b bg-muted/5 px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <h4 className="font-semibold">
                      Secuencia curricular unificada
                    </h4>
                    <p className="text-sm text-muted-foreground">
                      Lecciones, clases en vivo y evaluaciones comparten el
                      mismo orden.
                    </p>
                  </div>
                  <Badge variant="outline">
                    {module.activities.length} actividades
                  </Badge>
                </div>
                {module.activities.length ? (
                  <ol className="mt-3 grid gap-2">
                    {module.activities.map((activity) => (
                      <li
                        className="flex items-start gap-3 rounded-md border bg-background p-3"
                        key={activity.id}
                      >
                        <span className="mt-0.5 text-primary">
                          {activity.activity_type === 'live_class' ? (
                            <Video className="size-4" />
                          ) : activity.activity_type === 'assessment' ? (
                            <ClipboardCheck className="size-4" />
                          ) : (
                            <BookOpenText className="size-4" />
                          )}
                        </span>
                        <div className="min-w-0 flex-1">
                          <strong className="block truncate">
                            {activity.position}. {activity.title}
                          </strong>
                          <small className="text-muted-foreground">
                            {activityTypeLabel(activity.activity_type)} ·{' '}
                            {activity.required ? 'Obligatoria' : 'Opcional'} ·{' '}
                            {activityCompletionLabel(
                              activity.completion_method,
                            )}
                          </small>
                        </div>
                      </li>
                    ))}
                  </ol>
                ) : null}
                {canManage && editable && module.status === 'active' ? (
                  <details className="mt-3 rounded-md border bg-background px-3 py-2">
                    <summary className="cursor-pointer text-sm font-medium">
                      Añadir clase en vivo o evaluación
                    </summary>
                    <form
                      action={(formData) => addActivity(module.id, formData)}
                      className="mt-3 grid gap-3 md:grid-cols-2"
                    >
                      <label className="academic-field">
                        Tipo
                        <select
                          className="academic-control"
                          name="activity-type"
                        >
                          <option value="live_class">Clase en vivo</option>
                          <option value="assessment">Evaluación</option>
                        </select>
                      </label>
                      <label className="academic-field md:col-span-2">
                        Versión aprobada de evaluación
                        <select
                          className="academic-control"
                          name="assessment-version"
                        >
                          <option value="">
                            Selecciona si el tipo es evaluación
                          </option>
                          {assessmentVersions.map((option) => (
                            <option key={option.id} value={option.id}>
                              {option.label}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="academic-field">
                        Título
                        <input
                          className="academic-control"
                          maxLength={200}
                          name="activity-title"
                          required
                        />
                      </label>
                      <label className="academic-field md:col-span-2">
                        Resumen
                        <textarea
                          className="academic-control min-h-20"
                          maxLength={1200}
                          name="activity-summary"
                        />
                      </label>
                      <label className="academic-field">
                        Duración estimada (minutos)
                        <input
                          className="academic-control"
                          min={1}
                          name="activity-duration"
                          type="number"
                        />
                      </label>
                      <label className="academic-field">
                        Umbral de asistencia/nota (%)
                        <input
                          className="academic-control"
                          max={100}
                          min={0}
                          name="activity-threshold"
                          type="number"
                        />
                      </label>
                      <label className="flex items-center gap-2 text-sm font-medium">
                        <input
                          defaultChecked
                          name="activity-required"
                          type="checkbox"
                        />
                        Actividad obligatoria
                      </label>
                      <Button className="w-fit" type="submit">
                        <Plus /> Añadir actividad
                      </Button>
                    </form>
                  </details>
                ) : null}
              </section>
              {module.units.length ? (
                <ol className="divide-y">
                  {module.units.map((unit, unitIndex) => (
                    <li
                      className="px-5 py-4 transition-colors hover:bg-muted/15"
                      key={unit.id}
                    >
                      <div className="flex flex-wrap justify-between gap-3">
                        <div className="min-w-0 flex-1">
                          <div className="flex flex-wrap items-center gap-2">
                            <h4 className="font-semibold">
                              {unit.position ?? 'Archivada'}. {unit.title}
                            </h4>
                            <Badge
                              className="rounded"
                              variant={
                                unit.content_status === 'ready'
                                  ? 'secondary'
                                  : 'outline'
                              }
                            >
                              {contentStatusLabels[unit.content_status] ??
                                unit.content_status}
                            </Badge>
                          </div>
                          <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                            <span className="inline-flex items-center gap-1">
                              <BookOpenText className="size-3.5" />
                              {unit.content_version
                                ? `Versión ${unit.content_version}`
                                : 'Sin versión'}
                            </span>
                            <span className="inline-flex items-center gap-1">
                              <Network className="size-3.5" />
                              {unit.topics.length}{' '}
                              {unit.topics.length === 1 ? 'tema' : 'temas'} ·{' '}
                              {unit.learning_objectives.length}{' '}
                              {unit.learning_objectives.length === 1
                                ? 'objetivo'
                                : 'objetivos'}
                            </span>
                            {unit.estimated_duration_minutes ? (
                              <span className="inline-flex items-center gap-1">
                                <Clock3 className="size-3.5" />
                                {unit.estimated_duration_minutes} min
                              </span>
                            ) : null}
                          </div>
                          {unit.status === 'active' ? (
                            <Button
                              asChild
                              className="mt-3"
                              size="sm"
                              variant="outline"
                            >
                              <Link
                                href={`/organizaciones/${slug}/cursos/${courseSlug}/unidades/${unit.id}/contenido`}
                              >
                                <BookOpenText />
                                {canManage && editable
                                  ? 'Editar contenido'
                                  : 'Ver contenido'}
                              </Link>
                            </Button>
                          ) : null}
                          {canManage && editable && unit.status === 'active' ? (
                            <details className="mt-3 rounded-lg border bg-muted/10 px-3 py-2">
                              <summary
                                aria-label={`Editar unidad «${unit.title}»`}
                                className="cursor-pointer text-sm font-medium"
                              >
                                Editar información
                              </summary>
                              <form
                                action={(formData) =>
                                  editUnit(unit.id, formData)
                                }
                                className="mt-3 grid gap-3"
                              >
                                <label className="academic-field">
                                  Título
                                  <input
                                    aria-label={`Nuevo título de unidad «${unit.title}»`}
                                    className="academic-control"
                                    defaultValue={unit.title}
                                    maxLength={200}
                                    name="unit-title"
                                    required
                                  />
                                </label>
                                <label className="academic-field">
                                  Resumen
                                  <textarea
                                    className="academic-control min-h-20"
                                    defaultValue={unit.summary}
                                    maxLength={1200}
                                    name="unit-summary"
                                  />
                                </label>
                                <label className="academic-field">
                                  Duración (minutos)
                                  <input
                                    className="academic-control"
                                    defaultValue={
                                      unit.estimated_duration_minutes ?? ''
                                    }
                                    min={1}
                                    name="unit-duration"
                                    type="number"
                                  />
                                </label>
                                <Button
                                  aria-label={`Guardar unidad «${unit.title}»`}
                                  className="w-fit"
                                  size="sm"
                                  type="submit"
                                  variant="outline"
                                >
                                  Guardar cambios
                                </Button>
                              </form>
                            </details>
                          ) : null}
                          {canManage && editable && unit.status === 'active' ? (
                            <details className="mt-2 rounded-lg border bg-muted/10 px-3 py-2">
                              <summary className="cursor-pointer text-sm font-medium">
                                Alineación curricular
                              </summary>
                              <div className="mt-3 grid gap-4 xl:grid-cols-2">
                                <form
                                  action={(formData) =>
                                    saveUnitAlignment(
                                      unit.id,
                                      'topics',
                                      formData,
                                    )
                                  }
                                  className="rounded-lg border bg-card p-3"
                                >
                                  <fieldset>
                                    <legend className="text-sm font-semibold">
                                      Temas
                                    </legend>
                                    <div className="mt-2 max-h-56 space-y-1 overflow-y-auto">
                                      {topics.length ? (
                                        topics.map((topic) => (
                                          <label
                                            className="flex gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
                                            key={topic.id}
                                          >
                                            <input
                                              className="mt-0.5 size-4 accent-primary"
                                              defaultChecked={unit.topics.some(
                                                (item) =>
                                                  item.topic.id === topic.id,
                                              )}
                                              name="topics"
                                              type="checkbox"
                                              value={topic.id}
                                            />
                                            {topic.title}
                                          </label>
                                        ))
                                      ) : (
                                        <p className="text-sm text-muted-foreground">
                                          No hay temas disponibles.
                                        </p>
                                      )}
                                    </div>
                                  </fieldset>
                                  <Button
                                    className="mt-3"
                                    size="sm"
                                    type="submit"
                                    variant="outline"
                                  >
                                    {topics.length
                                      ? 'Guardar temas'
                                      : 'Limpiar temas'}
                                  </Button>
                                </form>
                                <form
                                  action={(formData) =>
                                    saveUnitAlignment(
                                      unit.id,
                                      'objectives',
                                      formData,
                                    )
                                  }
                                  className="rounded-lg border bg-card p-3"
                                >
                                  <fieldset>
                                    <legend className="text-sm font-semibold">
                                      Objetivos
                                    </legend>
                                    <div className="mt-2 max-h-56 space-y-1 overflow-y-auto">
                                      {objectives.length ? (
                                        objectives.map((objective) => (
                                          <label
                                            className="flex gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-muted"
                                            key={objective.id}
                                          >
                                            <input
                                              className="mt-0.5 size-4 accent-primary"
                                              defaultChecked={unit.learning_objectives.some(
                                                (item) =>
                                                  item.learning_objective.id ===
                                                  objective.id,
                                              )}
                                              name="objectives"
                                              type="checkbox"
                                              value={objective.id}
                                            />
                                            <span>
                                              <strong>{objective.code}</strong>{' '}
                                              — {objective.statement}
                                            </span>
                                          </label>
                                        ))
                                      ) : (
                                        <p className="text-sm text-muted-foreground">
                                          No hay objetivos disponibles.
                                        </p>
                                      )}
                                    </div>
                                  </fieldset>
                                  <Button
                                    className="mt-3"
                                    size="sm"
                                    type="submit"
                                    variant="outline"
                                  >
                                    {objectives.length
                                      ? 'Guardar objetivos'
                                      : 'Limpiar objetivos'}
                                  </Button>
                                </form>
                              </div>
                            </details>
                          ) : null}
                        </div>
                        {canManage && editable ? (
                          <div className="flex flex-wrap gap-2">
                            <Button
                              aria-label={`Mover «${unit.title}» una posición arriba`}
                              disabled={
                                unitIndex === 0 || unit.status !== 'active'
                              }
                              onClick={() =>
                                moveUnit(moduleIndex, unitIndex, -1)
                              }
                              size="icon-sm"
                              title="Mover arriba"
                              type="button"
                              variant="outline"
                            >
                              <ChevronUp />
                            </Button>
                            <Button
                              aria-label={`Mover «${unit.title}» una posición abajo`}
                              disabled={
                                unitIndex === module.units.length - 1 ||
                                unit.status !== 'active'
                              }
                              onClick={() =>
                                moveUnit(moduleIndex, unitIndex, 1)
                              }
                              size="icon-sm"
                              title="Mover abajo"
                              type="button"
                              variant="outline"
                            >
                              <ChevronDown />
                            </Button>
                            <Button
                              aria-label={`${unit.status === 'archived' ? 'Restaurar' : 'Archivar'} unidad «${unit.title}»`}
                              onClick={() =>
                                setArchived(
                                  unit.id,
                                  'unit',
                                  unit.status === 'archived',
                                )
                              }
                              size="icon-sm"
                              title={
                                unit.status === 'archived'
                                  ? 'Restaurar'
                                  : 'Archivar'
                              }
                              type="button"
                              variant="outline"
                            >
                              {unit.status === 'archived' ? (
                                <ArchiveRestore />
                              ) : (
                                <Archive />
                              )}
                            </Button>
                          </div>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="px-5 py-6 text-sm text-muted-foreground">
                  Este módulo todavía no tiene unidades.
                </p>
              )}
              {canManage && editable && module.status === 'active' ? (
                <form
                  action={(formData) => addUnit(module.id, formData)}
                  className="flex flex-wrap gap-3 border-t border-border bg-muted/10 px-5 py-4"
                >
                  <label className="academic-field min-w-56 flex-1">
                    Título de la nueva unidad
                    <input
                      className="academic-control"
                      maxLength={200}
                      name="unit-title"
                      required
                    />
                  </label>
                  <Button className="self-end" type="submit" variant="outline">
                    <Plus />
                    Añadir unidad
                  </Button>
                </form>
              ) : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-6 rounded-xl border border-dashed border-border p-6 text-muted-foreground">
          Aún no hay módulos. Empieza por definir la estructura del curso.
        </p>
      )}
    </section>
  );
}

function activityTypeLabel(value: string) {
  if (value === 'live_class') return 'Clase en vivo';
  if (value === 'assessment') return 'Evaluación';
  return 'Lección';
}

function activityCompletionLabel(value: string) {
  if (value === 'attendance') return 'Finaliza por asistencia';
  if (value === 'pass') return 'Finaliza al aprobar';
  return 'Finaliza manualmente';
}
