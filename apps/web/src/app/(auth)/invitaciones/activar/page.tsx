import { AuthShell } from '@/components/auth/auth-shell';
import { InvitationActivation } from '@/components/auth/invitation-activation';

export default async function InvitationActivationPage({
  searchParams,
}: Readonly<{ searchParams: Promise<{ token?: string }> }>) {
  const { token } = await searchParams;
  return (
    <AuthShell
      description="La invitación se valida en el servidor y no se volverá a exponer después de continuar."
      title="Activar invitación"
    >
      {token ? (
        <InvitationActivation token={token} />
      ) : (
        <p className="rounded-lg border border-destructive/30 p-4 text-sm text-destructive">
          Falta el enlace de invitación.
        </p>
      )}
    </AuthShell>
  );
}
