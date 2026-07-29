import type { Metadata } from 'next';

import { AuthShell } from '@/components/auth/auth-shell';
import { SignUpForm } from '@/components/auth/auth-forms';

export const metadata: Metadata = {
  title: 'Crear cuenta',
  description: 'Regístrate para preparar tu acceso a la plataforma.',
};

export default function SignUpPage() {
  return (
    <AuthShell
      title="Crear cuenta"
      description="Usa un correo al que puedas acceder para verificarlo."
    >
      <SignUpForm />
    </AuthShell>
  );
}
