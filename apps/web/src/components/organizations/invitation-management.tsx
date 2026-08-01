'use client';

import { Ban, MailCheck, Plus, RotateCcw, UserRound } from 'lucide-react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import type { components, operations } from '@/lib/api/generated/platform';
import {
  useCorrectManagedAccountEmail,
  useOrganizationInvitationsWithFilters,
  useResendInvitation,
  useRevokeInvitation,
} from '@/lib/organizations/hooks';
import { roleLabel, sortRoles } from '@/lib/organizations/labels';

type InvitationList =
  operations['organizations_invitations_list']['responses'][200]['content']['application/json'];
type Invitation = InvitationList['results'][number];
type Role = components['schemas']['OrganizationRole'];

function errorMessage(error: unknown) {
  return error instanceof Error
    ? error.message
    : 'No fue posible completar la acción.';
}

function invitationStatus(status: string) {
  const labels: Record<string, string> = {
    accepted: 'Aceptada',
    expired: 'Expirada',
    pending: 'Pendiente',
    revoked: 'Revocada',
  };
  return labels[status] ?? status;
}

function invitationType(type: string) {
  const labels: Record<string, string> = {
    existing_user: 'Cuenta existente',
    managed_account: 'Cuenta administrada',
    new_user: 'Cuenta nueva',
  };
  return labels[type] ?? type;
}

export function InvitationManagement({
  initial,
  slug,
}: Readonly<{
  initial: InvitationList;
  slug: string;
}>) {
  const searchParams = useSearchParams();
  const initialStatus = searchParams.get('status');
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState<
    'accepted' | 'expired' | 'pending' | 'revoked' | ''
  >(
    initialStatus === 'accepted' ||
      initialStatus === 'expired' ||
      initialStatus === 'pending' ||
      initialStatus === 'revoked'
      ? initialStatus
      : '',
  );
  const [invitationType, setInvitationType] = useState<
    'existing_user' | 'managed_account' | 'new_user' | ''
  >('');
  const [page, setPage] = useState(1);
  const query = useOrganizationInvitationsWithFilters(slug, {
    ...(search.trim() ? { q: search.trim() } : {}),
    ...(status ? { status } : {}),
    ...(invitationType ? { invitation_type: invitationType } : {}),
    page,
  });
  const resend = useResendInvitation(slug);
  const revoke = useRevokeInvitation(slug);
  const correctEmail = useCorrectManagedAccountEmail(slug);
  const invitations =
    (query.data as unknown as InvitationList | undefined) ?? initial;
  const error = resend.error ?? revoke.error ?? correctEmail.error;
  const totalPages = Math.max(1, Math.ceil(invitations.count / 25));

  function resetPage() {
    setPage(1);
  }

  return (
    <section className="space-y-5" aria-labelledby="invitations-title">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-lg font-semibold" id="invitations-title">
            Invitaciones y activaciones
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Sigue cada incorporación: quién fue invitado, qué roles recibirá y
            cuándo deja de ser válida.
          </p>
        </div>
        <Button asChild>
          <Link href={`/organizaciones/${slug}/miembros/nuevo`}>
            <Plus data-icon="inline-start" />
            Registrar persona
          </Link>
        </Button>
      </div>

      {error ? (
        <Alert variant="destructive">
          <AlertTitle>No se actualizó la invitación</AlertTitle>
          <AlertDescription>{errorMessage(error)}</AlertDescription>
        </Alert>
      ) : null}

      <div className="grid gap-3 md:grid-cols-3">
        <Input
          aria-label="Buscar invitación"
          onChange={(event) => {
            setSearch(event.target.value);
            resetPage();
          }}
          placeholder="Nombre o correo"
          type="search"
          value={search}
        />
        <select
          aria-label="Filtrar invitaciones por estado"
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
          onChange={(event) => {
            setStatus(event.target.value as typeof status);
            resetPage();
          }}
          value={status}
        >
          <option value="">Todos los estados</option>
          <option value="pending">Activación pendiente</option>
          <option value="expired">Expiradas</option>
          <option value="accepted">Aceptadas</option>
          <option value="revoked">Revocadas</option>
        </select>
        <select
          aria-label="Filtrar invitaciones por incorporación"
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
          onChange={(event) => {
            setInvitationType(event.target.value as typeof invitationType);
            resetPage();
          }}
          value={invitationType}
        >
          <option value="">Todos los flujos</option>
          <option value="managed_account">Cuenta administrada</option>
          <option value="existing_user">Cuenta existente</option>
          <option value="new_user">Cuenta nueva</option>
        </select>
      </div>

      {invitations.results.length ? (
        <div className="grid gap-4">
          {invitations.results.map((invitation) => (
            <InvitationCard
              invitation={invitation}
              key={invitation.id}
              onCorrectEmail={(email) =>
                correctEmail.mutateAsync({
                  email,
                  invitationId: invitation.id,
                })
              }
              onResend={() => resend.mutateAsync(invitation.id)}
              onRevoke={() => revoke.mutateAsync(invitation.id)}
              pending={
                resend.isPending || revoke.isPending || correctEmail.isPending
              }
            />
          ))}
        </div>
      ) : (
        <Card className="border-dashed">
          <CardContent className="py-12 text-center">
            <MailCheck className="mx-auto size-7 text-muted-foreground" />
            <p className="mt-3 font-medium">No hay invitaciones registradas</p>
            <p className="mt-1 text-sm text-muted-foreground">
              Registra un estudiante, docente o colaborador para iniciar su
              incorporación.
            </p>
          </CardContent>
        </Card>
      )}
      {invitations.count > 25 ? (
        <nav
          aria-label="Paginación de invitaciones"
          className="flex items-center justify-between gap-3"
        >
          <p className="text-sm text-muted-foreground">
            Página {page} de {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              disabled={page <= 1}
              onClick={() => setPage((current) => current - 1)}
              size="sm"
              type="button"
              variant="outline"
            >
              Anterior
            </Button>
            <Button
              disabled={page >= totalPages}
              onClick={() => setPage((current) => current + 1)}
              size="sm"
              type="button"
              variant="outline"
            >
              Siguiente
            </Button>
          </div>
        </nav>
      ) : null}
    </section>
  );
}

function InvitationCard({
  invitation,
  onCorrectEmail,
  onResend,
  onRevoke,
  pending,
}: Readonly<{
  invitation: Invitation;
  onCorrectEmail: (email: string) => Promise<unknown>;
  onResend: () => Promise<unknown>;
  onRevoke: () => Promise<unknown>;
  pending: boolean;
}>) {
  const [replacementEmail, setReplacementEmail] = useState(invitation.email);
  const pendingInvitation = invitation.status === 'pending';
  const display =
    invitation.preferred_name ||
    [invitation.given_name, invitation.family_name].filter(Boolean).join(' ') ||
    invitation.email;
  return (
    <Card>
      <CardHeader className="gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <CardTitle className="flex items-center gap-2 text-base">
            <UserRound className="size-4 text-primary" />
            <span className="truncate">{display}</span>
          </CardTitle>
          <CardDescription className="mt-1 break-all">
            {invitation.email}
          </CardDescription>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge
            className="rounded"
            variant={pendingInvitation ? 'secondary' : 'outline'}
          >
            {invitationStatus(invitation.status)}
          </Badge>
          <Badge className="rounded" variant="outline">
            {invitationType(invitation.invitation_type)}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap gap-1.5">
          {sortRoles(invitation.roles as Role[]).map((role) => (
            <Badge className="rounded" key={role} variant="outline">
              {roleLabel(role)}
            </Badge>
          ))}
        </div>
        <dl className="grid gap-3 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs text-muted-foreground">Creada</dt>
            <dd>{new Date(invitation.created_at).toLocaleString('es-CO')}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">Expira</dt>
            <dd>{new Date(invitation.expires_at).toLocaleString('es-CO')}</dd>
          </div>
          <div>
            <dt className="text-xs text-muted-foreground">ID institucional</dt>
            <dd>{invitation.institutional_id || '—'}</dd>
          </div>
        </dl>
        {pendingInvitation ? (
          <div className="flex flex-wrap gap-2 border-t pt-4">
            <Button
              disabled={pending}
              onClick={() => void onResend()}
              size="sm"
              type="button"
              variant="outline"
            >
              <RotateCcw />
              Reenviar activación
            </Button>
            <Button
              disabled={pending}
              onClick={() => void onRevoke()}
              size="sm"
              type="button"
              variant="destructive"
            >
              <Ban />
              Revocar invitación
            </Button>
            {invitation.invitation_type === 'managed_account' ? (
              <form
                className="basis-full rounded-md border bg-muted/20 p-3 sm:flex sm:items-end sm:gap-3"
                onSubmit={(event) => {
                  event.preventDefault();
                  void onCorrectEmail(replacementEmail.trim());
                }}
              >
                <div className="min-w-0 flex-1 space-y-2">
                  <Label htmlFor={`managed-email-${invitation.id}`}>
                    Corregir correo antes de activar
                  </Label>
                  <Input
                    id={`managed-email-${invitation.id}`}
                    onChange={(event) =>
                      setReplacementEmail(event.target.value)
                    }
                    required
                    type="email"
                    value={replacementEmail}
                  />
                </div>
                <Button
                  disabled={
                    pending || replacementEmail.trim() === invitation.email
                  }
                  size="sm"
                  type="submit"
                  variant="outline"
                >
                  Guardar y reenviar
                </Button>
              </form>
            ) : null}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
