import Link from 'next/link';

import { LoginResearchField } from '@/components/auth/login-research-field';

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
    <main className="research-login">
      <LoginResearchField />
      <section className="research-login__context" aria-hidden="true">
        <p>Conocimiento académico institucional</p>
        <h1>Acceso académico.</h1>
        <span>Currículo, autoría y conocimiento estructurado.</span>
      </section>
      <section className="research-login__panel" aria-labelledby="auth-title">
        <Link className="research-login__brand" href="/">
          <span>Plataforma académica</span>
          <small>Entorno institucional privado</small>
        </Link>
        <div className="research-login__intro">
          <p>Acceso institucional</p>
          <h2 id="auth-title">
            Aula <em>Académica</em>
          </h2>
          {title === 'Iniciar sesión' ? (
            <span className="sr-only">{title}. </span>
          ) : (
            <span className="research-login__screen-title">{title}</span>
          )}
          <span>{description}</span>
        </div>
        <div className="research-login__form">{children}</div>
        <p className="research-login__security">
          Sesión protegida · credenciales privadas · cierre seguro.
        </p>
      </section>
    </main>
  );
}
