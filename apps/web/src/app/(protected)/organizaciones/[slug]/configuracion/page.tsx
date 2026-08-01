import { ConfigurationCenter } from '@/components/organizations/configuration-center';
import { PageHeader } from '@/components/platform/page-header';
import { getOrganizationConfigurationForPage } from '@/lib/organizations/server';
import Link from 'next/link';

export default async function OrganizationConfigurationPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { integrations, membershipSettings, organization } =
    await getOrganizationConfigurationForPage(slug);
  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: organization.name },
          { label: 'Configuración' },
        ]}
        description="Reglas de incorporación, cuentas administradas y conexiones externas gobernadas por la institución."
        eyebrow="Gobierno institucional"
        title="Configuración"
      />
      <nav
        aria-label="Categorías de configuración"
        className="mt-6 flex flex-wrap gap-2"
      >
        <Link
          className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted"
          href={`/organizaciones/${slug}/configuracion/general`}
        >
          General
        </Link>
        <Link
          className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted"
          href={`/organizaciones/${slug}/configuracion/miembros`}
        >
          Miembros
        </Link>
        <Link
          className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted"
          href={`/organizaciones/${slug}/configuracion/integraciones`}
        >
          Integraciones
        </Link>
      </nav>
      <section className="mt-5 flex flex-wrap items-center justify-between gap-4 rounded-lg border bg-card p-4">
        <div>
          <h2 className="text-sm font-semibold">Gestión de personas</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Registra estudiantes y demás personas, administra sus roles,
            membresías, invitaciones y solicitudes desde un único directorio.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link
            className="rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted"
            href={`/organizaciones/${slug}/miembros`}
          >
            Gestionar personas
          </Link>
          <Link
            className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            href={`/organizaciones/${slug}/miembros/nuevo?rol=learner`}
          >
            Registrar estudiante
          </Link>
        </div>
      </section>
      <div className="mt-6">
        <ConfigurationCenter
          integrations={integrations}
          settings={membershipSettings}
          slug={slug}
        />
      </div>
    </main>
  );
}
