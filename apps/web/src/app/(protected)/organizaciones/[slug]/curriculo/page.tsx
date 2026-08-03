import { notFound } from 'next/navigation';

import { CurriculumCreateActions } from '@/components/catalog/curriculum-create-actions';
import { CurriculumExplorer } from '@/components/catalog/curriculum-explorer';
import { CurriculumWorkspaceNav } from '@/components/catalog/curriculum-workspace-nav';
import { PageHeader } from '@/components/platform/page-header';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

async function payload<T>(request: Promise<{ response: Response; data?: T }>) {
  const { data } = await request;
  return data ?? ([] as T);
}

export default async function CurriculumPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, organization } = await getOrganizationForPage(slug);
  if (!access.capabilities.includes('catalog.view')) notFound();
  const client = await createPlatformServerClient();
  const [areas, disciplines, subjects] = await Promise.all([
    payload(
      client.GET('/api/v1/organizations/{slug}/catalog/areas/', {
        params: { path: { slug } },
      }),
    ),
    payload(
      client.GET('/api/v1/organizations/{slug}/catalog/disciplines/', {
        params: { path: { slug } },
      }),
    ),
    payload(
      client.GET('/api/v1/organizations/{slug}/catalog/subjects/', {
        params: { path: { slug } },
      }),
    ),
  ]);
  const canManage = access.capabilities.includes('catalog.manage');
  return (
    <main className="academic-page curriculum-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { label: 'Currículo' },
        ]}
        description="Diseña la estructura de conocimiento de la institución y conecta cada área con sus disciplinas y asignaturas."
        eyebrow="Currículo institucional"
        title="Currículo"
      />
      <CurriculumWorkspaceNav current="" slug={slug} />
      <div className="mt-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">Mapa curricular</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Explora la jerarquía y selecciona un elemento para ver su contexto.
          </p>
        </div>
        {canManage ? (
          <CurriculumCreateActions
            areas={areas}
            disciplines={disciplines}
            slug={slug}
          />
        ) : null}
      </div>
      <div className="mt-3">
        {areas.length === 0 ? (
          <div className="rounded-lg border border-dashed p-10 text-center">
            <p className="font-medium">Aún no hay estructura curricular.</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Crea la primera área institucional para comenzar.
            </p>
          </div>
        ) : (
          <CurriculumExplorer
            areas={areas}
            canManage={canManage}
            disciplines={disciplines}
            slug={slug}
            subjects={subjects}
          />
        )}
      </div>
    </main>
  );
}
