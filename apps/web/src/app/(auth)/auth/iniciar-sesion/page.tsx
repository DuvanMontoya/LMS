import type { Metadata } from 'next';
import { Suspense } from 'react';

import { AuthShell } from '@/components/auth/auth-shell';
import { LoginForm } from '@/components/auth/auth-forms';

export const metadata: Metadata = {
  title: 'Iniciar sesión',
  description: 'Accede a la plataforma académica.',
};

export default function LoginPage() {
  return (
    <AuthShell
      title="Iniciar sesión"
      description="Ingresa con tu correo y contraseña."
    >
      <Suspense fallback={<p aria-live="polite">Preparando el formulario…</p>}>
        <LoginForm />
      </Suspense>
    </AuthShell>
  );
}
