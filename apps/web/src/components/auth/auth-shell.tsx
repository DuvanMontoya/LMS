import Link from 'next/link';

export function AuthShell({
  title,
  description,
  children,
}: Readonly<{
  title: string;
  description: string;
  children: React.ReactNode;
}>) {
  return (
    <main className="mx-auto flex min-h-screen max-w-xl items-center px-5 py-12">
      <section
        aria-labelledby="auth-title"
        className="w-full rounded-2xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8"
      >
        <Link
          href="/"
          className="text-sm font-semibold text-slate-700 underline-offset-4 hover:underline"
        >
          Plataforma académica
        </Link>
        <h1
          id="auth-title"
          className="mt-6 text-3xl font-semibold tracking-tight text-slate-950"
        >
          {title}
        </h1>
        <p className="mt-3 text-slate-600">{description}</p>
        <div className="mt-8">{children}</div>
      </section>
    </main>
  );
}
