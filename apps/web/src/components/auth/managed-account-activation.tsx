'use client';

import { LoaderCircle, Save } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

export function ManagedAccountActivation() {
  const router = useRouter();
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [pending, setPending] = useState(false);
  return (
    <form
      className="space-y-4"
      onSubmit={async (event) => {
        event.preventDefault();
        setPending(true);
        setError('');
        const { response } = await platformBrowserClient.POST(
          '/api/v1/public/managed-accounts/activate/',
          { body: { password } },
        );
        setPending(false);
        if (!response.ok) {
          setError(
            'No fue posible activar la cuenta. Solicita un nuevo enlace.',
          );
          return;
        }
        router.replace('/auth/iniciar-sesion');
      }}
    >
      <div className="space-y-2">
        <Label htmlFor="managed-password">Define tu contraseña</Label>
        <Input
          autoComplete="new-password"
          id="managed-password"
          minLength={12}
          onChange={(event) => setPassword(event.target.value)}
          required
          type="password"
          value={password}
        />
        <p className="text-xs text-muted-foreground">
          Usa al menos 12 caracteres.
        </p>
      </div>
      {error ? <p className="text-sm text-destructive">{error}</p> : null}
      <Button disabled={pending} type="submit">
        {pending ? <LoaderCircle className="animate-spin" /> : <Save />}
        Activar cuenta
      </Button>
    </form>
  );
}
