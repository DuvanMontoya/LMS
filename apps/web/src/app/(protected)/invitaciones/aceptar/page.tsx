import { InvitationAcceptance } from '@/components/auth/invitation-acceptance';

export default function InvitationAcceptancePage() {
  return (
    <main
      className="mx-auto w-full max-w-xl px-5 py-12"
      id="contenido-principal"
    >
      <h1 className="text-2xl font-semibold">Aceptar invitación</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Estamos verificando tu invitación y creando tu acceso institucional.
      </p>
      <div className="mt-6">
        <InvitationAcceptance />
      </div>
    </main>
  );
}
