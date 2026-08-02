import type { Metadata } from 'next';
import { notFound } from 'next/navigation';

import { AuthShell } from '@/components/auth/auth-shell';
import { SignUpForm } from '@/components/auth/auth-forms';
import { getInvitationRegistrationContext } from '@/lib/auth/invitation-registration';

export const metadata: Metadata = {
  title: 'Crear cuenta invitada',
  description:
    'Activa un acceso institucional mediante una invitación privada.',
};

export default async function InvitationSignUpPage() {
  const context = await getInvitationRegistrationContext();
  if (!context) notFound();
  return (
    <AuthShell
      title="Crear cuenta institucional"
      description={`Tu invitación para ${context.organizationName} está protegida y vinculada a este correo.`}
    >
      <SignUpForm invitedEmail={context.email} />
    </AuthShell>
  );
}
