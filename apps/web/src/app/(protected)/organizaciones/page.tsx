import { ArrowRight, Building2 } from 'lucide-react';
import Link from 'next/link';
import { redirect } from 'next/navigation';

import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { roleLabel, sortRoles } from '@/lib/organizations/labels';
import { getAccessContext } from '@/lib/organizations/server';

export default async function OrganizationsPage() {
  const context = await getAccessContext();
  if (context.organizations.length === 1) {
    redirect(`/organizaciones/${context.organizations[0]!.slug}`);
  }
  return (
    <main className="academic-page">
      <PageHeader
        description="Contextos institucionales a los que tu membresía permite acceder."
        eyebrow="Gobierno institucional"
        title="Cambiar de organización"
      />
      {context.organizations.length === 0 ? (
        <section className="academic-panel mt-8 p-8">
          <Building2 className="size-7 text-muted-foreground" />
          <h2 className="mt-5 text-lg font-semibold">
            No tienes organizaciones asignadas
          </h2>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
            {context.is_platform_operator
              ? 'Crea la primera institución para iniciar su configuración y delegar la administración institucional.'
              : 'Tu cuenta existe, pero un propietario institucional debe agregarla a una organización.'}
          </p>
          {context.is_platform_operator ? (
            <Button asChild className="mt-5">
              <Link href="/administracion/organizaciones">
                Crear institución
              </Link>
            </Button>
          ) : null}
        </section>
      ) : (
        <ul className="mt-7 divide-y overflow-hidden rounded-lg border bg-card">
          {context.organizations.map((organization) => (
            <li key={organization.id}>
              <Link
                className="group grid gap-4 px-5 py-4 hover:bg-muted/20 sm:grid-cols-[2.5rem_minmax(12rem,1fr)_minmax(10rem,0.7fr)_2rem] sm:items-center"
                href={`/organizaciones/${organization.slug}`}
              >
                <span className="grid size-9 place-items-center rounded-md bg-primary/10 text-primary">
                  <Building2 className="size-4" />
                </span>
                <span className="text-sm font-semibold group-hover:text-primary">
                  {organization.name}
                </span>
                <span className="flex flex-wrap gap-1.5">
                  {sortRoles(organization.roles).map((role) => (
                    <Badge className="rounded" key={role} variant="secondary">
                      {roleLabel(role)}
                    </Badge>
                  ))}
                </span>
                <ArrowRight className="size-4 text-muted-foreground group-hover:text-primary" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
