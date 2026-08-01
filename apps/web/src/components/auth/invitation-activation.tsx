'use client';

import { CircleAlert, LoaderCircle } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

type State = 'loading' | 'ready' | 'error';
type InvitationType = 'existing_user' | 'managed_account' | 'new_user';

export function InvitationActivation({ token }: Readonly<{ token: string }>) {
  const router = useRouter();
  const [state, setState] = useState<State>('loading');
  const [message, setMessage] = useState('');
  const [invitationType, setInvitationType] = useState<InvitationType>();

  useEffect(() => {
    let active = true;
    async function activate() {
      const { data, response } = await platformBrowserClient.POST(
        '/api/v1/public/invitations/activate/',
        { body: { token } },
      );
      if (!active) return;
      if (!response.ok || !data) {
        setState('error');
        setMessage(
          'La invitación no está disponible, expiró o ya fue utilizada.',
        );
        return;
      }
      // The invitation token is a one-use bearer secret. Once the API has
      // exchanged it for server-side state, keep the current UI but remove it
      // from the address bar and browser history before showing any action.
      window.history.replaceState(null, '', '/invitaciones/activar');
      if (data.invitation_type === 'managed_account') {
        router.replace('/invitaciones/activar-cuenta');
        return;
      }
      setInvitationType(data.invitation_type);
      setState('ready');
    }
    void activate();
    return () => {
      active = false;
    };
  }, [router, token]);

  if (state === 'loading') {
    return (
      <div className="flex items-center gap-3 rounded-lg border p-4 text-sm">
        <LoaderCircle className="size-4 animate-spin text-primary" />
        Validando tu invitación de un solo uso…
      </div>
    );
  }
  if (state === 'error') {
    return (
      <div className="rounded-lg border border-destructive/30 p-4 text-sm">
        <p className="flex items-center gap-2 font-medium text-destructive">
          <CircleAlert className="size-4" />
          No fue posible activar la invitación
        </p>
        <p className="mt-2 text-muted-foreground">{message}</p>
      </div>
    );
  }
  return (
    <div className="space-y-4 rounded-lg border p-4 text-sm">
      <div>
        <p className="font-medium">Invitación validada</p>
        <p className="mt-1 text-muted-foreground">
          {invitationType === 'existing_user'
            ? 'Inicia sesión con el correo invitado para aceptar la membresía institucional.'
            : 'Crea tu cuenta con el correo invitado. La membresía se creará sólo después de verificar el correo.'}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {invitationType !== 'existing_user' ? (
          <Button asChild>
            <Link href="/auth/registro">Crear cuenta</Link>
          </Button>
        ) : null}
        <Button
          asChild
          variant={invitationType === 'existing_user' ? 'default' : 'outline'}
        >
          <Link href="/auth/iniciar-sesion?next=/invitaciones/aceptar">
            Iniciar sesión y aceptar
          </Link>
        </Button>
      </div>
    </div>
  );
}
