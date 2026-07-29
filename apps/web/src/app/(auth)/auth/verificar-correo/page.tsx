import type { Metadata } from 'next';

import { AuthShell } from '@/components/auth/auth-shell';
import { VerifyEmailForm } from '@/components/auth/auth-forms';

export const metadata: Metadata = {
  title: 'Verificar correo',
  description: 'Confirma el código enviado a tu correo.',
};

export default function VerifyEmailPage() {
  return (
    <AuthShell
      title="Verifica tu correo"
      description="Ingresa el código que enviamos. No compartas este código con nadie."
    >
      <VerifyEmailForm />
    </AuthShell>
  );
}
