import type { Metadata } from 'next';

import { AuthShell } from '@/components/auth/auth-shell';
import { SignUpForm } from '@/components/auth/auth-forms';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';

export const metadata: Metadata = {
  title: 'Crear cuenta',
  description: 'Regístrate para preparar tu acceso a la plataforma.',
};

export default async function SignUpPage() {
  const client = await createPlatformServerClient();
  const { data, response } = await client.GET(
    '/api/v1/platform/registration-settings/public/',
  );
  const available = response.ok && data?.signup_available === true;
  const inviteOnly = data?.signup_mode === 'invite_only';
  return (
    <AuthShell
      title="Crear cuenta"
      description={
        available
          ? 'Usa un correo al que puedas acceder para verificarlo.'
          : inviteOnly
            ? 'Abre primero una invitación institucional válida para continuar.'
            : 'El registro público está cerrado en este momento.'
      }
    >
      {available ? (
        <SignUpForm />
      ) : (
        <div className="space-y-3 rounded-lg border border-dashed p-5 text-sm">
          <p className="font-medium">
            {inviteOnly
              ? 'El acceso requiere una invitación institucional.'
              : 'El registro público está cerrado.'}
          </p>
          <p className="text-muted-foreground">
            {inviteOnly
              ? 'Si recibiste un enlace de invitación, ábrelo primero para continuar con el registro seguro.'
              : 'La institución debe habilitar el registro antes de crear una cuenta sin invitación.'}
          </p>
        </div>
      )}
    </AuthShell>
  );
}
