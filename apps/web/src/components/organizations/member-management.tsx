'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import {
  CircleAlert,
  CircleCheck,
  Copy,
  LoaderCircle,
  Mail,
  RotateCcw,
  Save,
  Search,
  ShieldCheck,
  UserPlus,
  UserRoundX,
  UsersRound,
} from 'lucide-react';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { components, operations } from '@/lib/api/generated/platform';
import {
  useAddOrganizationMember,
  useOrganizationMembers,
  useReactivateMembership,
  useReplaceMembershipRoles,
  useRevokeMembership,
  useSuspendMembership,
} from '@/lib/organizations/hooks';
import {
  hasCapability,
  roleLabel,
  sortRoles,
} from '@/lib/organizations/labels';

type Role = components['schemas']['OrganizationRole'];
type MemberList =
  operations['organizations_memberships_list']['responses'][200]['content']['application/json'];
type Membership = components['schemas']['Membership'];

const roles: Role[] = [
  'owner',
  'administrator',
  'author',
  'reviewer',
  'instructor',
  'learner',
];

const addMemberSchema = z.object({
  email: z.string().email('Escribe un correo válido.'),
  roles: z.array(z.enum(roles)).min(1, 'Selecciona al menos un rol.'),
});
type AddMemberValues = z.infer<typeof addMemberSchema>;

function visibleRoles(canAssignOwner: boolean): Role[] {
  return canAssignOwner ? roles : roles.filter((role) => role !== 'owner');
}

function RolesFieldset({
  register,
  error,
  canAssignOwner,
}: Readonly<{
  register: ReturnType<typeof useForm<AddMemberValues>>['register'];
  error?: string | undefined;
  canAssignOwner: boolean;
}>) {
  return (
    <fieldset>
      <legend className="text-sm font-medium">Roles institucionales</legend>
      <p className="mt-1 text-xs text-muted-foreground">
        Selecciona únicamente las responsabilidades que ejercerá.
      </p>
      <div className="mt-3 grid overflow-hidden rounded-md border sm:grid-cols-2">
        {visibleRoles(canAssignOwner).map((role) => (
          <label
            className="flex min-h-10 items-center gap-2 border-b px-3 text-sm last:border-b-0 hover:bg-muted/30 sm:odd:border-r sm:nth-last-[-n+2]:border-b-0"
            key={role}
          >
            <input
              className="size-4 accent-primary"
              type="checkbox"
              value={role}
              {...register('roles')}
            />
            {roleLabel(role)}
          </label>
        ))}
      </div>
      {error ? <p className="mt-2 text-sm text-destructive">{error}</p> : null}
    </fieldset>
  );
}

function AddMemberDialog({
  slug,
  capabilities,
  onAdded,
}: Readonly<{
  slug: string;
  capabilities: readonly string[];
  onAdded: (email: string) => void;
}>) {
  const [open, setOpen] = useState(false);
  const [registrationCopied, setRegistrationCopied] = useState(false);
  const [registrationCopyError, setRegistrationCopyError] = useState(false);
  const addMember = useAddOrganizationMember(slug);
  const canAssignOwner = hasCapability(capabilities, 'role.assign_owner');
  const form = useForm<AddMemberValues>({
    resolver: zodResolver(addMemberSchema),
    defaultValues: { email: '', roles: ['learner'] },
  });

  async function onSubmit(values: AddMemberValues) {
    try {
      await addMember.mutateAsync(values);
      onAdded(values.email);
      form.reset({ email: '', roles: ['learner'] });
      setOpen(false);
    } catch {
      // The mutation exposes the structured API message inside the dialog.
    }
  }

  return (
    <Dialog
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) {
          form.clearErrors();
          addMember.reset();
          setRegistrationCopied(false);
          setRegistrationCopyError(false);
        }
      }}
      open={open}
    >
      <DialogTrigger asChild>
        <Button>
          <UserPlus data-icon="inline-start" />
          Añadir miembro
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Añadir miembro existente</DialogTitle>
          <DialogDescription>
            Vincula una cuenta verificada y define su acceso institucional.
          </DialogDescription>
        </DialogHeader>
        <div className="rounded-lg border bg-muted/25 px-3 py-2.5 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-medium">
                La persona debe tener una cuenta activa.
              </p>
              <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
                Su correo debe estar registrado y verificado.
              </p>
            </div>
            <Button
              onClick={async () => {
                try {
                  await navigator.clipboard.writeText(
                    `${window.location.origin}/auth/registro`,
                  );
                  setRegistrationCopied(true);
                  setRegistrationCopyError(false);
                } catch {
                  setRegistrationCopyError(true);
                }
              }}
              size="sm"
              type="button"
              variant="outline"
            >
              {registrationCopied ? <CircleCheck /> : <Copy />}
              {registrationCopied ? 'Enlace copiado' : 'Copiar registro'}
            </Button>
          </div>
          {registrationCopyError ? (
            <p className="mt-2 text-xs text-destructive" role="alert">
              No se pudo copiar. Abre /auth/registro y comparte esa dirección.
            </p>
          ) : null}
        </div>
        <form
          className="space-y-4"
          noValidate
          onSubmit={form.handleSubmit(onSubmit)}
        >
          <div className="space-y-2">
            <Label htmlFor="member-email">Correo electrónico</Label>
            <div className="relative">
              <Mail className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                aria-invalid={Boolean(form.formState.errors.email)}
                autoComplete="email"
                className="pl-9"
                id="member-email"
                placeholder="persona@institucion.edu"
                type="email"
                {...form.register('email')}
              />
            </div>
            {form.formState.errors.email?.message ? (
              <p className="text-sm text-destructive">
                {form.formState.errors.email.message}
              </p>
            ) : null}
          </div>
          <RolesFieldset
            canAssignOwner={canAssignOwner}
            error={form.formState.errors.roles?.message}
            register={form.register}
          />
          {addMember.error instanceof Error ? (
            <Alert aria-live="polite" variant="destructive">
              <CircleAlert />
              <AlertTitle>No se pudo añadir la membresía</AlertTitle>
              <AlertDescription>
                <p>{addMember.error.message}</p>
                <p>
                  Comprueba que la cuenta esté activa, tenga el correo
                  verificado y no conserve otra membresía vigente aquí.
                </p>
              </AlertDescription>
            </Alert>
          ) : null}
          <DialogFooter>
            <Button
              onClick={() => setOpen(false)}
              type="button"
              variant="outline"
            >
              Cancelar
            </Button>
            <Button disabled={addMember.isPending} type="submit">
              {addMember.isPending ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <UserPlus />
              )}
              Crear membresía
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ConfirmAction({
  description,
  label,
  onConfirm,
  pending,
  variant = 'outline',
}: Readonly<{
  description: string;
  label: string;
  onConfirm: () => Promise<unknown>;
  pending: boolean;
  variant?: 'destructive' | 'outline';
}>) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');

  async function confirm() {
    setError('');
    try {
      await onConfirm();
      setOpen(false);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'No fue posible completar la acción.',
      );
    }
  }

  return (
    <AlertDialog onOpenChange={setOpen} open={open}>
      <AlertDialogTrigger asChild>
        <Button size="sm" variant={variant}>
          {label === 'Reactivar' ? <RotateCcw /> : <UserRoundX />}
          {label}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{label} membresía</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        {error ? (
          <p aria-live="polite" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={pending}>Cancelar</AlertDialogCancel>
          <Button
            disabled={pending}
            onClick={() => void confirm()}
            variant={variant}
          >
            {pending ? <LoaderCircle className="animate-spin" /> : null}
            Confirmar
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

function MemberActions({
  slug,
  membership,
  organizationName,
  capabilities,
}: Readonly<{
  slug: string;
  membership: Membership;
  organizationName: string;
  capabilities: readonly string[];
}>) {
  const [rolesOpen, setRolesOpen] = useState(false);
  const suspend = useSuspendMembership(slug);
  const reactivate = useReactivateMembership(slug);
  const revoke = useRevokeMembership(slug);
  const replaceRoles = useReplaceMembershipRoles(slug);
  const canAssignRoles = hasCapability(capabilities, 'role.assign');
  const canAssignOwner = hasCapability(capabilities, 'role.assign_owner');
  const targetIsOwner = membership.roles.includes('owner');
  const canManageTarget = !targetIsOwner || canAssignOwner;
  const canSuspend = hasCapability(capabilities, 'membership.suspend');
  const canReactivate = hasCapability(capabilities, 'membership.reactivate');
  const canRevoke = hasCapability(capabilities, 'membership.revoke');
  const roleForm = useForm<AddMemberValues>({
    resolver: zodResolver(addMemberSchema),
    defaultValues: {
      email: membership.user.email,
      roles: membership.roles as Role[],
    },
  });

  async function saveRoles(values: AddMemberValues) {
    await replaceRoles.mutateAsync({
      membershipId: membership.membership_id,
      roles: values.roles,
    });
    setRolesOpen(false);
  }

  const hasActions =
    canManageTarget &&
    (canAssignRoles ||
      (membership.status === 'active' && canSuspend) ||
      (membership.status === 'suspended' && canReactivate) ||
      (membership.status !== 'revoked' && canRevoke));
  if (!hasActions)
    return <span className="text-xs text-muted-foreground">—</span>;

  return (
    <div className="flex flex-wrap justify-end gap-2">
      {canAssignRoles && canManageTarget ? (
        <Dialog
          onOpenChange={(open) => {
            setRolesOpen(open);
            if (open) {
              roleForm.reset({
                email: membership.user.email,
                roles: membership.roles as Role[],
              });
            }
          }}
          open={rolesOpen}
        >
          <DialogTrigger asChild>
            <Button size="sm" variant="outline">
              <ShieldCheck />
              Gestionar roles
            </Button>
          </DialogTrigger>
          <DialogContent className="sm:max-w-lg">
            <DialogHeader>
              <DialogTitle>Roles de {membership.user.display}</DialogTitle>
              <DialogDescription>
                Ajusta la responsabilidad de esta persona en {organizationName}.
              </DialogDescription>
            </DialogHeader>
            <form
              className="space-y-4"
              noValidate
              onSubmit={roleForm.handleSubmit(saveRoles)}
            >
              <RolesFieldset
                canAssignOwner={canAssignOwner}
                error={roleForm.formState.errors.roles?.message}
                register={roleForm.register}
              />
              {replaceRoles.error instanceof Error ? (
                <p className="text-sm text-destructive">
                  {replaceRoles.error.message}
                </p>
              ) : null}
              <DialogFooter>
                <Button
                  onClick={() => setRolesOpen(false)}
                  type="button"
                  variant="outline"
                >
                  Cancelar
                </Button>
                <Button disabled={replaceRoles.isPending} type="submit">
                  <Save />
                  Guardar roles
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      ) : null}
      {membership.status === 'active' && canSuspend && canManageTarget ? (
        <ConfirmAction
          description={`Suspenderás a ${membership.user.display} en ${organizationName}. Perderá el acceso institucional hasta reactivar su membresía.`}
          label="Suspender"
          onConfirm={() => suspend.mutateAsync(membership.membership_id)}
          pending={suspend.isPending}
        />
      ) : null}
      {membership.status === 'suspended' && canReactivate && canManageTarget ? (
        <ConfirmAction
          description={`Reactivarás a ${membership.user.display} en ${organizationName}. Recuperará el acceso de sus roles activos.`}
          label="Reactivar"
          onConfirm={() => reactivate.mutateAsync(membership.membership_id)}
          pending={reactivate.isPending}
        />
      ) : null}
      {membership.status !== 'revoked' && canRevoke && canManageTarget ? (
        <ConfirmAction
          description={`Revocarás a ${membership.user.display} de ${organizationName}. La membresía terminará y sus roles activos serán revocados.`}
          label="Revocar"
          onConfirm={() => revoke.mutateAsync(membership.membership_id)}
          pending={revoke.isPending}
          variant="destructive"
        />
      ) : null}
    </div>
  );
}

export function MemberManagement({
  slug,
  organizationName,
  capabilities,
  members,
}: Readonly<{
  slug: string;
  organizationName: string;
  capabilities: readonly string[];
  members: MemberList;
}>) {
  const [search, setSearch] = useState('');
  const [success, setSuccess] = useState('');
  const normalizedSearch = search.trim();
  const memberQuery = useOrganizationMembers(
    slug,
    normalizedSearch ? { email: normalizedSearch, page: 1 } : { page: 1 },
  );
  const visibleMembers = memberQuery.data ?? members;
  const activeCount = visibleMembers.results.filter(
    (membership) => membership.status === 'active',
  ).length;

  return (
    <section aria-labelledby="directory-title">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-sm font-semibold" id="directory-title">
            Directorio institucional
          </h2>
          <p className="mt-1 text-xs text-muted-foreground">
            {visibleMembers.count}{' '}
            {visibleMembers.count === 1 ? 'membresía' : 'membresías'} ·{' '}
            {activeCount} {activeCount === 1 ? 'activa' : 'activas'}
          </p>
        </div>
        {hasCapability(capabilities, 'membership.add') ? (
          <AddMemberDialog
            capabilities={capabilities}
            onAdded={(email) => {
              setSearch('');
              setSuccess(`Se añadió ${email} y sus roles ya están activos.`);
            }}
            slug={slug}
          />
        ) : null}
      </div>

      {success ? (
        <Alert className="mt-4 border-emerald-600/20 bg-emerald-500/5">
          <CircleCheck className="text-emerald-700" />
          <AlertTitle>Membresía creada</AlertTitle>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      ) : null}

      <div className="relative mt-4 max-w-sm">
        <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          aria-label="Buscar miembro por correo"
          className="pl-9"
          onChange={(event) => {
            setSearch(event.target.value);
            setSuccess('');
          }}
          placeholder="Buscar por correo"
          type="search"
          value={search}
        />
      </div>

      {visibleMembers.results.length ? (
        <div className="mt-4 overflow-hidden rounded-lg border bg-card">
          <div className="hidden grid-cols-[minmax(15rem,1.2fr)_minmax(13rem,1fr)_7rem_minmax(15rem,auto)] gap-4 border-b bg-muted/30 px-5 py-2.5 text-[0.6875rem] font-semibold tracking-wider text-muted-foreground uppercase lg:grid">
            <span>Persona</span>
            <span>Responsabilidad</span>
            <span>Estado</span>
            <span className="text-right">Acciones</span>
          </div>
          <ul className="divide-y">
            {visibleMembers.results.map((membership) => (
              <li
                className="grid gap-4 px-5 py-4 lg:grid-cols-[minmax(15rem,1.2fr)_minmax(13rem,1fr)_7rem_minmax(15rem,auto)] lg:items-center"
                key={membership.membership_id}
              >
                <div className="flex min-w-0 items-center gap-3">
                  <Avatar className="size-9">
                    <AvatarFallback className="bg-primary/5 text-xs font-semibold text-primary">
                      {initials(membership.user.display)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold">
                      {membership.user.display}
                    </p>
                    {membership.user.display !== membership.user.email ? (
                      <p className="truncate text-xs text-muted-foreground">
                        {membership.user.email}
                      </p>
                    ) : null}
                  </div>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {sortRoles(membership.roles as Role[]).map((role) => (
                    <Badge className="rounded" key={role} variant="outline">
                      {roleLabel(role)}
                    </Badge>
                  ))}
                </div>
                <StatusBadge status={membership.status} />
                <MemberActions
                  capabilities={capabilities}
                  membership={membership as Membership}
                  organizationName={organizationName}
                  slug={slug}
                />
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="mt-4 rounded-lg border border-dashed p-10 text-center">
          <UsersRound className="mx-auto size-6 text-muted-foreground" />
          <p className="mt-3 font-medium">
            {search ? 'No hay coincidencias' : 'No hay membresías para mostrar'}
          </p>
          {search ? (
            <Button
              className="mt-3"
              onClick={() => setSearch('')}
              size="sm"
              variant="outline"
            >
              Limpiar búsqueda
            </Button>
          ) : null}
        </div>
      )}
    </section>
  );
}

function StatusBadge({ status }: Readonly<{ status: string | undefined }>) {
  const label =
    status === 'active'
      ? 'Activa'
      : status === 'suspended'
        ? 'Suspendida'
        : status === 'revoked'
          ? 'Revocada'
          : 'Sin estado';
  return (
    <Badge
      className="rounded"
      variant={
        status === 'active'
          ? 'secondary'
          : status === 'suspended'
            ? 'outline'
            : status === 'revoked'
              ? 'destructive'
              : 'outline'
      }
    >
      {label}
    </Badge>
  );
}

function initials(value: string) {
  return (
    value
      .split(/[\s@._-]+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((part) => part.charAt(0))
      .join('')
      .toUpperCase() || 'U'
  );
}
