import {
  ArrowRight,
  BookOpenCheck,
  LibraryBig,
  Settings2,
  Users,
} from 'lucide-react';
import Link from 'next/link';
import { redirect } from 'next/navigation';

import { OrganizationNameForm } from '@/components/organizations/organization-name-form';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import {
  hasCapability,
  roleLabel,
  sortRoles,
} from '@/lib/organizations/labels';
import { getOrganizationForPage } from '@/lib/organizations/server';

export default async function OrganizationDetailPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, context, organization } = await getOrganizationForPage(slug);
  if (access.roles.length === 1 && access.roles[0] === 'learner') {
    redirect(`/organizaciones/${slug}/aprendizaje`);
  }
  const canViewMembers = hasCapability(access.capabilities, 'membership.view');
  const canUpdate = hasCapability(access.capabilities, 'organization.update');
  const destinations = [
    {
      description:
        'Áreas, disciplinas, asignaturas, conceptos, objetivos y prerrequisitos.',
      href: `/organizaciones/${slug}/curriculo`,
      icon: LibraryBig,
      label: 'Currículo institucional',
      visible: hasCapability(access.capabilities, 'catalog.view'),
    },
    {
      description:
        'Estructuras versionadas, alineación, contenido y flujo de revisión.',
      href: `/organizaciones/${slug}/cursos`,
      icon: BookOpenCheck,
      label: 'Cursos',
      visible:
        hasCapability(access.capabilities, 'course.authoring.view') ||
        hasCapability(access.capabilities, 'course.approved.view'),
    },
    {
      description:
        'Membresías, estados, roles institucionales e historial de cambios.',
      href: `/organizaciones/${slug}/miembros`,
      icon: Users,
      label: 'Miembros',
      visible: canViewMembers,
    },
  ].filter((item) => item.visible);

  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[
          context.organizations.length > 1
            ? { href: '/organizaciones', label: 'Organizaciones' }
            : { href: '/estudiar', label: 'Inicio' },
          { label: organization.name },
        ]}
        description="Gobierno, acceso y trabajo académico dentro de este contexto institucional."
        eyebrow="Organización"
        title={organization.name}
      />

      <section className="mt-6 grid gap-7 lg:grid-cols-[minmax(0,1fr)_20rem]">
        <div>
          <h2 className="text-sm font-semibold">Áreas de trabajo</h2>
          <p className="mt-1 text-xs text-muted-foreground">
            Accede a los dominios habilitados por tu membresía.
          </p>
          <ul className="mt-4 divide-y overflow-hidden rounded-lg border bg-card">
            {destinations.map(({ description, href, icon: Icon, label }) => (
              <li key={href}>
                <Link
                  className="group grid grid-cols-[2.25rem_minmax(0,1fr)_2rem] items-center gap-3 px-5 py-4 hover:bg-muted/20"
                  href={href}
                >
                  <span className="grid size-9 place-items-center rounded-md bg-primary/10 text-primary">
                    <Icon className="size-4" />
                  </span>
                  <span className="min-w-0">
                    <span className="block text-sm font-semibold group-hover:text-primary">
                      {label}
                    </span>
                    <span className="mt-1 block text-sm leading-5 text-muted-foreground">
                      {description}
                    </span>
                  </span>
                  <ArrowRight className="size-4 text-muted-foreground group-hover:text-primary" />
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <aside className="border-l pl-6">
          <h2 className="text-sm font-semibold">Tu acceso</h2>
          <p className="text-xs font-semibold tracking-wider text-muted-foreground uppercase">
            Roles
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            {sortRoles(access.roles).map((role) => (
              <Badge className="rounded" key={role}>
                {roleLabel(role)}
              </Badge>
            ))}
          </div>
        </aside>
      </section>

      {canUpdate ? (
        <section className="mt-6 grid gap-5 border-t pt-5 lg:grid-cols-[20rem_minmax(0,1fr)] lg:gap-8">
          <div className="flex items-start gap-3">
            <Settings2 className="size-5 text-primary" />
            <div>
              <h2 className="text-sm font-semibold">
                Configuración institucional
              </h2>
              <p className="mt-1 text-xs text-muted-foreground">
                Identidad visible del espacio.
              </p>
            </div>
          </div>
          <div>
            <OrganizationNameForm name={organization.name} slug={slug} />
          </div>
        </section>
      ) : null}
    </main>
  );
}
