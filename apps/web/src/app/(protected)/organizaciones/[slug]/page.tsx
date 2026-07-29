import Link from 'next/link';

import { OrganizationNameForm } from '@/components/organizations/organization-name-form';
import {
  hasCapability,
  capabilityLabel,
  roleLabel,
  sortRoles,
} from '@/lib/organizations/labels';
import { getOrganizationForPage } from '@/lib/organizations/server';

export default async function OrganizationDetailPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const { access, organization } = await getOrganizationForPage(slug);
  const canViewMembers = hasCapability(access.capabilities, 'membership.view');
  const canUpdate = hasCapability(access.capabilities, 'organization.update');
  return (
    <main className="mx-auto min-h-screen max-w-4xl px-6 py-12">
      <p className="text-sm font-medium text-slate-600">Organización</p>
      <h1 className="mt-2 text-3xl font-semibold text-slate-950">
        {organization.name}
      </h1>
      <section
        aria-labelledby="my-roles"
        className="mt-8 rounded-xl border border-slate-200 bg-white p-6"
      >
        <h2 className="text-xl font-semibold text-slate-950" id="my-roles">
          Mis roles
        </h2>
        <p className="mt-2 text-slate-700">
          {sortRoles(access.roles).map(roleLabel).join(', ')}
        </p>
      </section>
      <section
        aria-labelledby="my-capabilities"
        className="mt-6 rounded-xl border border-slate-200 bg-white p-6"
      >
        <h2
          className="text-xl font-semibold text-slate-950"
          id="my-capabilities"
        >
          Acciones disponibles
        </h2>
        <ul className="mt-3 list-disc space-y-1 pl-5 text-slate-700">
          {access.capabilities.map((capability) => (
            <li key={capability}>{capabilityLabel(capability)}</li>
          ))}
        </ul>
      </section>
      {canViewMembers ? (
        <Link
          className="mt-6 inline-block rounded-lg bg-slate-900 px-4 py-2 font-medium text-white"
          href={`/organizaciones/${slug}/miembros`}
        >
          Gestionar miembros
        </Link>
      ) : null}
      {canUpdate ? (
        <OrganizationNameForm name={organization.name} slug={slug} />
      ) : null}
    </main>
  );
}
