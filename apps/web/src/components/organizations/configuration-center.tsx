'use client';

import { LoaderCircle, Save, Settings2 } from 'lucide-react';
import Link from 'next/link';
import { useState } from 'react';

import { IntegrationCenter } from '@/components/organizations/integration-center';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { components } from '@/lib/api/generated/platform';
import { useUpdateMembershipSettings } from '@/lib/organizations/hooks';

type MembershipSettings =
  components['schemas']['OrganizationMembershipSettings'];
type Connection = components['schemas']['IntegrationConnection'];
type DefaultRole =
  'administrator' | 'author' | 'reviewer' | 'instructor' | 'learner';

function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'No fue posible guardar los cambios.';
}

export function ConfigurationCenter({
  integrations,
  settings,
  slug,
}: Readonly<{
  integrations: readonly Connection[];
  settings: MembershipSettings;
  slug: string;
}>) {
  const updateSettings = useUpdateMembershipSettings(slug);
  const [publicJoin, setPublicJoin] = useState(
    Boolean(settings.public_join_enabled),
  );
  const [approval, setApproval] = useState(
    Boolean(settings.join_requires_approval),
  );
  const [domains, setDomains] = useState(
    Array.isArray(settings.allowed_email_domains)
      ? settings.allowed_email_domains.join(', ')
      : '',
  );
  const [expiry, setExpiry] = useState(
    String(settings.invitation_expiry_hours ?? 168),
  );
  const [managedAccounts, setManagedAccounts] = useState(
    Boolean(settings.allow_admin_managed_accounts),
  );
  const [bulkInvitations, setBulkInvitations] = useState(
    Boolean(settings.allow_bulk_invitations),
  );
  const [defaultRole, setDefaultRole] = useState<DefaultRole>(
    (settings.default_role as DefaultRole) ?? 'learner',
  );
  const [lockVersion, setLockVersion] = useState(settings.lock_version);
  const [success, setSuccess] = useState('');

  async function saveMembershipSettings(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();
    setSuccess('');
    const updated = await updateSettings.mutateAsync({
      expected_version: lockVersion,
      public_join_enabled: publicJoin,
      join_requires_approval: approval,
      allowed_email_domains: domains
        .split(',')
        .map((domain) => domain.trim().toLowerCase())
        .filter(Boolean),
      default_role: defaultRole,
      invitation_expiry_hours: Number(expiry),
      allow_admin_managed_accounts: managedAccounts,
      allow_bulk_invitations: bulkInvitations,
    });
    setLockVersion(updated.lock_version);
    setSuccess('Las reglas de incorporación fueron actualizadas.');
  }

  return (
    <div className="space-y-8">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Settings2 className="size-4 text-primary" />
            Incorporación y membresías
          </CardTitle>
          <CardDescription>
            Estas reglas se aplican en el servidor antes de crear acceso. Para
            registrar una persona y darle seguimiento, usa el área de Miembros.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-5"
            onSubmit={(event) => void saveMembershipSettings(event)}
          >
            <fieldset className="space-y-3">
              <legend className="text-sm font-medium">Ingreso público</legend>
              <label className="flex items-start gap-3 rounded-lg border p-3 text-sm">
                <input
                  checked={publicJoin}
                  className="mt-0.5 size-4 accent-primary"
                  onChange={(event) => setPublicJoin(event.target.checked)}
                  type="checkbox"
                />
                <span>
                  <span className="block font-medium">
                    Permitir solicitudes públicas
                  </span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    La persona debe verificar su correo antes de que aparezca
                    una solicitud revisable.
                  </span>
                </span>
              </label>
              <label className="flex items-start gap-3 rounded-lg border p-3 text-sm">
                <input
                  checked={approval}
                  className="mt-0.5 size-4 accent-primary"
                  disabled={!publicJoin}
                  onChange={(event) => setApproval(event.target.checked)}
                  type="checkbox"
                />
                <span>
                  <span className="block font-medium">Requerir aprobación</span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    Si se desactiva, la incorporación asigna el rol
                    predeterminado después de verificar el correo.
                  </span>
                </span>
              </label>
            </fieldset>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div className="space-y-2">
                <Label htmlFor="allowed-domains">Dominios permitidos</Label>
                <Input
                  id="allowed-domains"
                  onChange={(event) => setDomains(event.target.value)}
                  placeholder="institucion.edu, colegio.edu"
                  value={domains}
                />
                <p className="text-xs text-muted-foreground">
                  Vacío: cualquier dominio.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-expiry">Expiración (horas)</Label>
                <Input
                  id="invite-expiry"
                  max="720"
                  min="1"
                  onChange={(event) => setExpiry(event.target.value)}
                  type="number"
                  value={expiry}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="default-role">Rol predeterminado</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
                  id="default-role"
                  onChange={(event) =>
                    setDefaultRole(event.target.value as DefaultRole)
                  }
                  value={defaultRole}
                >
                  <option value="learner">Estudiante</option>
                  <option value="instructor">Docente</option>
                  <option value="author">Autor</option>
                  <option value="reviewer">Revisor</option>
                  <option value="administrator">Administrador</option>
                </select>
              </div>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="flex items-start gap-3 rounded-lg border p-3 text-sm">
                <input
                  checked={managedAccounts}
                  className="mt-0.5 size-4 accent-primary"
                  onChange={(event) => setManagedAccounts(event.target.checked)}
                  type="checkbox"
                />
                <span>
                  <span className="block font-medium">
                    Permitir cuentas administradas
                  </span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    Crea una cuenta inactiva y deja que la persona establezca su
                    contraseña con su enlace de activación.
                  </span>
                </span>
              </label>
              <label className="flex items-start gap-3 rounded-lg border p-3 text-sm">
                <input
                  checked={bulkInvitations}
                  className="mt-0.5 size-4 accent-primary"
                  onChange={(event) => setBulkInvitations(event.target.checked)}
                  type="checkbox"
                />
                <span>
                  <span className="block font-medium">
                    Permitir CSV de invitaciones
                  </span>
                  <span className="mt-1 block text-xs text-muted-foreground">
                    Máximo 500 filas, vista previa obligatoria y ningún acceso
                    previo a la aceptación.
                  </span>
                </span>
              </label>
            </div>
            {updateSettings.error ? (
              <Alert variant="destructive">
                <AlertTitle>No se guardó la configuración</AlertTitle>
                <AlertDescription>
                  {errorMessage(updateSettings.error)}
                </AlertDescription>
              </Alert>
            ) : null}
            {success ? (
              <Alert className="border-emerald-600/20 bg-emerald-500/5">
                <AlertTitle>Configuración actualizada</AlertTitle>
                <AlertDescription>{success}</AlertDescription>
              </Alert>
            ) : null}
            <Button disabled={updateSettings.isPending} type="submit">
              {updateSettings.isPending ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <Save />
              )}
              Guardar reglas de incorporación
            </Button>
          </form>
        </CardContent>
      </Card>

      {publicJoin ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Ingreso público</CardTitle>
            <CardDescription>
              Comparte esta ruta sólo cuando la política institucional esté
              habilitada. Las solicitudes no conceden una membresía activa por
              sí mismas.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link
              className="text-sm font-medium text-primary underline underline-offset-4"
              href={`/unirse/${slug}`}
              target="_blank"
            >
              Abrir enlace público de ingreso
            </Link>
          </CardContent>
        </Card>
      ) : null}

      <IntegrationCenter connections={integrations} slug={slug} />
    </div>
  );
}
