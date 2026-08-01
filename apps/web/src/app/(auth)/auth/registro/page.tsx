import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { AuthShell } from '@/components/auth/auth-shell';
import { SignUpForm } from '@/components/auth/auth-forms';
import { isSignupAvailable } from '@/lib/auth/registration';

export const metadata: Metadata = {
  title: 'Crear cuenta',
  description: 'Regístrate para preparar tu acceso a la plataforma.',
};

export default async function SignUpPage() {
  const available = await isSignupAvailable();
  if (!available) notFound();
  return (
    <AuthShell
      title="Crear cuenta"
      description="Usa un correo al que puedas acceder para verificarlo."
    >
      <SignUpForm />
    </AuthShell>
  );
}
