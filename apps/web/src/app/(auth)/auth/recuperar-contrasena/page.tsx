import type { Metadata } from 'next';

import { AuthShell } from '@/components/auth/auth-shell';
import { PasswordRequestForm } from '@/components/auth/auth-forms';

export const metadata: Metadata = {
  title: 'Recuperar contraseña',
  description: 'Solicita un código para restablecer tu contraseña.',
};

export default function PasswordRequestPage() {
  return (
    <AuthShell
      title="Recuperar contraseña"
      description="Si existe una cuenta asociada, recibirás instrucciones para continuar."
    >
      <PasswordRequestForm />
    </AuthShell>
  );
}
