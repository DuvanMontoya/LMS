'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useRef, useState } from 'react';
import {
  Archive,
  ArchiveRestore,
  ArrowRightLeft,
  AudioLines,
  BookOpenText,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  CircleAlert,
  ClipboardCheck,
  FileCode2,
  FileText,
  Plus,
  Presentation,
  Settings2,
  Video,
} from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  LessonConfiguration,
  type LessonConfigurationInput,
} from '@/components/courses/lesson-configuration';
import {
  AssessmentActivityDialog,
  type AssessmentVersionOption,
} from '@/components/courses/assessment-activity-dialog';
import { LiveClassActivityDialog } from '@/components/courses/live-class-activity-dialog';
import { CompletionPolicyCard } from '@/components/courses/completion-policy-card';
import type { CourseTopicOption } from '@/lib/courses/curriculum-topics';
import type { components } from '@/lib/api/generated/platform';
import {
  RevisionConflictError,
  useCreateAssessmentActivity,
  useCreateLiveClassActivity,
  useCreateModule,
  useCreateUnit,
  useMoveActivityToModule,
  useReorderActivities,
  useReorderStructure,
  useSetStructureArchived,
  useUpdateLiveClassActivity,
  useUpdateStructure,
} from '@/lib/courses/hooks';

type Outline = components['schemas']['Outline'];
type Objective = components['schemas']['Objective'];
type Topic = CourseTopicOption;
type LiveClassBinding = components['schemas']['LiveClassActivityBinding'];
type LiveClassConfiguration =
  components['schemas']['LiveClassCourseActivityConfiguration'];
type LessonKind =
  | 'audio'
  | 'document'
  | 'latex_source'
  | 'markdown_source'
  | 'mediacms_video'
  | 'pdf'
  | 'slides';

const lessonKindOptions: readonly {
  description: string;
  kind: LessonKind;
  label: string;
}[] = [
  {
    kind: 'document',
    label: 'Documento',
    description: 'Documento académico estructurado y sus recursos privados.',
  },
  {
    kind: 'mediacms_video',
    label: 'Video MediaCMS',
    description: 'Únicamente el reproductor privado de MediaCMS.',
  },
  {
    kind: 'latex_source',
    label: 'LaTeX (.tex)',
    description: 'Archivo fuente UTF-8; nunca se ejecuta en el servidor.',
  },
  {
    kind: 'markdown_source',
    label: 'Markdown (.md)',
    description: 'Únicamente un archivo fuente Markdown UTF-8.',
  },
  {
    kind: 'pdf',
    label: 'PDF',
    description: 'Documento con vista previa privada y descarga temporal.',
  },
  {
    kind: 'slides',
    label: 'Diapositivas',
    description: 'PDF o PPTX validado como recurso privado.',
  },
  {
    kind: 'audio',
    label: 'Audio',
    description: 'Únicamente un reproductor de audio privado.',
  },
];
const deliveryStatusLabels: Record<string, string> = {
  document_empty: 'Documento vacío',
  document_missing: 'Sin documento',
  document_ready: 'Documento listo',
  mediacms_missing: 'Sin vídeo MediaCMS',
  mediacms_ready: 'Vídeo MediaCMS listo',
  resource_invalid: 'Archivo no apto',
  resource_missing: 'Sin archivo',
  resource_ready: 'Archivo listo',
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

function liveClassConfiguration(
  formData: FormData,
  expectedRevisionVersion: number,
): LiveClassConfiguration {
  const duration = Number(formData.get('live-duration'));
  const thresholdPercent = Number(formData.get('live-threshold'));
  const recordingMode = String(formData.get('live-recording-mode')) as
    'manual' | 'off';
  if (
    !Number.isFinite(duration) ||
    duration < 1 ||
    !Number.isFinite(thresholdPercent) ||
    thresholdPercent < 1 ||
    thresholdPercent > 100
  ) {
    throw new Error(
      'Define una duración válida y un umbral de asistencia entre 1 % y 100 %.',
    );
  }
  const learningObjectiveIds = formData.getAll('live-objective').map(String);
  if (!learningObjectiveIds.length) {
    throw new Error('Selecciona al menos un objetivo que trabaje esta clase.');
  }
  return {
    chat_enabled: formData.get('live-chat') === 'on',
    estimated_duration_minutes: duration,
    expected_revision_version: expectedRevisionVersion,
    join_after_minutes: Number(formData.get('live-join-after')),
    join_before_minutes: Number(formData.get('live-join-before')),
    learning_objective_ids: learningObjectiveIds,
    max_participants: Number(formData.get('live-max-participants')),
    minimum_attendance_basis_points: thresholdPercent * 100,
    // Disabled controls are omitted from FormData. Keep the persisted room
    // policy valid even when recording is off and the layout is not editable.
    recording_layout:
      recordingMode === 'off'
        ? 'screen_share'
        : (String(formData.get('live-recording-layout')) as
            'grid' | 'screen_share' | 'speaker'),
    recording_mode: recordingMode,
    recording_resolution:
      recordingMode === 'off'
        ? '1080p'
        : (String(formData.get('live-recording-resolution')) as
            '720p' | '1080p'),
    required: formData.get('live-required') === 'on',
    room_departure_timeout_seconds: Number(
      formData.get('live-departure-timeout'),
    ),
    room_empty_timeout_seconds: Number(formData.get('live-empty-timeout')) * 60,
    session_mode: String(formData.get('live-session-mode')) as
      'interactive' | 'webinar',
    student_audio_enabled: formData.get('live-student-audio') === 'on',
    student_screen_share_enabled: formData.get('live-student-screen') === 'on',
    student_video_enabled: formData.get('live-student-video') === 'on',
    summary: String(formData.get('live-summary') ?? ''),
    title: String(formData.get('live-title') ?? ''),
  };
}

export function StructureEditor({
  assessmentVersions,
  canManageAssessments,
  canManage,
  completionPolicy,
  courseSlug,
  liveClassBindings,
  objectives,
  outline,
  slug,
  topics,
}: Readonly<{
  assessmentVersions: AssessmentVersionOption[];
  canManageAssessments: boolean;
  canManage: boolean;
  completionPolicy: components['schemas']['CourseCompletionPolicy'];
  courseSlug: string;
  liveClassBindings: LiveClassBinding[];
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
  const mediaCmsAuthoringUrl =
    process.env.NEXT_PUBLIC_MEDIACMS_AUTHORING_URL?.trim() ??
    (process.env.NODE_ENV === 'development' ? 'http://localhost:8091/' : '');
  const moduleTitle = useRef<HTMLInputElement>(null);
  const path = { courseSlug, revisionId: outline.revision.id, slug };
  const createModule = useCreateModule(path);
  const createAssessmentActivity = useCreateAssessmentActivity(path);
  const createLiveClassActivity = useCreateLiveClassActivity(path);
  const updateLiveClassActivity = useUpdateLiveClassActivity(path);
  const createUnit = useCreateUnit(path);
  const moveAcrossModules = useMoveActivityToModule(path);
  const updateStructure = useUpdateStructure(path);
  const reorder = useReorderStructure(path);
  const reorderActivities = useReorderActivities(path);
  const archive = useSetStructureArchived(path);
  const liveClassBindingByActivityId = new Map(
    liveClassBindings.map((binding) => [binding.activity_id, binding]),
  );

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
          lesson_kind: String(
            formData.get('lesson-kind') ?? 'document',
          ) as LessonKind,
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

  async function addLiveClass(moduleId: string, formData: FormData) {
    setError('');
    try {
      const configuration = liveClassConfiguration(formData, version);
      const created = await createLiveClassActivity.mutateAsync({
        ...configuration,
        module_id: moduleId,
      });
      setVersion(created.revision_lock_version);
      setMessage('Clase en vivo añadida con su política de asistencia.');
      router.refresh();
      return true;
    } catch (cause) {
      failed(cause);
      return false;
    }
  }

  async function editLiveClass(activityId: string, formData: FormData) {
    setError('');
    try {
      const updated = await updateLiveClassActivity.mutateAsync({
        activityId,
        body: liveClassConfiguration(formData, version),
      });
      setVersion(updated.revision_lock_version);
      setMessage('Clase en vivo y política LiveKit actualizadas.');
      router.refresh();
      return true;
    } catch (cause) {
      failed(cause);
      return false;
    }
  }

  async function addAssessment(moduleId: string, formData: FormData) {
    setError('');
    const assessmentVersionId = String(
      formData.get('assessment-version') ?? '',
    );
    const option = assessmentVersions.find(
      (item) => item.id === assessmentVersionId,
    );
    if (!option) {
      setError('Selecciona una versión aprobada de evaluación.');
      return false;
    }
    try {
      const created = await createAssessmentActivity.mutateAsync({
        assessment_version_id: option.id,
        expected_revision_version: version,
        module_id: moduleId,
        required: formData.get('assessment-required') === 'on',
      });
      setVersion(created.revision_lock_version);
      setMessage(
        'Evaluación añadida con la duración y el umbral de su versión aprobada.',
      );
      router.refresh();
      return true;
    } catch (cause) {
      failed(cause);
      return false;
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

  async function saveUnitConfiguration(
    unitId: string,
    input: LessonConfigurationInput,
  ) {
    setError('');
    try {
      await updateStructure.mutateAsync({
        body: {
          estimated_duration_minutes: input.estimatedDurationMinutes,
          expected_version: version,
          learning_objective_ids: input.learningObjectiveIds,
          ...(input.mediaCmsFriendlyToken === undefined
            ? {}
            : {
                mediacms_video_friendly_token: input.mediaCmsFriendlyToken,
              }),
          summary: input.summary,
          title: input.title,
          topic_ids: input.topicIds,
        },
        id: unitId,
        kind: 'unit',
      });
      setVersion((current) => current + 1);
      setMessage('Información y alineación de la lección actualizadas.');
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

  async function moveActivity(
    moduleIndex: number,
    activityIndex: number,
    delta: number,
  ) {
    const courseModule = modules[moduleIndex];
    if (!courseModule) return;
    const activities = [...courseModule.activities];
    const target = activityIndex + delta;
    if (target < 0 || target >= activities.length) return;
    const moving = activities[activityIndex];
    const displaced = activities[target];
    if (!moving || !displaced) return;
    activities[activityIndex] = displaced;
    activities[target] = moving;
    try {
      const result = await reorderActivities.mutateAsync({
        body: {
          expected_version: version,
          ordered_ids: activities
            .filter((item) => item.status === 'active')
            .map((item) => item.id),
        },
        moduleId: courseModule.id,
      });
      const nextModules = [...modules];
      nextModules[moduleIndex] = { ...courseModule, activities };
      setModules(nextModules);
      setVersion(result.lock_version);
      setMessage(
        `«${moving.title}» ahora está en la posición ${target + 1} de la secuencia.`,
      );
    } catch (cause) {
      failed(cause);
    }
  }

  async function moveActivityToAnotherModule(
    activityId: string,
    targetModuleId: string,
  ) {
    setError('');
    try {
      const result = await moveAcrossModules.mutateAsync({
        activityId,
        body: {
          expected_version: version,
          target_module_id: targetModuleId,
        },
      });
      setVersion(result.lock_version);
      setMessage('Actividad movida al final del módulo seleccionado.');
      router.refresh();
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

  const activityCount = modules.reduce(
    (total, courseModule) => total + courseModule.activities.length,
    0,
  );
  const readyLessonCount = modules.reduce(
    (total, courseModule) =>
      total +
      courseModule.units.filter((unit) =>
        ['document_ready', 'mediacms_ready', 'resource_ready'].includes(
          unit.delivery_status,
        ),
      ).length,
    0,
  );
  const alignedLessonCount = modules.reduce(
    (total, courseModule) =>
      total +
      courseModule.units.filter(
        (unit) => unit.topics.length || unit.learning_objectives.length,
      ).length,
    0,
  );

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
      <div className="grid overflow-hidden rounded-xl border bg-card shadow-xs sm:grid-cols-2 xl:grid-cols-4">
        {[
          {
            label: 'Módulos',
            note: 'Bloques pedagógicos',
            value: modules.filter((item) => item.status === 'active').length,
          },
          {
            label: 'Secuencia',
            note: 'Actividades ordenadas',
            value: activityCount,
          },
          {
            label: 'Entregas listas',
            note: 'Lecciones listas para publicar',
            value: readyLessonCount,
          },
          {
            label: 'Alineación',
            note: 'Lecciones vinculadas',
            value: alignedLessonCount,
          },
        ].map((metric, index) => (
          <div
            className="border-b p-4 last:border-b-0 sm:even:border-l xl:border-b-0 xl:border-l xl:first:border-l-0"
            key={metric.label}
          >
            <div className="flex items-baseline justify-between gap-3">
              <span className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
                {String(index + 1).padStart(2, '0')} · {metric.label}
              </span>
              <strong className="text-xl tabular-nums">{metric.value}</strong>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{metric.note}</p>
          </div>
        ))}
      </div>
      {!editable ? (
        <Alert className="mt-4 border-amber-600/20 bg-amber-500/5">
          <CircleAlert className="text-amber-700" />
          <AlertTitle>Solo lectura</AlertTitle>
          <AlertDescription>
            La revisión está {statusLabel(outline.revision.authoring_status)}.
          </AlertDescription>
        </Alert>
      ) : null}
      {canManage && editable ? (
        <div className="mt-5 rounded-xl border bg-card p-4 shadow-xs md:flex md:items-end md:justify-between md:gap-6">
          <div className="mb-4 md:mb-0">
            <p className="text-xs font-semibold tracking-wider text-primary uppercase">
              {modules.some((module) => module.status === 'active')
                ? 'Amplía el recorrido'
                : 'Primer paso de esta revisión'}
            </p>
            <h3 className="mt-1 font-semibold">
              {modules.some((module) => module.status === 'active')
                ? 'Añade otro bloque pedagógico'
                : 'Crea un bloque pedagógico'}
            </h3>
            <p className="mt-1 max-w-xl text-sm text-muted-foreground">
              Cada módulo reúne una etapa del aprendizaje. Después agregarás las
              actividades en el orden exacto en que las verá el estudiante.
            </p>
          </div>
          <form
            action={addModule}
            className="flex min-w-0 flex-1 flex-wrap gap-3 md:max-w-xl"
          >
            <label className="academic-field min-w-56 flex-1">
              Nombre del módulo
              <input
                className="academic-control"
                maxLength={200}
                name="module-title"
                placeholder="Ej. Fundamentos de funciones"
                ref={moduleTitle}
                required
              />
            </label>
            <Button className="self-end" type="submit">
              <Plus />
              Crear módulo
            </Button>
          </form>
        </div>
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
                    {statusLabel(module.status)} · {module.activities.length}{' '}
                    {module.activities.length === 1
                      ? 'actividad'
                      : 'actividades'}
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
                    {module.activities.map((activity, activityIndex) => {
                      const lesson = activity.lesson_unit_id
                        ? module.units.find(
                            (unit) => unit.id === activity.lesson_unit_id,
                          )
                        : undefined;
                      const liveClassBinding =
                        activity.activity_type === 'live_class'
                          ? liveClassBindingByActivityId.get(activity.id)
                          : undefined;
                      return (
                        <li
                          className="flex items-start gap-3 rounded-lg border bg-background p-3 shadow-xs"
                          key={activity.id}
                        >
                          <span className="grid size-8 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
                            {activity.activity_type === 'live_class' ? (
                              <Video className="size-4" />
                            ) : activity.activity_type === 'assessment' ? (
                              <ClipboardCheck className="size-4" />
                            ) : (
                              <BookOpenText className="size-4" />
                            )}
                          </span>
                          <div className="min-w-0 flex-1">
                            <div className="flex flex-wrap items-center gap-2">
                              <strong>
                                {activity.position}. {activity.title}
                              </strong>
                              <Badge className="rounded" variant="outline">
                                {activityTypeLabel(activity.activity_type)}
                              </Badge>
                              {lesson ? (
                                <Badge className="rounded" variant="secondary">
                                  {lessonKindLabel(lesson.lesson_kind)}
                                </Badge>
                              ) : null}
                            </div>
                            <p className="mt-1 text-xs text-muted-foreground">
                              {activity.required ? 'Obligatoria' : 'Opcional'} ·{' '}
                              {activityCompletionLabel(
                                activity.completion_method,
                              )}
                              {activity.estimated_duration_minutes
                                ? ` · ${activity.estimated_duration_minutes} min`
                                : ''}
                            </p>
                            {activity.summary ? (
                              <p className="mt-2 text-sm text-muted-foreground">
                                {activity.summary}
                              </p>
                            ) : null}
                            {activity.activity_type === 'live_class' &&
                            canManage &&
                            editable ? (
                              <div className="mt-3 flex flex-wrap items-center gap-2">
                                <LiveClassActivityDialog
                                  activity={activity}
                                  {...(liveClassBinding
                                    ? { binding: liveClassBinding }
                                    : {})}
                                  isSaving={updateLiveClassActivity.isPending}
                                  objectives={objectives}
                                  onSubmit={(formData) =>
                                    editLiveClass(activity.id, formData)
                                  }
                                />
                                {!liveClassBinding ? (
                                  <span className="text-xs text-amber-700">
                                    Completa la política LiveKit heredada.
                                  </span>
                                ) : null}
                              </div>
                            ) : null}
                            {lesson ? (
                              <div className="mt-2">
                                <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                                  <span>
                                    {deliveryStatusLabels[
                                      lesson.delivery_status
                                    ] ?? lesson.delivery_status}
                                  </span>
                                  <span aria-hidden="true">·</span>
                                  <span>
                                    {lesson.topics.length}{' '}
                                    {lesson.topics.length === 1
                                      ? 'tema'
                                      : 'temas'}{' '}
                                    · {lesson.learning_objectives.length}{' '}
                                    {lesson.learning_objectives.length === 1
                                      ? 'objetivo'
                                      : 'objetivos'}
                                  </span>
                                  {lesson.lesson_kind === 'document' &&
                                  lesson.content_version ? (
                                    <>
                                      <span aria-hidden="true">·</span>
                                      <span>
                                        Versión {lesson.content_version}
                                      </span>
                                    </>
                                  ) : null}
                                </div>
                                {lesson.status === 'active' ? (
                                  <div className="mt-3 flex flex-wrap items-center gap-2">
                                    {lesson.lesson_kind === 'document' ? (
                                      <Button
                                        asChild
                                        size="sm"
                                        variant="outline"
                                      >
                                        <Link
                                          href={`/organizaciones/${slug}/cursos/${courseSlug}/unidades/${lesson.id}/contenido`}
                                        >
                                          <BookOpenText />
                                          {canManage && editable
                                            ? 'Editar documento'
                                            : 'Ver documento'}
                                        </Link>
                                      </Button>
                                    ) : null}
                                    {canManage && editable ? (
                                      <details className="w-full overflow-hidden rounded-lg border bg-muted/10">
                                        <summary
                                          aria-label={`Configurar lección «${lesson.title}»`}
                                          className="flex cursor-pointer list-none items-center justify-between gap-3 px-3 py-2.5 text-sm font-medium marker:hidden hover:bg-muted/25"
                                        >
                                          <span className="flex items-center gap-2">
                                            <Settings2 className="size-4 text-primary" />
                                            Configurar lección
                                          </span>
                                          <span className="text-xs font-normal text-muted-foreground">
                                            Información · temas · objetivos
                                          </span>
                                        </summary>
                                        <div className="border-t p-2 sm:p-3">
                                          <LessonConfiguration
                                            alignedSubjects={outline.subjects}
                                            courseSlug={courseSlug}
                                            isSaving={updateStructure.isPending}
                                            lesson={lesson}
                                            mediaCmsAuthoringUrl={
                                              mediaCmsAuthoringUrl
                                            }
                                            objectives={objectives}
                                            onArchive={() =>
                                              setArchived(
                                                lesson.id,
                                                'unit',
                                                false,
                                              )
                                            }
                                            onDeliverySaved={(
                                              lockVersion,
                                              message,
                                            ) => {
                                              setVersion(lockVersion);
                                              setMessage(message);
                                              router.refresh();
                                            }}
                                            onSave={(input) =>
                                              saveUnitConfiguration(
                                                lesson.id,
                                                input,
                                              )
                                            }
                                            organizationSlug={slug}
                                            revisionId={outline.revision.id}
                                            revisionVersion={version}
                                            topics={topics}
                                          />
                                        </div>
                                      </details>
                                    ) : null}
                                  </div>
                                ) : null}
                              </div>
                            ) : null}
                          </div>
                          {canManage && editable ? (
                            <div className="flex shrink-0 items-center gap-1">
                              {activity.activity_type !== 'lesson' ? (
                                <details className="relative">
                                  <summary
                                    aria-label={`Mover «${activity.title}» a otro módulo`}
                                    className="flex size-8 cursor-pointer list-none items-center justify-center rounded-md text-muted-foreground marker:hidden hover:bg-muted hover:text-foreground"
                                    title="Mover a otro módulo"
                                  >
                                    <ArrowRightLeft className="size-4" />
                                  </summary>
                                  <div className="absolute right-0 z-30 mt-1 w-72 rounded-xl border bg-popover p-3 text-popover-foreground shadow-lg">
                                    <label className="text-xs font-semibold">
                                      Mover al final de
                                      <select
                                        aria-label={`Módulo de destino para «${activity.title}»`}
                                        className="academic-control mt-1.5"
                                        disabled={moveAcrossModules.isPending}
                                        onChange={(event) => {
                                          if (
                                            event.target.value !== module.id
                                          ) {
                                            void moveActivityToAnotherModule(
                                              activity.id,
                                              event.target.value,
                                            );
                                          }
                                        }}
                                        value={module.id}
                                      >
                                        {modules
                                          .filter(
                                            (candidate) =>
                                              candidate.status === 'active',
                                          )
                                          .map((candidate) => (
                                            <option
                                              key={candidate.id}
                                              value={candidate.id}
                                            >
                                              {candidate.title}
                                            </option>
                                          ))}
                                      </select>
                                    </label>
                                    <p className="mt-2 text-xs text-muted-foreground">
                                      Conserva la configuración y la vinculación
                                      de la actividad.
                                    </p>
                                  </div>
                                </details>
                              ) : null}
                              <Button
                                aria-label={`Mover «${activity.title}» una posición arriba`}
                                disabled={activityIndex === 0}
                                onClick={() =>
                                  moveActivity(moduleIndex, activityIndex, -1)
                                }
                                size="icon-sm"
                                title="Mover arriba"
                                type="button"
                                variant="ghost"
                              >
                                <ChevronUp />
                              </Button>
                              <Button
                                aria-label={`Mover «${activity.title}» una posición abajo`}
                                disabled={
                                  activityIndex === module.activities.length - 1
                                }
                                onClick={() =>
                                  moveActivity(moduleIndex, activityIndex, 1)
                                }
                                size="icon-sm"
                                title="Mover abajo"
                                type="button"
                                variant="ghost"
                              >
                                <ChevronDown />
                              </Button>
                            </div>
                          ) : null}
                        </li>
                      );
                    })}
                  </ol>
                ) : null}
                {canManage && editable && module.status === 'active' ? (
                  <div
                    className={
                      canManageAssessments
                        ? 'mt-3 grid gap-2 xl:grid-cols-3'
                        : 'mt-3 grid gap-2 lg:grid-cols-2'
                    }
                  >
                    <details className="group rounded-lg border bg-background">
                      <summary className="flex cursor-pointer list-none items-start gap-3 px-3 py-3 marker:hidden hover:bg-muted/20">
                        <span className="rounded-md bg-primary/10 p-1.5 text-primary">
                          <BookOpenText className="size-4" />
                        </span>
                        <span>
                          <span className="block text-sm font-semibold">
                            Añadir lección
                          </span>
                          <span className="mt-0.5 block text-xs font-normal text-muted-foreground">
                            Contenido asincrónico y alineación
                          </span>
                        </span>
                      </summary>
                      <form
                        action={(formData) => addUnit(module.id, formData)}
                        className="grid gap-3 border-t p-3"
                      >
                        <label className="academic-field">
                          Título de la lección
                          <input
                            className="academic-control"
                            maxLength={200}
                            name="unit-title"
                            placeholder="Ej. Dominio y rango de una función"
                            required
                          />
                        </label>
                        <fieldset className="grid gap-2">
                          <legend className="text-sm font-medium">
                            Modalidad de la lección
                          </legend>
                          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
                            {lessonKindOptions.map((option) => (
                              <label
                                className="cursor-pointer rounded-md border p-2.5 text-sm transition-colors has-[:checked]:border-primary has-[:checked]:bg-primary/5"
                                key={option.kind}
                              >
                                <input
                                  className="sr-only"
                                  defaultChecked={option.kind === 'document'}
                                  name="lesson-kind"
                                  type="radio"
                                  value={option.kind}
                                />
                                <span className="flex items-center gap-2 font-medium">
                                  <LessonKindIcon kind={option.kind} />
                                  {option.label}
                                </span>
                                <span className="mt-1 block text-xs leading-4 text-muted-foreground">
                                  {option.description}
                                </span>
                              </label>
                            ))}
                          </div>
                        </fieldset>
                        {mediaCmsAuthoringUrl ? (
                          <Button
                            asChild
                            className="w-fit"
                            size="sm"
                            variant="outline"
                          >
                            <a
                              href={mediaCmsAuthoringUrl}
                              rel="noreferrer"
                              target="_blank"
                            >
                              <Video /> Abrir MediaCMS para autoría de vídeo
                            </a>
                          </Button>
                        ) : null}
                        <p className="text-xs leading-5 text-muted-foreground">
                          Se crea una única lección y su actividad en la
                          secuencia. La modalidad queda fijada; el contenido y
                          la alineación se completan después sin crear otra
                          actividad.
                        </p>
                        <Button className="w-fit" type="submit">
                          <Plus /> Crear lección
                        </Button>
                      </form>
                    </details>
                    <LiveClassActivityDialog
                      isSaving={createLiveClassActivity.isPending}
                      objectives={objectives}
                      onSubmit={(formData) => addLiveClass(module.id, formData)}
                    />
                    {canManageAssessments ? (
                      <AssessmentActivityDialog
                        courseObjectiveIds={objectives.map(
                          (objective) => objective.id,
                        )}
                        isSaving={createAssessmentActivity.isPending}
                        onSubmit={(formData) =>
                          addAssessment(module.id, formData)
                        }
                        options={assessmentVersions}
                        slug={slug}
                      />
                    ) : null}
                  </div>
                ) : null}
              </section>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-6 rounded-xl border border-dashed border-border p-6 text-muted-foreground">
          Aún no hay módulos. Empieza por definir la estructura del curso.
        </p>
      )}
      {canManage && editable ? (
        <CompletionPolicyCard
          courseSlug={courseSlug}
          onConfirmed={() => {
            setVersion((current) => current + 1);
            setMessage('Política de finalización confirmada.');
            router.refresh();
          }}
          policy={completionPolicy}
          revisionId={outline.revision.id}
          revisionVersion={version}
          slug={slug}
        />
      ) : null}
    </section>
  );
}

function activityTypeLabel(value: string) {
  if (value === 'live_class') return 'Clase en vivo';
  if (value === 'assessment') return 'Evaluación';
  return 'Lección';
}

function lessonKindLabel(value: string) {
  return (
    lessonKindOptions.find((option) => option.kind === value)?.label ?? value
  );
}

function LessonKindIcon({ kind }: Readonly<{ kind: LessonKind }>) {
  const className = 'size-4 text-primary';
  if (kind === 'audio') return <AudioLines className={className} />;
  if (kind === 'latex_source' || kind === 'markdown_source') {
    return <FileCode2 className={className} />;
  }
  if (kind === 'mediacms_video') return <Video className={className} />;
  if (kind === 'slides') return <Presentation className={className} />;
  return <FileText className={className} />;
}

function activityCompletionLabel(value: string) {
  if (value === 'attendance') return 'Finaliza por asistencia';
  if (value === 'pass') return 'Finaliza al aprobar';
  return 'Finaliza manualmente';
}
