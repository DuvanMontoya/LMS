import type { Metadata } from 'next';

import { AuthShell } from '@/components/auth/auth-shell';
import { PasswordResetForm } from '@/components/auth/auth-forms';

export const metadata: Metadata = {
  title: 'Restablecer contraseña',
  description: 'Actualiza tu contraseña con el código enviado.',
};

export default function PasswordResetPage() {
  return (
    <AuthShell
      title="Restablecer contraseña"
      description="Ingresa el código recibido y elige una contraseña nueva."
    >
      <PasswordResetForm />
    </AuthShell>
  );
}
