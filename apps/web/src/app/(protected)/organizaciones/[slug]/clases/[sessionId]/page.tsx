import { Clock3, UserRound } from 'lucide-react';
import { redirect } from 'next/navigation';

import { LiveClassroom } from '@/components/scheduling/live-classroom';
import { LiveAttendancePanel } from '@/components/scheduling/live-attendance-panel';
import { PageHeader } from '@/components/platform/page-header';
import { getLiveSession } from '@/lib/scheduling/server';

export const dynamic = 'force-dynamic';

export default async function LiveClassPage({
  params,
}: Readonly<{ params: Promise<{ sessionId: string; slug: string }> }>) {
  const { sessionId, slug } = await params;
  const data = await getLiveSession(slug, sessionId);
  const courseSlug =
    data.session.course && typeof data.session.course.slug === 'string'
      ? data.session.course.slug
      : null;
  if (
    data.session.course_group_activity_id &&
    courseSlug &&
    data.access.capabilities.includes('assessment.attempt')
  ) {
    redirect(
      `/organizaciones/${slug}/aprender/${courseSlug}/actividades/${data.session.course_group_activity_id}`,
    );
  }
  return (
    <main className="academic-page live-class-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { href: `/organizaciones/${slug}/calendario`, label: 'Calendario' },
          { label: data.session.title },
        ]}
        description={data.session.description || 'Sesión académica sincrónica.'}
        eyebrow="Clase en vivo"
        title={data.session.title}
      />
      <dl className="live-class-meta">
        <div>
          <UserRound />
          <dt>Profesor</dt>
          <dd>{data.session.hostName}</dd>
        </div>
        <div>
          <Clock3 />
          <dt>Horario</dt>
          <dd>
            {new Intl.DateTimeFormat('es-CO', {
              dateStyle: 'long',
              timeStyle: 'short',
            }).format(new Date(data.session.scheduledStart))}
          </dd>
        </div>
      </dl>
      <LiveClassroom detail={data.session} slug={slug} />
      {data.session.canModerate ? (
        <LiveAttendancePanel
          sessionId={data.session.id}
          sessionStatus={data.session.status}
          slug={slug}
          thresholdMinutes={data.session.attendanceThresholdMinutes}
        />
      ) : null}
    </main>
  );
}
