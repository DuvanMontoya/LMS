import type { Metadata } from 'next';
import { Suspense } from 'react';

import { AuthShell } from '@/components/auth/auth-shell';
import { LoginForm } from '@/components/auth/auth-forms';
import { isSignupAvailable } from '@/lib/auth/registration';

export const metadata: Metadata = {
  title: 'Iniciar sesión',
  description: 'Accede a la plataforma académica.',
};

export default async function LoginPage() {
  const registrationAvailable = await isSignupAvailable();
  return (
    <AuthShell
      title="Iniciar sesión"
      description="Ingresa con tu correo y contraseña."
    >
      <Suspense fallback={<p aria-live="polite">Preparando el formulario…</p>}>
        <LoginForm registrationAvailable={registrationAvailable} />
      </Suspense>
    </AuthShell>
  );
}
