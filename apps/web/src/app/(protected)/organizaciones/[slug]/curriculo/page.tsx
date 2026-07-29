import Link from 'next/link';

import { AreaForm } from '@/components/catalog/area-form';
import { CurriculumExplorer } from '@/components/catalog/curriculum-explorer';
import { StructureForms } from '@/components/catalog/structure-forms';
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
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-12">
      <p className="text-sm font-medium text-slate-600">{organization.name}</p>
      <div className="mt-2 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold text-slate-950">Currículo</h1>
          <p className="mt-2 text-slate-700">
            Taxonomía académica institucional y relaciones de aprendizaje.
          </p>
        </div>
        <nav aria-label="Herramientas de currículo" className="flex gap-3">
          <Link
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium"
            href={`/organizaciones/${slug}/curriculo/conceptos`}
          >
            Conceptos
          </Link>
          <Link
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium"
            href={`/organizaciones/${slug}/curriculo/objetivos`}
          >
            Objetivos
          </Link>
          <Link
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium"
            href={`/organizaciones/${slug}/curriculo/prerrequisitos`}
          >
            Prerrequisitos
          </Link>
        </nav>
      </div>
      <section
        className="mt-8 rounded-xl border border-slate-200 bg-white p-6"
        aria-labelledby="curriculum-structure"
      >
        <h2
          id="curriculum-structure"
          className="text-xl font-semibold text-slate-950"
        >
          Área, disciplina y asignatura
        </h2>
        {areas.length === 0 ? (
          <p className="mt-4 text-slate-600">
            Aún no hay estructura curricular.
          </p>
        ) : (
          <CurriculumExplorer
            areas={areas}
            canManage={canManage}
            disciplines={disciplines}
            slug={slug}
            subjects={subjects}
          />
        )}
      </section>
      {canManage ? (
        <>
          <AreaForm slug={slug} />
          <StructureForms areas={areas} disciplines={disciplines} slug={slug} />
        </>
      ) : (
        <p className="mt-5 text-sm text-slate-600">
          Tu membresía puede consultar únicamente entidades activas.
        </p>
      )}
    </main>
  );
}
