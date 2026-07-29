import Link from 'next/link';

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl items-center px-6 py-16">
      <section aria-labelledby="scaffolding-title">
        <p className="text-sm font-medium text-slate-600">LMS</p>
        <h1 id="scaffolding-title" className="mt-2 text-3xl font-semibold">
          Plataforma académica
        </h1>
        <p className="mt-4 max-w-prose text-slate-700">
          El acceso a la plataforma está preparado. Las funciones académicas se
          incorporarán en fases posteriores.
        </p>
        <Link
          href="/auth/iniciar-sesion"
          className="mt-6 inline-block rounded-lg bg-slate-950 px-4 py-2 font-medium text-white"
        >
          Iniciar sesión
        </Link>
      </section>
    </main>
  );
}
