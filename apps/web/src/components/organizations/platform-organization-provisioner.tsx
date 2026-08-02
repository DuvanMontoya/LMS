'use client';

import {
  Building2,
  CheckCircle2,
  LoaderCircle,
  MailCheck,
  Plus,
  RefreshCw,
  XCircle,
} from 'lucide-react';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  usePlatformBootstrapInvitations,
  useProvisionPlatformOrganization,
  useResendPlatformBootstrapInvitation,
  useRevokePlatformBootstrapInvitation,
} from '@/lib/organizations/hooks';

type Organization = {
  id: string;
  name: string;
  slug: string;
  status?: 'active' | 'closed' | 'pending_activation' | 'suspended';
};

export function PlatformOrganizationProvisioner({
  organizations,
}: Readonly<{
  organizations: readonly Organization[];
}>) {
  const provision = useProvisionPlatformOrganization();
  const [name, setName] = useState('');
  const [ownerEmail, setOwnerEmail] = useState('');
  const [administratorEmails, setAdministratorEmails] = useState('');
  const [created, setCreated] = useState<Organization | null>(null);
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const [knownOrganizations, setKnownOrganizations] = useState([
    ...organizations,
  ]);
  const activeCount = knownOrganizations.filter(
    (organization) => organization.status === 'active',
  ).length;
  const pendingCount = knownOrganizations.filter(
    (organization) => organization.status === 'pending_activation',
  ).length;

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreated(null);
    try {
      const organization = await provision.mutateAsync({
        name: name.trim(),
        owner_email: ownerEmail.trim(),
        administrator_emails: administratorEmails
          .split(/[,\n]/)
          .map((email) => email.trim())
          .filter(Boolean),
      });
      setCreated(organization);
      setSelectedSlug(organization.slug);
      setKnownOrganizations((current) =>
        [...current, organization].sort((left, right) =>
          left.name.localeCompare(right.name, 'es'),
        ),
      );
      setName('');
      setOwnerEmail('');
      setAdministratorEmails('');
    } catch {
      // The normalized API error is rendered below.
    }
  }

  return (
    <div className="min-w-0 space-y-5">
      <section
        aria-label="Estado de instituciones"
        className="grid overflow-hidden rounded-xl border bg-card shadow-[0_12px_36px_rgb(41_56_82_/_0.06)] sm:grid-cols-3"
      >
        <PlatformMetric
          label="Instituciones"
          value={knownOrganizations.length}
        />
        <PlatformMetric label="Activas" tone="active" value={activeCount} />
        <PlatformMetric
          label="Por activar"
          tone="pending"
          value={pendingCount}
        />
      </section>

      <div className="grid min-w-0 gap-5 xl:grid-cols-[minmax(21rem,0.8fr)_minmax(30rem,1.2fr)] xl:items-start">
        <Card className="min-w-0 shadow-[0_12px_36px_rgb(41_56_82_/_0.06)]">
          <CardHeader>
            <p className="text-[0.6875rem] font-semibold tracking-[0.1em] text-primary uppercase">
              Alta controlada
            </p>
            <CardTitle>Nueva institución</CardTitle>
            <p className="text-sm leading-6 text-muted-foreground">
              Se crea pendiente y sin miembros. La persona propietaria activa el
              espacio desde su invitación; el operador nunca entra al tenant.
            </p>
          </CardHeader>
          <CardContent>
            <form
              className="space-y-5"
              onSubmit={(event) => void submit(event)}
            >
              <div className="space-y-2">
                <Label htmlFor="organization-name">
                  Nombre de la institución
                </Label>
                <Input
                  autoComplete="organization"
                  id="organization-name"
                  maxLength={160}
                  onChange={(event) => setName(event.target.value)}
                  placeholder="Ej. Academia Gauss"
                  required
                  value={name}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="organization-owner-email">
                  Correo de la persona propietaria
                </Label>
                <Input
                  autoComplete="email"
                  id="organization-owner-email"
                  onChange={(event) => setOwnerEmail(event.target.value)}
                  placeholder="responsable@institucion.edu.co"
                  required
                  type="email"
                  value={ownerEmail}
                />
                <p className="text-xs leading-5 text-muted-foreground">
                  Puede ser una cuenta existente o un correo nuevo. La
                  institución permanecerá pendiente hasta que esta invitación de
                  un solo uso sea aceptada.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="organization-administrator-emails">
                  Administradores iniciales opcionales
                </Label>
                <Textarea
                  id="organization-administrator-emails"
                  onChange={(event) =>
                    setAdministratorEmails(event.target.value)
                  }
                  placeholder={
                    'administracion@institucion.edu.co\ncoordinacion@institucion.edu.co'
                  }
                  value={administratorEmails}
                />
                <p className="text-xs leading-5 text-muted-foreground">
                  Un correo por línea, máximo 20. También recibirán
                  invitaciones; no obtienen acceso antes de aceptarlas.
                </p>
              </div>
              {provision.error instanceof Error ? (
                <Alert variant="destructive">
                  <AlertTitle>No se creó la institución</AlertTitle>
                  <AlertDescription>{provision.error.message}</AlertDescription>
                </Alert>
              ) : null}
              {created ? (
                <Alert className="border-emerald-600/20 bg-emerald-500/5">
                  <CheckCircle2 className="text-emerald-700" />
                  <AlertTitle>Institución pendiente de activación</AlertTitle>
                  <AlertDescription>
                    El código institucional generado es{' '}
                    <strong>{created.slug}</strong>. Las invitaciones de
                    bootstrap quedaron registradas; el owner activará la
                    institución al aceptar la suya. El operador no recibió
                    membresía.
                  </AlertDescription>
                </Alert>
              ) : null}
              <Button
                disabled={
                  provision.isPending || !name.trim() || !ownerEmail.trim()
                }
                type="submit"
              >
                {provision.isPending ? (
                  <LoaderCircle className="animate-spin" />
                ) : (
                  <Plus />
                )}
                Crear institución
              </Button>
            </form>
          </CardContent>
        </Card>

        <section className="min-w-0 space-y-5">
          <Card className="shadow-[0_12px_36px_rgb(41_56_82_/_0.06)]">
            <CardHeader>
              <p className="text-[0.6875rem] font-semibold tracking-[0.1em] text-primary uppercase">
                Plano global
              </p>
              <CardTitle>Directorio institucional</CardTitle>
              <p className="text-sm text-muted-foreground">
                Selecciona una institución para gestionar únicamente sus
                invitaciones de activación.
              </p>
            </CardHeader>
            <CardContent>
              {knownOrganizations.length ? (
                <ul className="divide-y overflow-hidden rounded-lg border">
                  {knownOrganizations.map((organization) => (
                    <li key={organization.id}>
                      <button
                        aria-pressed={selectedSlug === organization.slug}
                        className="grid min-h-14 w-full grid-cols-[2.25rem_minmax(0,1fr)_auto] items-center gap-3 px-4 text-left transition-colors hover:bg-muted/40 aria-pressed:bg-primary/5"
                        onClick={() => setSelectedSlug(organization.slug)}
                        type="button"
                      >
                        <span className="grid size-8 place-items-center rounded-md bg-primary/10 text-primary">
                          <Building2 className="size-4" />
                        </span>
                        <span className="min-w-0">
                          <span className="block truncate text-sm font-semibold">
                            {organization.name}
                          </span>
                          <span className="block truncate font-mono text-[0.7rem] text-muted-foreground">
                            {organization.slug}
                          </span>
                        </span>
                        <Badge
                          variant={
                            organization.status === 'active'
                              ? 'secondary'
                              : 'outline'
                          }
                        >
                          {organizationStatus(organization.status)}
                        </Badge>
                      </button>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">
                  Aún no hay instituciones creadas.
                </p>
              )}
              <p className="mt-4 text-xs leading-5 text-muted-foreground">
                Este directorio no concede acceso a cursos, personas, notas ni
                configuración institucional.
              </p>
            </CardContent>
          </Card>
          {selectedSlug ? (
            <PlatformBootstrapInvitations slug={selectedSlug} />
          ) : (
            <div className="rounded-xl border border-dashed p-8 text-center text-sm text-muted-foreground">
              Selecciona una institución para revisar su activación.
            </div>
          )}
        </section>
      </div>
    </div>
  );
}

function PlatformMetric({
  label,
  tone,
  value,
}: Readonly<{
  label: string;
  tone?: 'active' | 'pending';
  value: number;
}>) {
  return (
    <article className="border-b px-5 py-4 last:border-b-0 sm:border-r sm:border-b-0 sm:last:border-r-0">
      <p className="text-xs font-medium text-muted-foreground">{label}</p>
      <div className="mt-1 flex items-center gap-2">
        <strong className="text-2xl tracking-tight">{value}</strong>
        {tone ? (
          <span
            aria-hidden="true"
            className={`size-2 rounded-full ${tone === 'active' ? 'bg-emerald-500' : 'bg-amber-500'}`}
          />
        ) : null}
      </div>
    </article>
  );
}

function PlatformBootstrapInvitations({ slug }: Readonly<{ slug: string }>) {
  const invitations = usePlatformBootstrapInvitations(slug);
  const resend = useResendPlatformBootstrapInvitation(slug);
  const revoke = useRevokePlatformBootstrapInvitation(slug);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MailCheck className="size-4 text-primary" />
          Invitaciones de activación
        </CardTitle>
        <p className="text-xs leading-5 text-muted-foreground">{slug}</p>
      </CardHeader>
      <CardContent>
        {invitations.isLoading ? (
          <p className="text-sm text-muted-foreground">Consultando estado…</p>
        ) : invitations.data?.length ? (
          <ul className="space-y-3">
            {invitations.data.map((invitation) => (
              <li className="rounded-lg border p-3" key={invitation.id}>
                <p className="truncate text-sm font-medium">
                  {invitation.email}
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {invitation.invitation_type === 'initial_owner'
                    ? 'Owner inicial'
                    : 'Administrador inicial'}{' '}
                  · {invitation.status}
                </p>
                {invitation.status === 'pending' ? (
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button
                      onClick={() => void resend.mutateAsync(invitation.id)}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      <RefreshCw />
                      Reenviar
                    </Button>
                    <Button
                      onClick={() => void revoke.mutateAsync(invitation.id)}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      <XCircle />
                      Revocar
                    </Button>
                  </div>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            No hay invitaciones de bootstrap registradas.
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function organizationStatus(status: Organization['status']) {
  if (status === 'pending_activation') return 'Pendiente';
  if (status === 'suspended') return 'Suspendida';
  if (status === 'closed') return 'Cerrada';
  return 'Activa';
}
