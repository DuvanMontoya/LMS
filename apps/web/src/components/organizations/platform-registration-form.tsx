'use client';

import { LockKeyhole, LoaderCircle, Save, UserPlus } from 'lucide-react';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import type { components } from '@/lib/api/generated/platform';
import { useUpdatePlatformRegistrationSettings } from '@/lib/organizations/hooks';

export function PlatformRegistrationForm({
  settings,
}: Readonly<{ settings: components['schemas']['RegistrationSettings'] }>) {
  const update = useUpdatePlatformRegistrationSettings();
  const [signupMode, setSignupMode] = useState<'closed' | 'open'>(
    settings.signup_mode === 'open' ? 'open' : 'closed',
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
    setSuccess(
      updated.signup_mode === 'closed'
        ? 'Alta pública cerrada. Las invitaciones privadas vigentes continúan funcionando únicamente para el correo invitado.'
        : 'Alta pública abierta. El formulario general y las invitaciones privadas están disponibles.',
    );
  }

  return (
    <form
      className="space-y-6 rounded-xl border bg-card p-6 shadow-[0_12px_36px_rgb(41_56_82_/_0.06)]"
      onSubmit={(event) => void submit(event)}
    >
      <fieldset className="space-y-2">
        <legend className="text-base font-semibold">Creación de cuentas</legend>
        <p className="text-xs text-muted-foreground">
          Decide si cualquier persona puede iniciar un alta. Las invitaciones
          institucionales de un solo uso permanecen operativas en ambos modos.
        </p>
        <div className="grid gap-3 sm:grid-cols-2">
          {[
            {
              description:
                'Sólo pueden crear cuenta quienes tengan una invitación válida.',
              icon: LockKeyhole,
              label: 'Alta pública cerrada',
              value: 'closed',
            },
            {
              description:
                'Cualquier persona puede iniciar el registro y verificar su correo.',
              icon: UserPlus,
              label: 'Alta pública abierta',
              value: 'open',
            },
          ].map(({ description, icon: Icon, label, value }) => (
            <label
              className="grid cursor-pointer grid-cols-[1.5rem_minmax(0,1fr)_1rem] gap-3 rounded-lg border p-4 transition-colors has-checked:border-primary has-checked:bg-primary/5"
              key={value}
            >
              <Icon className="mt-0.5 size-5 text-primary" />
              <span>
                <span className="block text-sm font-semibold">{label}</span>
                <span className="mt-1 block text-xs leading-5 text-muted-foreground">
                  {description}
                </span>
              </span>
              <input
                checked={signupMode === value}
                className="mt-0.5 size-4 accent-primary"
                name="signup-mode"
                onChange={() => setSignupMode(value as typeof signupMode)}
                type="radio"
                value={value}
              />
            </label>
          ))}
        </div>
      </fieldset>
      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-2">
          <Label htmlFor="platform-locale">Locale predeterminado</Label>
          <select
            className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            id="platform-locale"
            onChange={(event) => setLocale(event.target.value)}
            value={locale}
          >
            <option value="es">Español</option>
            <option value="es-CO">Español (Colombia)</option>
          </select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="platform-timezone">Zona horaria predeterminada</Label>
          <select
            className="h-9 w-full rounded-md border border-input bg-background px-3 text-sm"
            id="platform-timezone"
            onChange={(event) => setTimezone(event.target.value)}
            value={timezone}
          >
            <option value="America/Bogota">Colombia (Bogotá)</option>
            <option value="UTC">UTC</option>
          </select>
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
