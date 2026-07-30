import { ArrowRight, BookOpenCheck, Building2, LibraryBig } from 'lucide-react';
import Link from 'next/link';

import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getServerAuthSession } from '@/lib/auth/server-session';
import { roleLabel, sortRoles } from '@/lib/organizations/labels';
import { getAccessContext } from '@/lib/organizations/server';

export default async function StudyPage() {
  const [session, context] = await Promise.all([
    getServerAuthSession(),
    getAccessContext(),
  ]);
  if (!session) return null;

  return (
    <main className="academic-page">
      <PageHeader
        description="Accesos académicos disponibles según tu membresía."
        eyebrow="Inicio académico"
        title="Espacio de trabajo"
      />

      {context.organizations.length ? (
        <section className="mt-6" aria-labelledby="institutional-spaces">
          <div className="flex items-end justify-between gap-4">
            <div>
              <h2
                className="text-base font-semibold tracking-tight"
                id="institutional-spaces"
              >
                {context.organizations.length === 1
                  ? 'Espacio institucional'
                  : 'Espacios institucionales'}
              </h2>
            </div>
          </div>
          <div className="mt-3 overflow-hidden rounded-md border bg-card shadow-[0_1px_2px_rgb(0_0_0_/_0.025)]">
            <div className="hidden grid-cols-[minmax(16rem,1fr)_minmax(12rem,0.7fr)_minmax(15rem,1fr)_3rem] gap-4 border-b bg-muted/30 px-5 py-2.5 text-[0.6875rem] font-semibold tracking-wider text-muted-foreground uppercase lg:grid">
              <span>Institución</span>
              <span>Responsabilidad</span>
              <span>Espacios disponibles</span>
              <span className="sr-only">Abrir</span>
            </div>
            <ul className="divide-y">
              {context.organizations.map((organization) => {
                const canViewCatalog =
                  organization.capabilities.includes('catalog.view');
                const canViewCourses =
                  organization.capabilities.includes('course.authoring.view') ||
                  organization.capabilities.includes('course.approved.view');
                return (
                  <li
                    className="grid gap-4 px-5 py-3.5 transition-colors hover:bg-muted/25 lg:grid-cols-[minmax(16rem,1fr)_minmax(12rem,0.7fr)_minmax(15rem,1fr)_3rem] lg:items-center"
                    key={organization.id}
                  >
                    <div className="flex min-w-0 items-center gap-3">
                      <span className="grid size-9 shrink-0 place-items-center rounded-md bg-primary/10 text-primary">
                        <Building2 className="size-4" />
                      </span>
                      <div className="min-w-0">
                        <Link
                          className="truncate text-sm font-semibold underline-offset-4 hover:text-primary hover:underline"
                          href={`/organizaciones/${organization.slug}`}
                        >
                          {organization.name}
                        </Link>
                      </div>
                    </div>
                    <p className="text-sm">
                      {sortRoles(organization.roles).map(roleLabel).join(', ')}
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {canViewCatalog ? (
                        <Badge asChild className="rounded" variant="outline">
                          <Link
                            href={`/organizaciones/${organization.slug}/curriculo`}
                          >
                            <LibraryBig data-icon="inline-start" />
                            Currículo
                          </Link>
                        </Badge>
                      ) : null}
                      {canViewCourses ? (
                        <Badge asChild className="rounded" variant="outline">
                          <Link
                            href={`/organizaciones/${organization.slug}/cursos`}
                          >
                            <BookOpenCheck data-icon="inline-start" />
                            Cursos
                          </Link>
                        </Badge>
                      ) : null}
                    </div>
                    <Button
                      asChild
                      aria-label={`Abrir ${organization.name}`}
                      size="icon-sm"
                      variant="ghost"
                    >
                      <Link href={`/organizaciones/${organization.slug}`}>
                        <ArrowRight />
                      </Link>
                    </Button>
                  </li>
                );
              })}
            </ul>
          </div>
        </section>
      ) : (
        <section className="academic-panel mt-8 flex flex-col items-start gap-5 p-7 sm:flex-row sm:items-center">
          <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-muted text-muted-foreground">
            <Building2 className="size-5" />
          </span>
          <div>
            <h2 className="font-semibold">Sin organización asignada</h2>
            <p className="mt-1 text-sm leading-6 text-muted-foreground">
              Tu cuenta está activa, pero todavía no tiene un contexto
              institucional.
            </p>
          </div>
        </section>
      )}
    </main>
  );
}
