'use client';

import { ArrowRight, CircleAlert, LoaderCircle } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

type State = 'idle' | 'pending' | 'ready' | 'submitted' | 'error';

export function PublicJoin({ slug }: Readonly<{ slug: string }>) {
  const [state, setState] = useState<State>('idle');
  const [message, setMessage] = useState('');

  async function begin() {
    setState('pending');
    setMessage('');
    const { data, response } = await platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/join/',
      { params: { path: { slug } } },
    );
    if (response.status === 202) {
      setState('ready');
      return;
    }
    if (response.ok && data) {
      setState('submitted');
      setMessage(
        'Tu solicitud fue registrada. La institución revisará el acceso antes de crear una membresía activa.',
      );
      return;
    }
    setState('error');
    setMessage(
      'La institución no acepta solicitudes públicas o esta cuenta ya tiene acceso.',
    );
  }

  return (
    <section className="mx-auto max-w-xl rounded-xl border bg-card p-6 shadow-sm">
      <h1 className="text-2xl font-semibold">
        Solicitar ingreso institucional
      </h1>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        Crea y verifica una cuenta con tu correo. La institución aplicará su
        política de dominio y, cuando corresponda, aprobará la solicitud antes
        de darte acceso.
      </p>
      {state === 'error' ? (
        <Alert className="mt-5" variant="destructive">
          <CircleAlert />
          <AlertTitle>No se pudo iniciar la solicitud</AlertTitle>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      ) : null}
      {state === 'submitted' ? (
        <Alert className="mt-5 border-emerald-600/20 bg-emerald-500/5">
          <AlertTitle>Solicitud registrada</AlertTitle>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      ) : null}
      <div className="mt-6 flex flex-wrap gap-3">
        {state === 'ready' ? (
          <Button asChild>
            <Link href="/auth/registro">
              Crear y verificar cuenta
              <ArrowRight />
            </Link>
          </Button>
        ) : (
          <Button disabled={state === 'pending'} onClick={() => void begin()}>
            {state === 'pending' ? (
              <LoaderCircle className="animate-spin" />
            ) : null}
            Solicitar acceso
          </Button>
        )}
        <Button asChild variant="outline">
          <Link href="/auth/iniciar-sesion">Ya tengo cuenta</Link>
        </Button>
      </div>
    </section>
  );
}
