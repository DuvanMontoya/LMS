import { LogoutButton } from '@/components/auth/logout-button';
import { getServerAuthSession } from '@/lib/auth/server-session';
import { getAccessContext } from '@/lib/organizations/server';
import Link from 'next/link';

export default async function StudyPage() {
  const session = await getServerAuthSession();
  if (!session) return null;
  const context = await getAccessContext();
  const onlyOrganization = context.organizations[0];
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl items-center px-6 py-16">
      <section
        aria-labelledby="study-title"
        className="w-full rounded-2xl border border-slate-200 bg-white p-8 shadow-sm"
      >
        <p className="text-sm font-medium text-slate-600">Sesión autenticada</p>
        <h1
          id="study-title"
          className="mt-2 text-3xl font-semibold text-slate-950"
        >
          Espacio de estudio
        </h1>
        <p className="mt-4 text-slate-700">{session.email}</p>
        {context.organizations.length === 0 ? (
          <p className="mt-2 text-slate-600">
            Todavía no perteneces a una organización.
          </p>
        ) : null}
        {context.organizations.length === 1 && onlyOrganization ? (
          <Link
            className="mt-4 inline-block font-medium text-slate-900 underline"
            href={`/organizaciones/${onlyOrganization.slug}`}
          >
            Abrir {onlyOrganization.name}
          </Link>
        ) : null}
        {context.organizations.length > 1 ? (
          <nav aria-label="Organizaciones disponibles" className="mt-4">
            <p className="text-slate-600">Selecciona una organización:</p>
            <ul className="mt-2 list-disc pl-5">
              {context.organizations.map((organization) => (
                <li key={organization.id}>
                  <Link
                    className="underline"
                    href={`/organizaciones/${organization.slug}`}
                  >
                    {organization.name}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
        ) : null}
        <div className="mt-8">
          <LogoutButton />
        </div>
      </section>
    </main>
  );
}
