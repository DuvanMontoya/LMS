import { EnrollmentActions } from '@/components/learning/learning-admin-actions';
import { LearningProgress } from '@/components/learning/learning-progress';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import {
  accessStateLabel,
  dateTimeLabel,
  enrollmentStatusLabel,
} from '@/lib/learning/labels';
import { getEnrollment } from '@/lib/learning/server';

export default async function EnrollmentDetailPage({
  params,
}: Readonly<{ params: Promise<{ enrollmentId: string; slug: string }> }>) {
  const { enrollmentId, slug } = await params;
  const data = await getEnrollment(slug, enrollmentId);
  const item = data.enrollment;
  const canManage = data.access.capabilities.includes(
    'learning.enrollment.manage',
  );
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/aprendizaje/matriculas`,
            label: 'Matrículas',
          },
          { label: item.student_email },
        ]}
        description={`${item.course_title} · release ${item.release_number}`}
        eyebrow="Matrícula"
        title={item.student_email}
      />
      <section className="academic-panel mt-6 grid gap-5 p-5 md:grid-cols-3">
        <div>
          <p className="text-sm text-muted-foreground">Estado</p>
          <Badge
            className="mt-2"
            variant={item.status === 'active' ? 'secondary' : 'outline'}
          >
            {enrollmentStatusLabel(item.status ?? 'active')}
          </Badge>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Acceso efectivo</p>
          <p className="mt-2 font-medium">
            {accessStateLabel(item.access_state)}
          </p>
        </div>
        <div>
          <p className="text-sm text-muted-foreground">Grupo de curso</p>
          <p className="mt-2 font-medium">{item.cohort_name ?? 'Individual'}</p>
        </div>
      </section>
      <section
        className="academic-panel mt-6 p-5"
        aria-label="Progreso de la matrícula"
      >
        <LearningProgress progress={data.progress} />
        <dl className="mt-4 grid gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-muted-foreground">Inicio</dt>
            <dd className="mt-1 font-medium">
              {data.progress.started_at
                ? dateTimeLabel(data.progress.started_at)
                : 'Sin iniciar'}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Última actividad</dt>
            <dd className="mt-1 font-medium">
              {data.progress.last_activity_at
                ? dateTimeLabel(data.progress.last_activity_at)
                : 'Sin actividad'}
            </dd>
          </div>
          <div>
            <dt className="text-muted-foreground">Completado</dt>
            <dd className="mt-1 font-medium">
              {data.progress.completed_at
                ? dateTimeLabel(data.progress.completed_at)
                : 'Pendiente'}
            </dd>
          </div>
        </dl>
      </section>
      {canManage ? (
        <div className="mt-6">
          <EnrollmentActions
            cohortId={item.cohort_id}
            enrollmentId={item.id}
            releaseOptions={
              data.options.courses
                .find((course) => course.slug === item.course_slug)
                ?.releases.filter(
                  (release) => release.number > item.release_number,
                ) ?? []
            }
            slug={slug}
            status={item.status ?? 'active'}
            version={item.enrollment_version}
          />
        </div>
      ) : null}
    </main>
  );
}
