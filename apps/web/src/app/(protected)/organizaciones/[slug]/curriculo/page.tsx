import Link from 'next/link';

import { CurriculumCreateActions } from '@/components/catalog/curriculum-create-actions';
import { CurriculumExplorer } from '@/components/catalog/curriculum-explorer';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
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
  if (!access.capabilities.includes('catalog.view')) return null;
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
    <main className="academic-page">
      <PageHeader
        actions={
          <nav aria-label="Herramientas de currículo" className="flex gap-2">
            {[
              ['Conceptos', 'conceptos'],
              ['Objetivos', 'objetivos'],
              ['Prerrequisitos', 'prerrequisitos'],
            ].map(([label, route]) => (
              <Button asChild key={route} size="sm" variant="outline">
                <Link href={`/organizaciones/${slug}/curriculo/${route}`}>
                  {label}
                </Link>
              </Button>
            ))}
          </nav>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { label: 'Currículo' },
        ]}
        description="Organiza áreas, disciplinas, asignaturas y sus relaciones de aprendizaje."
        eyebrow="Currículo institucional"
        title="Currículo"
      />
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold">Estructura académica</h2>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Explora la jerarquía y selecciona un elemento para administrarlo.
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
