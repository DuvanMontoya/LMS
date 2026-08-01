import { Clock3, UserRound } from 'lucide-react';

import { LiveClassroom } from '@/components/scheduling/live-classroom';
import { PageHeader } from '@/components/platform/page-header';
import { getLiveSession } from '@/lib/scheduling/server';

export default async function LiveClassPage({
  params,
}: Readonly<{ params: Promise<{ sessionId: string; slug: string }> }>) {
  const { sessionId, slug } = await params;
  const data = await getLiveSession(slug, sessionId);
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
    </main>
  );
}
