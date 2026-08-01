'use client';

import { LoaderCircle, Save } from 'lucide-react';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { components } from '@/lib/api/generated/platform';
import { useUpdatePlatformRegistrationSettings } from '@/lib/organizations/hooks';

export function PlatformRegistrationForm({
  settings,
}: Readonly<{ settings: components['schemas']['RegistrationSettings'] }>) {
  const update = useUpdatePlatformRegistrationSettings();
  const [signupMode, setSignupMode] = useState(
    settings.signup_mode ?? 'closed',
  );
  const [locale, setLocale] = useState(settings.default_locale ?? 'es');
  const [timezone, setTimezone] = useState(settings.default_timezone ?? 'UTC');
  const [lockVersion, setLockVersion] = useState(settings.lock_version);
  const [success, setSuccess] = useState('');

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSuccess('');
    const updated = await update.mutateAsync({
      expected_version: lockVersion,
      signup_mode: signupMode,
      default_locale: locale,
      default_timezone: timezone,
    });
    setLockVersion(updated.lock_version);
    setSuccess('La política de registro fue actualizada.');
  }

  return (
    <form
      className="space-y-5 rounded-xl border bg-card p-5 shadow-sm"
      onSubmit={(event) => void submit(event)}
    >
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium">Modo de registro</legend>
        <p className="text-xs text-muted-foreground">
          El backend y la pantalla de registro consultan esta política en cada
          solicitud.
        </p>
        <div className="grid gap-2 sm:grid-cols-3">
          {[
            ['closed', 'Cerrado'],
            ['invite_only', 'Sólo invitación'],
            ['open', 'Abierto'],
          ].map(([value, label]) => (
            <label
              className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
              key={value}
            >
              <input
                checked={signupMode === value}
                className="size-4 accent-primary"
                name="signup-mode"
                onChange={() => setSignupMode(value as typeof signupMode)}
                type="radio"
                value={value}
              />
              {label}
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="platform-locale">Locale predeterminado</Label>
          <Input
            id="platform-locale"
            onChange={(event) => setLocale(event.target.value)}
            value={locale}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="platform-timezone">Zona horaria predeterminada</Label>
          <Input
            id="platform-timezone"
            onChange={(event) => setTimezone(event.target.value)}
            value={timezone}
          />
        </div>
      </div>
      {update.error instanceof Error ? (
        <Alert variant="destructive">
          <AlertTitle>No se guardó la política</AlertTitle>
          <AlertDescription>{update.error.message}</AlertDescription>
        </Alert>
      ) : null}
      {success ? (
        <Alert className="border-emerald-600/20 bg-emerald-500/5">
          <AlertTitle>Política actualizada</AlertTitle>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      ) : null}
      <Button disabled={update.isPending} type="submit">
        {update.isPending ? (
          <LoaderCircle className="animate-spin" />
        ) : (
          <Save />
        )}
        Guardar política
      </Button>
    </form>
  );
}
