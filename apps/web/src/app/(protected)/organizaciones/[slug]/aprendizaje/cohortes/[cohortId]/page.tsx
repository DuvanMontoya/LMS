import Link from 'next/link';

import { CohortActions } from '@/components/learning/learning-admin-actions';
import { CohortBatchEnrollForm } from '@/components/learning/learning-admin-forms';
import { CohortRosterSync } from '@/components/learning/cohort-roster-sync';
import { LearningProgress } from '@/components/learning/learning-progress';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  cohortStatusLabel,
  enrollmentStatusLabel,
} from '@/lib/learning/labels';
import { getCohort } from '@/lib/learning/server';

export default async function CohortDetailPage({
  params,
}: Readonly<{ params: Promise<{ cohortId: string; slug: string }> }>) {
  const { cohortId, slug } = await params;
  const data = await getCohort(slug, cohortId);
  const canManage = data.access.capabilities.includes('learning.cohort.manage');
  const academicGroup = data.cohort.academic_group_id
    ? data.options.academicGroups.find(
        (group) => group.id === data.cohort.academic_group_id,
      )
    : undefined;
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          <>
            <Badge
              variant={
                data.cohort.status === 'active' ? 'secondary' : 'outline'
              }
            >
              {cohortStatusLabel(data.cohort.status ?? 'active')}
            </Badge>
            {canManage ? (
              <CohortActions
                cohortId={cohortId}
                slug={slug}
                status={data.cohort.status ?? 'active'}
                version={data.cohort.course_group_version}
              />
            ) : null}
          </>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/aprendizaje/cohortes`,
            label: 'Secciones',
          },
          { label: data.cohort.name },
        ]}
        description={`${data.cohort.course_title} · release ${data.cohort.release_number}`}
        eyebrow="Sección"
        title={data.cohort.name}
      />
      <section
        className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4"
        aria-label="Progreso agregado"
      >
        <Metric
          label="Matrículas"
          value={data.progress.summary.total_enrollments}
        />
        <Metric label="En curso" value={data.progress.summary.in_progress} />
        <Metric label="Completadas" value={data.progress.summary.completed} />
        <Metric
          label="Promedio"
          value={`${data.progress.summary.average_percent}%`}
        />
      </section>
      {canManage && data.cohort.status !== 'archived' ? (
        <CohortBatchEnrollForm
          cohortId={cohortId}
          cohortVersion={data.cohort.course_group_version}
          enrolledEmails={data.progress.results
            .filter((enrollment) => enrollment.status !== 'revoked')
            .map((enrollment) => enrollment.student_email)}
          slug={slug}
        />
      ) : null}
      {canManage &&
      data.cohort.status !== 'archived' &&
      data.cohort.roster_mode === 'synced' &&
      academicGroup ? (
        <CohortRosterSync
          academicGroupName={academicGroup.name}
          academicGroupVersion={academicGroup.lockVersion}
          cohortId={cohortId}
          cohortVersion={data.cohort.course_group_version}
          slug={slug}
        />
      ) : null}
      <div className="mt-6 grid gap-4">
        {data.progress.results.map((enrollment) => (
          <article
            className="academic-panel grid gap-4 p-5 md:grid-cols-[minmax(0,1fr)_minmax(16rem,1fr)_auto] md:items-center"
            key={enrollment.id}
          >
            <div>
              <p className="font-medium">{enrollment.student_email}</p>
              <Badge className="mt-2" variant="outline">
                {enrollmentStatusLabel(enrollment.status ?? 'active')}
              </Badge>
            </div>
            <LearningProgress progress={enrollment.progress} />
            <Button asChild variant="outline">
              <Link
                href={`/organizaciones/${slug}/aprendizaje/matriculas/${enrollment.id}`}
              >
                Ver matrícula
              </Link>
            </Button>
          </article>
        ))}
      </div>
      {!data.progress.results.length ? (
        <p className="academic-panel mt-6 border-dashed p-6 text-center text-sm text-muted-foreground">
          Esta sección todavía no tiene matrículas.
        </p>
      ) : null}
    </main>
  );
}

function Metric({
  label,
  value,
}: Readonly<{ label: string; value: number | string }>) {
  return (
    <div className="academic-panel bg-card p-5">
      <p className="text-sm text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}
