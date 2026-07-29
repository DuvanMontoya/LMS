import { LogoutButton } from '@/components/auth/logout-button';
import { getServerAuthSession } from '@/lib/auth/server-session';

export default async function StudyPage() {
  const session = await getServerAuthSession();
  if (!session) return null;
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
        <p className="mt-2 text-slate-600">
          El espacio académico está preparado.
        </p>
        <div className="mt-8">
          <LogoutButton />
        </div>
      </section>
    </main>
  );
}
