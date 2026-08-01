import { PageHeader } from '@/components/platform/page-header';
import { LiveSessionList } from '@/components/scheduling/live-session-list';
import { getLiveSessions } from '@/lib/scheduling/server';

export default async function LiveSessionsPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ periodo?: string }>;
}>) {
  const [{ slug }, query] = await Promise.all([params, searchParams]);
  const scope = query.periodo === 'anteriores' ? 'past' : 'upcoming';
  const data = await getLiveSessions(slug, { scope });
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Clases en vivo' },
        ]}
        description="Consulta tus clases de curso y sesiones independientes desde un solo lugar."
        eyebrow="Aprendizaje sincrónico"
        title="Clases en vivo"
      />
      <nav aria-label="Periodo de clases" className="mb-5 flex gap-2">
        <a
          className={scope === 'upcoming' ? 'font-semibold' : ''}
          href={`/organizaciones/${slug}/clases`}
        >
          Próximas
        </a>
        <span aria-hidden="true">·</span>
        <a
          className={scope === 'past' ? 'font-semibold' : ''}
          href={`/organizaciones/${slug}/clases?periodo=anteriores`}
        >
          Anteriores
        </a>
      </nav>
      <LiveSessionList sessions={data.sessions} slug={slug} />
    </main>
  );
}
