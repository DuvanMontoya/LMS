'use client';

import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  Clock3,
  Rocket,
  Send,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useState } from 'react';

import { MutationError } from '@/components/assessments/authoring-forms';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  activateAssessmentDelivery,
  assignAssessmentCohort,
  assignAssessmentDelivery,
  createAssessmentDelivery,
  useAssessmentMutation,
  withdrawAssessmentDelivery,
} from '@/lib/assessments/hooks';
import type {
  AssessmentDeliveryPage,
  AssessmentVersion,
} from '@/lib/assessments/server';

type EnrollmentOption = {
  cohort_id: string | null;
  cohort_name: string | null;
  course_title: string;
  current_release_assignment_id: string | null;
  release_number: number;
  student_email: string;
};

type ReleaseOption = {
  courseTitle: string;
  id: string;
  number: number;
};

type ActivityOption = {
  course_group_name: string;
  id: string;
  module_position: number;
  position: number;
  releaseId: string;
  title: string;
};

export function DeliveryManager({
  activityOptions,
  canManage,
  canViewResults,
  deliveries,
  enrollments,
  releaseOptions,
  slug,
  versions,
}: Readonly<{
  activityOptions: ActivityOption[];
  canManage: boolean;
  canViewResults: boolean;
  deliveries: AssessmentDeliveryPage;
  enrollments: EnrollmentOption[];
  releaseOptions: ReleaseOption[];
  slug: string;
  versions: AssessmentVersion[];
}>) {
  const router = useRouter();
  const [name, setName] = useState('');
  const [versionId, setVersionId] = useState('');
  const [opensAt, setOpensAt] = useState('');
  const [closesAt, setClosesAt] = useState('');
  const [releaseId, setReleaseId] = useState('');
  const [activityId, setActivityId] = useState('');
  const eligibleActivities = activityOptions.filter(
    (activity) => activity.releaseId === releaseId,
  );
  const create = useAssessmentMutation(() =>
    createAssessmentDelivery(slug, {
      assessment_version_id: versionId,
      closes_at: closesAt ? new Date(closesAt).toISOString() : null,
      course_release_id: releaseId || null,
      course_group_activity_id: activityId || null,
      name,
      opens_at: opensAt ? new Date(opensAt).toISOString() : null,
    }),
  );
  const activeCount = deliveries.results.filter(
    (delivery) => delivery.status === 'active',
  ).length;
  return (
    <>
      <section className="assessment-delivery-summary">
        <div>
          <p className="assessment-rail-kicker">Operación de evaluaciones</p>
          <h2>Programación y distribución</h2>
          <p>
            Las entregas fijan una versión inmutable y una población con release
            efectivo; no alteran el contenido aprobado.
          </p>
        </div>
        <dl>
          {canManage ? (
            <div>
              <dt>Versiones elegibles</dt>
              <dd>{versions.length}</dd>
            </div>
          ) : null}
          <div>
            <dt>Entregas activas</dt>
            <dd>{activeCount}</dd>
          </div>
          {canManage ? (
            <div>
              <dt>Matrículas vigentes</dt>
              <dd>{enrollments.length}</dd>
            </div>
          ) : null}
        </dl>
      </section>
      <div
        className={
          canManage
            ? 'mt-5 grid gap-5 xl:grid-cols-[24rem_minmax(0,1fr)]'
            : 'mt-5'
        }
      >
        {canManage ? (
          <section className="assessment-delivery-builder">
            <header>
              <span className="assessment-icon-box">
                <Send />
              </span>
              <div>
                <p className="assessment-rail-kicker">Nueva operación</p>
                <h2>Configurar entrega</h2>
              </div>
            </header>
            <div className="assessment-delivery-builder__body">
              <Label htmlFor="delivery-name">Nombre</Label>
              <Input
                id="delivery-name"
                onChange={(event) => setName(event.target.value)}
                placeholder="Ej. Diagnóstico inicial — grupo A"
                value={name}
              />
              <Label htmlFor="delivery-version">Versión inmutable</Label>
              <select
                className="academic-control"
                id="delivery-version"
                onChange={(event) => setVersionId(event.target.value)}
                value={versionId}
              >
                <option value="">Selecciona una versión aprobada</option>
                {versions.map((version) => (
                  <option key={version.id} value={version.id}>
                    {version.title} · v{version.number} ·{' '}
                    {version.maximum_score} pts
                  </option>
                ))}
              </select>
              <Label htmlFor="delivery-release">
                Release de curso (opcional)
              </Label>
              <select
                className="academic-control"
                id="delivery-release"
                onChange={(event) => {
                  setReleaseId(event.target.value);
                  setActivityId('');
                }}
                value={releaseId}
              >
                <option value="">Entrega institucional sin release</option>
                {releaseOptions.map((release) => (
                  <option key={release.id} value={release.id}>
                    {release.courseTitle} · release {release.number}
                  </option>
                ))}
              </select>
              {releaseId ? (
                <>
                  <Label htmlFor="delivery-activity">
                    Actividad evaluativa del grupo
                  </Label>
                  <select
                    className="academic-control"
                    id="delivery-activity"
                    onChange={(event) => setActivityId(event.target.value)}
                    value={activityId}
                  >
                    <option value="">Selecciona la actividad curricular</option>
                    {eligibleActivities.map((activity) => (
                      <option key={activity.id} value={activity.id}>
                        {activity.course_group_name} ·{' '}
                        {activity.module_position}.{activity.position}{' '}
                        {activity.title}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs leading-5 text-muted-foreground">
                    Esta relación permite que la nota actualice el progreso y la
                    aprobación del curso correcto.
                  </p>
                </>
              ) : null}
              <Label htmlFor="delivery-opens">Apertura (opcional)</Label>
              <Input
                id="delivery-opens"
                onChange={(event) => setOpensAt(event.target.value)}
                type="datetime-local"
                value={opensAt}
              />
              <Label htmlFor="delivery-closes">Cierre (opcional)</Label>
              <Input
                id="delivery-closes"
                onChange={(event) => setClosesAt(event.target.value)}
                type="datetime-local"
                value={closesAt}
              />
              <Button
                className="w-full"
                disabled={
                  !name.trim() ||
                  !versionId ||
                  (Boolean(releaseId) && !activityId) ||
                  create.isPending
                }
                onClick={async () => {
                  try {
                    await create.mutateAsync(undefined);
                    setName('');
                    setVersionId('');
                    setReleaseId('');
                    setActivityId('');
                    setOpensAt('');
                    setClosesAt('');
                    router.refresh();
                  } catch {
                    // React Query conserva el error dentro del constructor.
                  }
                }}
                type="button"
              >
                <Rocket data-icon="inline-start" /> Crear borrador de entrega
              </Button>
              <MutationError error={create.error} />
              <div className="assessment-assurance assessment-assurance--light">
                <CheckCircle2 />
                <p>
                  Primero se crea como borrador. La activación y la asignación
                  son decisiones explícitas separadas.
                </p>
              </div>
            </div>
          </section>
        ) : null}
        <section className="assessment-delivery-pipeline">
          <header>
            <div>
              <p className="assessment-rail-kicker">Pipeline operativo</p>
              <h2>Entregas configuradas</h2>
            </div>
            <span>{deliveries.count} registros</span>
          </header>
          <ul>
            {deliveries.results.map((delivery) => (
              <li key={delivery.id}>
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="assessment-resource-card__code">
                      Versión fijada ·{' '}
                      {delivery.assessment_version_id.slice(0, 8)}
                    </p>
                    <h3 className="font-semibold">{delivery.name}</h3>
                    <p className="text-sm text-muted-foreground">
                      {delivery.assessment_title}
                    </p>
                  </div>
                  <Badge
                    className="assessment-status"
                    data-status={delivery.status}
                    variant="outline"
                  >
                    {deliveryStatusLabel(delivery.status)}
                  </Badge>
                </div>
                <dl className="assessment-delivery-window">
                  <div>
                    <CalendarClock />
                    <dt>Apertura</dt>
                    <dd>{formatDate(delivery.opens_at)}</dd>
                  </div>
                  <div>
                    <Clock3 />
                    <dt>Cierre</dt>
                    <dd>{formatDate(delivery.closes_at)}</dd>
                  </div>
                </dl>
                <div className="assessment-delivery-actions">
                  {canManage && delivery.status !== 'withdrawn' ? (
                    <AssignmentControl
                      deliveryId={delivery.id}
                      enrollments={enrollments}
                      slug={slug}
                    />
                  ) : null}
                  <div className="assessment-delivery-actions__secondary">
                    {canManage && delivery.status === 'draft' ? (
                      <ActivateButton
                        deliveryId={delivery.id}
                        lockVersion={delivery.lock_version}
                        slug={slug}
                      />
                    ) : null}
                    {canManage && delivery.status !== 'withdrawn' ? (
                      <WithdrawButton
                        deliveryId={delivery.id}
                        lockVersion={delivery.lock_version}
                        slug={slug}
                      />
                    ) : null}
                    {canViewResults ? (
                      <Button asChild type="button" variant="ghost">
                        <Link
                          href={`/organizaciones/${slug}/evaluaciones/resultados?delivery=${delivery.id}`}
                        >
                          Ver intentos y resultados{' '}
                          <ArrowRight data-icon="inline-end" />
                        </Link>
                      </Button>
                    ) : null}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </>
  );
}

function ActivateButton({
  deliveryId,
  lockVersion,
  slug,
}: Readonly<{ deliveryId: string; lockVersion: number; slug: string }>) {
  const router = useRouter();
  const mutation = useAssessmentMutation(() =>
    activateAssessmentDelivery(slug, deliveryId, lockVersion),
  );
  return (
    <div>
      <Button
        disabled={mutation.isPending}
        onClick={async () => {
          try {
            await mutation.mutateAsync(undefined);
            router.refresh();
          } catch {
            // El error queda disponible en la mutación.
          }
        }}
        type="button"
        variant="outline"
      >
        Activar
      </Button>
      <MutationError error={mutation.error} />
    </div>
  );
}

function AssignmentControl({
  deliveryId,
  enrollments,
  slug,
}: Readonly<{
  deliveryId: string;
  enrollments: EnrollmentOption[];
  slug: string;
}>) {
  const router = useRouter();
  const [assignmentId, setAssignmentId] = useState('');
  const [cohortId, setCohortId] = useState('');
  const mutation = useAssessmentMutation(() =>
    assignAssessmentDelivery(slug, deliveryId, assignmentId),
  );
  const cohortMutation = useAssessmentMutation(() =>
    assignAssessmentCohort(slug, deliveryId, cohortId),
  );
  const available = enrollments.filter(
    (enrollment) => enrollment.current_release_assignment_id,
  );
  const cohorts = Array.from(
    new Map(
      available
        .filter((enrollment) => enrollment.cohort_id)
        .map((enrollment) => [
          enrollment.cohort_id as string,
          enrollment.cohort_name ?? 'Sección',
        ]),
    ),
  );
  return (
    <div className="assessment-assignment-grid">
      <div className="flex min-w-0 gap-2">
        <Label className="sr-only" htmlFor={`assignment-${deliveryId}`}>
          Matrícula con release vigente
        </Label>
        <select
          className="h-9 min-w-0 flex-1 border bg-background px-3 text-sm"
          id={`assignment-${deliveryId}`}
          onChange={(event) => setAssignmentId(event.target.value)}
          value={assignmentId}
        >
          <option value="">Asignar a estudiante</option>
          {available.map((enrollment) => (
            <option
              key={enrollment.current_release_assignment_id}
              value={enrollment.current_release_assignment_id ?? ''}
            >
              {enrollment.student_email} · {enrollment.course_title} r
              {enrollment.release_number}
            </option>
          ))}
        </select>
        <Button
          disabled={!assignmentId || mutation.isPending}
          onClick={async () => {
            try {
              await mutation.mutateAsync(undefined);
              router.refresh();
            } catch {
              // El error queda disponible en la mutación.
            }
          }}
          type="button"
        >
          Asignar
        </Button>
      </div>
      <div className="flex min-w-0 gap-2">
        <Label className="sr-only" htmlFor={`cohort-${deliveryId}`}>
          Sección con matrículas vigentes
        </Label>
        <select
          className="h-9 min-w-0 flex-1 border bg-background px-3 text-sm"
          id={`cohort-${deliveryId}`}
          onChange={(event) => setCohortId(event.target.value)}
          value={cohortId}
        >
          <option value="">Asignar sección</option>
          {cohorts.map(([id, name]) => (
            <option key={id} value={id}>
              {name}
            </option>
          ))}
        </select>
        <Button
          disabled={!cohortId || cohortMutation.isPending}
          onClick={async () => {
            try {
              await cohortMutation.mutateAsync(undefined);
              router.refresh();
            } catch {
              // El error queda disponible en la mutación.
            }
          }}
          type="button"
          variant="outline"
        >
          Asignar sección
        </Button>
      </div>
      <div className="md:col-span-2">
        <MutationError error={mutation.error ?? cohortMutation.error} />
      </div>
    </div>
  );
}

function WithdrawButton({
  deliveryId,
  lockVersion,
  slug,
}: Readonly<{ deliveryId: string; lockVersion: number; slug: string }>) {
  const router = useRouter();
  const [note, setNote] = useState('');
  const mutation = useAssessmentMutation(() =>
    withdrawAssessmentDelivery(slug, deliveryId, lockVersion, note),
  );
  return (
    <details className="assessment-withdraw-control">
      <summary className="cursor-pointer text-sm font-medium text-destructive">
        Retirar entrega
      </summary>
      <div className="mt-2 flex gap-2">
        <Label className="sr-only" htmlFor={`withdraw-${deliveryId}`}>
          Justificación del retiro
        </Label>
        <Input
          id={`withdraw-${deliveryId}`}
          onChange={(event) => setNote(event.target.value)}
          placeholder="Justificación obligatoria"
          value={note}
        />
        <Button
          disabled={!note.trim() || mutation.isPending}
          onClick={async () => {
            try {
              await mutation.mutateAsync(undefined);
              router.refresh();
            } catch {
              // El error queda disponible en la mutación.
            }
          }}
          type="button"
          variant="destructive"
        >
          Confirmar retiro
        </Button>
      </div>
      <MutationError error={mutation.error} />
    </details>
  );
}

function deliveryStatusLabel(status: string) {
  const labels: Record<string, string> = {
    active: 'Activa',
    draft: 'Borrador',
    withdrawn: 'Retirada',
  };
  return labels[status] ?? status;
}

function formatDate(value: string | null) {
  return value
    ? new Intl.DateTimeFormat('es-CO', {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(new Date(value))
    : 'Sin límite';
}
