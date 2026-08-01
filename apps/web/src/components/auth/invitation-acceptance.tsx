'use client';

import { CircleAlert, LoaderCircle } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useRef, useState } from 'react';

import { Button } from '@/components/ui/button';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

type State = 'accepting' | 'error';

export function InvitationAcceptance() {
  const [state, setState] = useState<State>('accepting');
  const [message, setMessage] = useState('');
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    let active = true;
    async function accept() {
      const { response } = await platformBrowserClient.POST(
        '/api/v1/public/invitations/accept/',
      );
      if (!active) return;
      if (response.ok) {
        window.location.assign('/organizaciones');
        return;
      }
      setState('error');
      setMessage(
        'La invitación no está disponible para esta cuenta. Abre un enlace vigente con el correo invitado.',
      );
    }
    void accept();
    return () => {
      active = false;
    };
  }, []);

  if (state === 'accepting') {
    return (
      <div className="flex items-center gap-3 rounded-lg border p-4 text-sm">
        <LoaderCircle className="size-4 animate-spin text-primary" />
        Creando tu membresía institucional…
      </div>
    );
  }
  return (
    <div className="space-y-4 rounded-lg border border-destructive/30 p-4 text-sm">
      <p className="flex items-center gap-2 font-medium text-destructive">
        <CircleAlert className="size-4" />
        No se pudo aceptar la invitación
      </p>
      <p className="text-muted-foreground">{message}</p>
      <Button asChild variant="outline">
        <Link href="/organizaciones">Volver a organizaciones</Link>
      </Button>
    </div>
  );
}
