import { AcademicCalendar } from '@/components/scheduling/academic-calendar';
import { PageHeader } from '@/components/platform/page-header';
import { getSchedulingPage } from '@/lib/scheduling/server';

export default async function CalendarPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getSchedulingPage(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Calendario' },
        ]}
        description="Clases en vivo y actividades académicas visibles según tus matrículas y permisos institucionales."
        eyebrow="Agenda académica"
        title="Calendario"
      />
      <AcademicCalendar
        canCreate={data.canCreate}
        courses={data.courses.map(({ slug: courseSlug, title }) => ({
          slug: courseSlug,
          title,
        }))}
        participantOptions={data.participantOptions.map(
          ({ membership_id: membershipId, display }) => ({
            membershipId,
            display,
          }),
        )}
        slug={slug}
      />
    </main>
  );
}
