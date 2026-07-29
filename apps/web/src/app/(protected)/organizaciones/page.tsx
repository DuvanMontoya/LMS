import Link from 'next/link';

import { getAccessContext } from '@/lib/organizations/server';
import { roleLabel, sortRoles } from '@/lib/organizations/labels';

export default async function OrganizationsPage() {
  const context = await getAccessContext();
  return (
    <main className="mx-auto min-h-screen max-w-5xl px-6 py-12">
      <p className="text-sm font-medium text-slate-600">
        Contexto institucional
      </p>
      <h1 className="mt-2 text-3xl font-semibold text-slate-950">
        Mis organizaciones
      </h1>
      {context.organizations.length === 0 ? (
        <p className="mt-6 rounded-xl border border-slate-200 bg-white p-6 text-slate-700">
          Todavía no perteneces a una organización.
        </p>
      ) : (
        <ul className="mt-6 grid gap-4 sm:grid-cols-2">
          {context.organizations.map((organization) => (
            <li
              className="rounded-xl border border-slate-200 bg-white p-5"
              key={organization.id}
            >
              <h2 className="text-xl font-semibold text-slate-950">
                {organization.name}
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                {sortRoles(organization.roles).map(roleLabel).join(', ')}
              </p>
              <Link
                className="mt-4 inline-block font-medium text-slate-900 underline"
                href={`/organizaciones/${organization.slug}`}
              >
                Abrir contexto institucional
              </Link>
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
