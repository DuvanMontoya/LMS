'use client';

import {
  Archive,
  ArrowDown,
  ArrowUp,
  LoaderCircle,
  RefreshCw,
  Save,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { MutationError } from '@/components/assessments/authoring-forms';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  addGradebookColumn,
  activateGradebook,
  archiveGradebookColumn,
  createGradebook,
  createRegradeJob,
  getAssessmentAnalyticsJob,
  reorderGradebookColumns,
  refreshAssessmentAnalytics,
  retryRegradeJob,
  updateGradebookColumn,
} from '@/lib/assessments/api';

function PendingIcon() {
  return <LoaderCircle className="size-4 animate-spin" />;
}

type AdvancedVersionOption = {
  deliveries: readonly { id: string; label: string }[];
  id: string;
  label: string;
  revisions: readonly { id: string; label: string; number: number }[];
};

export function CreateRegradeJobForm({
  slug,
  versionOptions,
}: Readonly<{
  slug: string;
  versionOptions: readonly AdvancedVersionOption[];
}>) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [selectedVersionId, setSelectedVersionId] = useState(
    versionOptions[0]?.id ?? '',
  );
  const selectedVersion = versionOptions.find(
    (option) => option.id === selectedVersionId,
  );
  return (
    <form
      className="space-y-5"
      onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const deliveryId = String(form.get('delivery_id') ?? '');
        setPending(true);
        setError(null);
        void createRegradeJob(slug, {
          assessment_version_id: String(form.get('assessment_version_id')),
          ...(deliveryId ? { delivery_id: deliveryId } : {}),
          grading_revision_id: String(form.get('grading_revision_id')),
          preserve_manual_grades: true,
          reason: String(form.get('reason')),
        })
          .then((job) => {
            router.push(
              `/organizaciones/${slug}/evaluaciones/regrading/${job.id}`,
            );
            router.refresh();
          })
          .catch(setError)
          .finally(() => setPending(false));
      }}
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <label className="space-y-1.5">
          <span className="text-sm font-medium">Versión de evaluación</span>
          <select
            className="academic-control"
            name="assessment_version_id"
            onChange={(event) => setSelectedVersionId(event.target.value)}
            required
            value={selectedVersionId}
          >
            <option value="">Selecciona una versión</option>
            {versionOptions.map((version) => (
              <option key={version.id} value={version.id}>
                {version.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1.5">
          <span className="text-sm font-medium">Revisión de calificación</span>
          <select
            className="academic-control"
            key={selectedVersionId}
            name="grading_revision_id"
            required
          >
            <option value="">Selecciona una revisión</option>
            {selectedVersion?.revisions.map((revision) => (
              <option key={revision.id} value={revision.id}>
                {revision.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1.5 lg:col-span-2">
          <span className="text-sm font-medium">Alcance</span>
          <select className="academic-control" name="delivery_id">
            <option value="">Todos los intentos de esta versión</option>
            {selectedVersion?.deliveries.map((delivery) => (
              <option key={delivery.id} value={delivery.id}>
                Sólo la entrega «{delivery.label}»
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className="space-y-1.5">
        <span className="text-sm font-medium">Justificación auditable</span>
        <Input
          minLength={10}
          name="reason"
          placeholder="Corrección aprobada de la política de puntaje"
          required
        />
      </label>
      <label className="flex items-start gap-3 rounded-lg border border-primary/15 bg-primary/5 p-4 text-sm">
        <input
          checked={confirmed}
          className="mt-0.5 size-4"
          onChange={(event) => setConfirmed(event.target.checked)}
          type="checkbox"
        />
        <span>
          <strong className="block font-semibold">
            Confirmo el alcance de esta recalificación
          </strong>
          <span className="mt-1 block leading-5 text-muted-foreground">
            Se crearán nuevas versiones de calificación, se preservarán las
            decisiones manuales y ningún resultado histórico será sobrescrito.
          </span>
        </span>
      </label>
      <MutationError error={error} />
      <Button disabled={pending || !confirmed} type="submit">
        {pending ? <PendingIcon /> : <RefreshCw />}
        Crear recalificación
      </Button>
    </form>
  );
}

export function RetryRegradeButton({
  expectedVersion,
  jobId,
  slug,
}: Readonly<{ expectedVersion: number; jobId: string; slug: string }>) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  return (
    <div>
      <Button
        disabled={pending}
        onClick={() => {
          setPending(true);
          setError(null);
          void retryRegradeJob(slug, jobId, expectedVersion)
            .then(() => router.refresh())
            .catch(setError)
            .finally(() => setPending(false));
        }}
        variant="outline"
      >
        {pending ? <PendingIcon /> : <RefreshCw />}
        Reintentar fallidos
      </Button>
      <MutationError error={error} />
    </div>
  );
}

export function CreateGradebookForm({
  groupOptions,
  slug,
}: Readonly<{
  groupOptions: readonly {
    courseGroupId: string;
    courseReleaseId: string;
    label: string;
  }[];
  slug: string;
}>) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  return (
    <form
      className="flex flex-col gap-3 sm:flex-row sm:items-end"
      onSubmit={(event) => {
        event.preventDefault();
        const courseGroupId = String(
          new FormData(event.currentTarget).get('course_group_id'),
        );
        const option = groupOptions.find(
          (candidate) => candidate.courseGroupId === courseGroupId,
        );
        if (!option) return;
        setPending(true);
        setError(null);
        void createGradebook(slug, {
          course_group_id: option.courseGroupId,
          course_release_id: option.courseReleaseId,
        })
          .then((gradebook) =>
            router.push(
              `/organizaciones/${slug}/evaluaciones/gradebooks/${gradebook.id}`,
            ),
          )
          .catch(setError)
          .finally(() => setPending(false));
      }}
    >
      <label className="min-w-0 flex-1 space-y-1.5">
        <span className="text-sm font-medium">Grupo de curso</span>
        <select className="academic-control" name="course_group_id" required>
          <option value="">Selecciona un grupo</option>
          {groupOptions.map((group) => (
            <option key={group.courseGroupId} value={group.courseGroupId}>
              {group.label}
            </option>
          ))}
        </select>
      </label>
      <Button disabled={pending} type="submit">
        {pending ? <PendingIcon /> : null}
        Crear libro
      </Button>
      <MutationError error={error} />
    </form>
  );
}

export function AddGradebookColumnForm({
  deliveries,
  expectedVersion,
  gradebookId,
  slug,
}: Readonly<{
  deliveries: readonly { id: string; label: string }[];
  expectedVersion: number;
  gradebookId: string;
  slug: string;
}>) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  return (
    <form
      className="assessment-workbench"
      onSubmit={(event) => {
        event.preventDefault();
        const formElement = event.currentTarget;
        const form = new FormData(formElement);
        setPending(true);
        setError(null);
        void addGradebookColumn(slug, gradebookId, {
          attempt_aggregation:
            form.get('attempt_aggregation') === 'latest' ? 'latest' : 'highest',
          delivery_id: String(form.get('delivery_id')),
          expected_version: expectedVersion,
          required: form.get('required') === 'on',
          title: String(form.get('title')),
          weight_basis_points: Math.round(
            Number(form.get('weight_percent')) * 100,
          ),
        })
          .then(() => {
            formElement.reset();
            router.refresh();
          })
          .catch(setError)
          .finally(() => setPending(false));
      }}
    >
      <div className="grid gap-4 lg:grid-cols-2">
        <label className="space-y-1.5">
          <span className="text-sm font-medium">Evaluación entregada</span>
          <select className="academic-control" name="delivery_id" required>
            <option value="">Selecciona una entrega</option>
            {deliveries.map((delivery) => (
              <option key={delivery.id} value={delivery.id}>
                {delivery.label}
              </option>
            ))}
          </select>
        </label>
        <label className="space-y-1.5">
          <span className="text-sm font-medium">Título de columna</span>
          <Input maxLength={200} name="title" required />
        </label>
        <label className="space-y-1.5">
          <span className="text-sm font-medium">Peso porcentual</span>
          <Input
            max="100"
            min="0.01"
            name="weight_percent"
            required
            step="0.01"
            type="number"
          />
        </label>
        <label className="space-y-1.5">
          <span className="text-sm font-medium">Agregación de intentos</span>
          <select className="academic-control" name="attempt_aggregation">
            <option value="highest">Puntaje más alto</option>
            <option value="latest">Último intento</option>
          </select>
        </label>
      </div>
      <label className="flex items-center gap-2 text-sm">
        <input defaultChecked name="required" type="checkbox" />
        Columna requerida para completar el libro
      </label>
      <MutationError error={error} />
      <Button disabled={pending} type="submit">
        {pending ? <PendingIcon /> : null}
        Añadir columna
      </Button>
    </form>
  );
}

type GradebookColumnOption = {
  attempt_aggregation: 'highest' | 'latest';
  id: string;
  position: number;
  required: boolean;
  status: 'active' | 'archived';
  title: string;
  weight_basis_points: number;
};

export function GradebookColumnManager({
  columns,
  expectedVersion,
  gradebookId,
  slug,
}: Readonly<{
  columns: readonly GradebookColumnOption[];
  expectedVersion: number;
  gradebookId: string;
  slug: string;
}>) {
  const router = useRouter();
  const [pending, setPending] = useState('');
  const [error, setError] = useState<Error | null>(null);
  const ordered = [...columns].sort((left, right) => {
    return left.position - right.position;
  });
  const active = ordered.filter((column) => column.status === 'active');
  const archived = ordered.filter((column) => column.status === 'archived');

  function complete(operation: Promise<unknown>, key: string) {
    setPending(key);
    setError(null);
    void operation
      .then(() => router.refresh())
      .catch(setError)
      .finally(() => setPending(''));
  }

  function move(columnId: string, offset: -1 | 1) {
    const current = active.findIndex((column) => column.id === columnId);
    const destination = current + offset;
    if (current < 0 || destination < 0 || destination >= active.length) return;
    const ids = active.map((column) => column.id);
    [ids[current], ids[destination]] = [ids[destination]!, ids[current]!];
    complete(
      reorderGradebookColumns(slug, gradebookId, {
        column_ids: [...ids, ...archived.map((column) => column.id)],
        expected_version: expectedVersion,
      }),
      `move:${columnId}`,
    );
  }

  return (
    <section className="assessment-builder-section">
      <header className="assessment-builder-section__header">
        <div>
          <h2>Diseño del libro</h2>
          <p>
            Ajusta títulos, pesos y agregación; ordena las columnas activas o
            archívalas sin borrar historial.
          </p>
        </div>
        <span className="text-sm text-muted-foreground">
          {active.length} activas ·{' '}
          {(
            active.reduce(
              (total, column) => total + column.weight_basis_points,
              0,
            ) / 100
          ).toFixed(2)}
          % configurado
        </span>
      </header>
      <div className="space-y-3">
        {ordered.map((column) => {
          const activeIndex = active.findIndex((item) => item.id === column.id);
          return (
            <article
              className="rounded-xl border border-border bg-background p-4"
              key={column.id}
            >
              <form
                className="grid gap-3 lg:grid-cols-[minmax(0,1fr)_10rem_12rem_auto]"
                onSubmit={(event) => {
                  event.preventDefault();
                  const form = new FormData(event.currentTarget);
                  complete(
                    updateGradebookColumn(slug, gradebookId, column.id, {
                      attempt_aggregation:
                        form.get('attempt_aggregation') === 'latest'
                          ? 'latest'
                          : 'highest',
                      expected_version: expectedVersion,
                      required: form.get('required') === 'on',
                      title: String(form.get('title')),
                      weight_basis_points: Math.round(
                        Number(form.get('weight_percent')) * 100,
                      ),
                    }),
                    `save:${column.id}`,
                  );
                }}
              >
                <label className="space-y-1">
                  <span className="text-xs font-medium">Título</span>
                  <Input
                    defaultValue={column.title}
                    disabled={column.status === 'archived'}
                    maxLength={200}
                    name="title"
                    required
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium">Peso %</span>
                  <Input
                    defaultValue={(column.weight_basis_points / 100).toFixed(2)}
                    disabled={column.status === 'archived'}
                    max="100"
                    min="0.01"
                    name="weight_percent"
                    required
                    step="0.01"
                    type="number"
                  />
                </label>
                <label className="space-y-1">
                  <span className="text-xs font-medium">Intento usado</span>
                  <select
                    className="academic-control"
                    defaultValue={column.attempt_aggregation}
                    disabled={column.status === 'archived'}
                    name="attempt_aggregation"
                  >
                    <option value="highest">Puntaje más alto</option>
                    <option value="latest">Último intento</option>
                  </select>
                </label>
                <div className="flex flex-wrap items-end gap-2">
                  {column.status === 'active' ? (
                    <>
                      <label className="mb-2 flex items-center gap-2 text-xs">
                        <input
                          defaultChecked={column.required}
                          name="required"
                          type="checkbox"
                        />
                        Requerida
                      </label>
                      <Button
                        aria-label={`Guardar ${column.title}`}
                        disabled={Boolean(pending)}
                        size="sm"
                        type="submit"
                        variant="outline"
                      >
                        {pending === `save:${column.id}` ? (
                          <PendingIcon />
                        ) : (
                          <Save />
                        )}
                      </Button>
                      <Button
                        aria-label={`Subir ${column.title}`}
                        disabled={Boolean(pending) || activeIndex === 0}
                        onClick={() => move(column.id, -1)}
                        size="sm"
                        type="button"
                        variant="outline"
                      >
                        <ArrowUp />
                      </Button>
                      <Button
                        aria-label={`Bajar ${column.title}`}
                        disabled={
                          Boolean(pending) || activeIndex === active.length - 1
                        }
                        onClick={() => move(column.id, 1)}
                        size="sm"
                        type="button"
                        variant="outline"
                      >
                        <ArrowDown />
                      </Button>
                      <Button
                        aria-label={`Archivar ${column.title}`}
                        disabled={Boolean(pending)}
                        onClick={() =>
                          complete(
                            archiveGradebookColumn(
                              slug,
                              gradebookId,
                              column.id,
                              expectedVersion,
                            ),
                            `archive:${column.id}`,
                          )
                        }
                        size="sm"
                        type="button"
                        variant="outline"
                      >
                        {pending === `archive:${column.id}` ? (
                          <PendingIcon />
                        ) : (
                          <Archive />
                        )}
                      </Button>
                    </>
                  ) : (
                    <span className="mb-2 text-xs text-muted-foreground">
                      Archivada
                    </span>
                  )}
                </div>
              </form>
            </article>
          );
        })}
        {!ordered.length ? (
          <p className="text-sm text-muted-foreground">
            Añade la primera columna para comenzar a diseñar el libro.
          </p>
        ) : null}
      </div>
      <MutationError error={error} />
    </section>
  );
}

export function ActivateGradebookButton({
  expectedVersion,
  gradebookId,
  ready,
  slug,
}: Readonly<{
  expectedVersion: number;
  gradebookId: string;
  ready: boolean;
  slug: string;
}>) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  return (
    <div>
      <Button
        disabled={pending || !ready}
        onClick={() => {
          setPending(true);
          setError(null);
          void activateGradebook(slug, gradebookId, expectedVersion)
            .then(() => router.refresh())
            .catch(setError)
            .finally(() => setPending(false));
        }}
      >
        {pending ? <PendingIcon /> : null}
        Activar libro
      </Button>
      {!ready ? (
        <p className="mt-1 max-w-56 text-xs text-muted-foreground">
          Configura columnas activas contiguas cuyos pesos sumen 100 %.
        </p>
      ) : null}
      <MutationError error={error} />
    </div>
  );
}

export function AnalyticsLookupForm({
  slug,
  versionOptions,
}: Readonly<{
  slug: string;
  versionOptions: readonly Pick<AdvancedVersionOption, 'id' | 'label'>[];
}>) {
  const router = useRouter();
  return (
    <form
      className="flex flex-col gap-3 sm:flex-row sm:items-end"
      onSubmit={(event) => {
        event.preventDefault();
        const versionId = String(
          new FormData(event.currentTarget).get('assessment_version_id'),
        ).trim();
        if (versionId) {
          router.push(
            `/organizaciones/${slug}/evaluaciones/analitica/${versionId}`,
          );
        }
      }}
    >
      <label className="min-w-0 flex-1 space-y-1.5">
        <span className="text-sm font-medium">Versión de evaluación</span>
        <select
          className="academic-control"
          name="assessment_version_id"
          required
        >
          <option value="">Selecciona una versión</option>
          {versionOptions.map((version) => (
            <option key={version.id} value={version.id}>
              {version.label}
            </option>
          ))}
        </select>
      </label>
      <Button type="submit">Abrir analítica</Button>
    </form>
  );
}

export function AnalyticsRefreshForm({
  assessmentVersionId,
  revisions,
  slug,
}: Readonly<{
  assessmentVersionId: string;
  revisions: readonly { id: string; label: string }[];
  slug: string;
}>) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [jobId, setJobId] = useState('');
  const [jobStatus, setJobStatus] = useState('');

  useEffect(() => {
    if (!jobId || ['completed', 'failed'].includes(jobStatus)) return;
    let cancelled = false;
    let timeoutId: number | undefined;
    let attempts = 0;
    const poll = () => {
      attempts += 1;
      void getAssessmentAnalyticsJob(slug, jobId)
        .then((job) => {
          if (cancelled) return;
          setJobStatus(job.status);
          if (job.status === 'completed') {
            router.refresh();
          } else if (job.status !== 'failed' && attempts < 20) {
            timeoutId = window.setTimeout(poll, 1500);
          }
        })
        .catch((pollError: Error) => {
          if (!cancelled) setError(pollError);
        });
    };
    timeoutId = window.setTimeout(poll, 1000);
    return () => {
      cancelled = true;
      if (timeoutId !== undefined) window.clearTimeout(timeoutId);
    };
  }, [jobId, jobStatus, router, slug]);

  return (
    <form
      className="flex flex-col gap-3 sm:flex-row sm:items-end"
      onSubmit={(event) => {
        event.preventDefault();
        const revisionId = String(
          new FormData(event.currentTarget).get('grading_revision_id'),
        );
        setPending(true);
        setError(null);
        setJobId('');
        setJobStatus('');
        void refreshAssessmentAnalytics(slug, {
          assessment_version_id: assessmentVersionId,
          grading_revision_id: revisionId,
        })
          .then((job) => {
            setJobId(job.id);
            setJobStatus(job.status);
          })
          .catch(setError)
          .finally(() => setPending(false));
      }}
    >
      <label className="min-w-0 flex-1 space-y-1.5">
        <span className="text-sm font-medium">Revisión de calificación</span>
        <select
          className="academic-control"
          name="grading_revision_id"
          required
        >
          <option value="">Selecciona una revisión</option>
          {revisions.map((revision) => (
            <option key={revision.id} value={revision.id}>
              {revision.label}
            </option>
          ))}
        </select>
      </label>
      <Button disabled={pending} type="submit" variant="outline">
        {pending ? <PendingIcon /> : <RefreshCw />}
        Actualizar snapshot
      </Button>
      {jobId ? (
        <p aria-live="polite" className="text-sm text-muted-foreground">
          {jobStatus === 'completed'
            ? 'Snapshot actualizado.'
            : jobStatus === 'failed'
              ? 'La actualización no pudo completarse. Puedes reintentarlo.'
              : 'Actualización en proceso; esta vista se renovará al terminar.'}
        </p>
      ) : null}
      <MutationError error={error} />
    </form>
  );
}
