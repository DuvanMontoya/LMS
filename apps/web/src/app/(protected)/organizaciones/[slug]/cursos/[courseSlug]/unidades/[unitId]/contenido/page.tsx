import { ContentWorkspace } from '@/components/content/content-workspace';
import { PageHeader } from '@/components/platform/page-header';
import { getUnitContentWorkspace } from '@/lib/content/server';

export default async function UnitContentPage({
  params,
}: Readonly<{
  params: Promise<{ courseSlug: string; slug: string; unitId: string }>;
}>) {
  const { courseSlug, slug, unitId } = await params;
  const data = await getUnitContentWorkspace(slug, courseSlug, unitId);

  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}/cursos`, label: 'Cursos' },
          {
            href: `/organizaciones/${slug}/cursos/${courseSlug}`,
            label: data.revision.title,
          },
          {
            href: `/organizaciones/${slug}/cursos/${courseSlug}/estructura`,
            label: 'Estructura',
          },
          { label: 'Contenido' },
        ]}
        description="Redacta, estructura y revisa el material académico de esta unidad."
        eyebrow={data.courseModule.title}
        title={data.unit.title}
      />
      <ContentWorkspace
        courseSlug={courseSlug}
        current={data.current}
        organizationSlug={slug}
        revisionId={data.revision.id}
        revisionStatus={data.revision.authoring_status}
        unitId={unitId}
        versions={data.versions}
      />
    </main>
  );
}
