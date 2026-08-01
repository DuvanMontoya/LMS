'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import {
  CircleAlert,
  CircleCheck,
  Copy,
  FileUp,
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
import Link from 'next/link';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
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
import { csrfFetch } from '@/lib/api/csrf';
import {
  useConfirmBulkInvitations,
  useBulkMembershipTransition,
  useCreateManagedAccount,
  useCreateOrganizationInvitation,
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
  mode: z.enum(['invitation', 'managed']),
  email: z.string().email('Escribe un correo válido.'),
  roles: z.array(z.enum(roles)).min(1, 'Selecciona al menos un rol.'),
  given_name: z.string(),
  family_name: z.string(),
  preferred_name: z.string(),
  member_type: z.string(),
  institutional_id: z.string(),
  phone: z.string(),
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

export function AddMemberDialog({
  slug,
  onAdded,
}: Readonly<{
  slug: string;
  onAdded: (email: string) => void;
}>) {
  const [open, setOpen] = useState(false);
  const [registrationCopied, setRegistrationCopied] = useState(false);
  const [registrationCopyError, setRegistrationCopyError] = useState(false);
  const invitation = useCreateOrganizationInvitation(slug);
  const managedAccount = useCreateManagedAccount(slug);
  const form = useForm<AddMemberValues>({
    resolver: zodResolver(addMemberSchema),
    defaultValues: {
      mode: 'invitation',
      email: '',
      roles: ['learner'],
      given_name: '',
      family_name: '',
      preferred_name: '',
      member_type: '',
      institutional_id: '',
      phone: '',
    },
  });
  const mode = useWatch({ control: form.control, name: 'mode' });

  async function onSubmit(values: AddMemberValues) {
    try {
      if (values.mode === 'managed') {
        if (
          !values.given_name.trim() ||
          !values.family_name.trim() ||
          !values.member_type.trim()
        ) {
          form.setError('member_type', {
            message: 'Nombres, apellidos y tipo de miembro son obligatorios.',
          });
          return;
        }
        await managedAccount.mutateAsync({
          email: values.email,
          roles: values.roles,
          given_name: values.given_name,
          family_name: values.family_name,
          preferred_name: values.preferred_name,
          member_type: values.member_type,
          institutional_id: values.institutional_id,
          phone: values.phone,
        });
      } else {
        await invitation.mutateAsync({
          email: values.email,
          roles: values.roles,
        });
      }
      onAdded(values.email);
      form.reset();
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
          invitation.reset();
          managedAccount.reset();
          setRegistrationCopied(false);
          setRegistrationCopyError(false);
        }
      }}
      open={open}
    >
      <DialogTrigger asChild>
        <Button>
          <UserPlus data-icon="inline-start" />
          Invitar persona
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <DialogHeader>
          <DialogTitle>Invitar a una persona</DialogTitle>
          <DialogDescription>
            El acceso se creará únicamente cuando acepte y complete su
            verificación.
          </DialogDescription>
        </DialogHeader>
        <div className="rounded-lg border bg-muted/25 px-3 py-2.5 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div>
              <p className="font-medium">
                No se crea una membresía anticipada.
              </p>
              <p className="mt-0.5 text-xs leading-5 text-muted-foreground">
                Si ya tiene cuenta recibirá la invitación; si no, podrá
                registrarse desde el enlace de un solo uso.
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
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">
              Tipo de incorporación
            </legend>
            <div className="grid gap-2 sm:grid-cols-2">
              <label className="flex cursor-pointer items-start gap-2 rounded-lg border p-3 text-sm">
                <input
                  checked={mode === 'invitation'}
                  type="radio"
                  value="invitation"
                  {...form.register('mode')}
                />
                <span>
                  <span className="block font-medium">Invitación</span>
                  <span className="block text-xs text-muted-foreground">
                    La persona usa una cuenta existente o crea la suya.
                  </span>
                </span>
              </label>
              <label className="flex cursor-pointer items-start gap-2 rounded-lg border p-3 text-sm">
                <input
                  checked={mode === 'managed'}
                  type="radio"
                  value="managed"
                  {...form.register('mode')}
                />
                <span>
                  <span className="block font-medium">Cuenta administrada</span>
                  <span className="block text-xs text-muted-foreground">
                    La institución no conoce la contraseña; la persona la crea.
                  </span>
                </span>
              </label>
            </div>
          </fieldset>
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
          {mode === 'managed' ? (
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <Label htmlFor="managed-given-name">Nombres</Label>
                <Input
                  id="managed-given-name"
                  {...form.register('given_name')}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="managed-family-name">Apellidos</Label>
                <Input
                  id="managed-family-name"
                  {...form.register('family_name')}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="managed-member-type">Tipo de miembro</Label>
                <Input
                  id="managed-member-type"
                  {...form.register('member_type')}
                />
                {form.formState.errors.member_type?.message ? (
                  <p className="text-sm text-destructive">
                    {form.formState.errors.member_type.message}
                  </p>
                ) : null}
              </div>
              <div className="space-y-2">
                <Label htmlFor="managed-preferred-name">Nombre visible</Label>
                <Input
                  id="managed-preferred-name"
                  {...form.register('preferred_name')}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="managed-institutional-id">
                  ID institucional
                </Label>
                <Input
                  id="managed-institutional-id"
                  {...form.register('institutional_id')}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="managed-phone">Teléfono</Label>
                <Input id="managed-phone" {...form.register('phone')} />
              </div>
            </div>
          ) : null}
          <RolesFieldset
            canAssignOwner={false}
            error={form.formState.errors.roles?.message}
            register={form.register}
          />
          {invitation.error instanceof Error ||
          managedAccount.error instanceof Error ? (
            <Alert aria-live="polite" variant="destructive">
              <CircleAlert />
              <AlertTitle>No se pudo completar la incorporación</AlertTitle>
              <AlertDescription>
                <p>
                  {invitation.error instanceof Error
                    ? invitation.error.message
                    : managedAccount.error instanceof Error
                      ? managedAccount.error.message
                      : ''}
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
            <Button
              disabled={invitation.isPending || managedAccount.isPending}
              type="submit"
            >
              {invitation.isPending || managedAccount.isPending ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <UserPlus />
              )}
              {mode === 'managed' ? 'Crear activación' : 'Enviar invitación'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function BulkInvitationDialog({
  slug,
  onCompleted,
}: Readonly<{
  slug: string;
  onCompleted: (count: number) => void;
}>) {
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<
    components['schemas']['BulkInvitationPreviewResponse'] | undefined
  >();
  const [error, setError] = useState('');
  const confirm = useConfirmBulkInvitations(slug);

  async function createPreview() {
    if (!file) {
      setError('Selecciona un archivo CSV antes de continuar.');
      return;
    }
    setError('');
    const data = new FormData();
    data.set('file', file);
    const response = await csrfFetch(
      `/api/v1/organizations/${slug}/invitations/bulk/preview/`,
      { method: 'POST', body: data },
    );
    const payload: unknown = await response.json();
    if (!response.ok || !payload || typeof payload !== 'object') {
      setError('No fue posible validar el archivo.');
      return;
    }
    if (!('preview_id' in payload) || !('issues' in payload)) {
      setError('El servidor no devolvió una vista previa válida.');
      return;
    }
    setPreview(
      payload as components['schemas']['BulkInvitationPreviewResponse'],
    );
  }

  async function confirmPreview() {
    if (!preview) return;
    try {
      const result = await confirm.mutateAsync(preview.preview_id);
      const count =
        result && typeof result === 'object' && 'created' in result
          ? Number(result.created)
          : preview.valid_count;
      onCompleted(count);
      setOpen(false);
      setFile(null);
      setPreview(undefined);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'No fue posible confirmar las invitaciones.',
      );
    }
  }

  return (
    <Dialog
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) {
          setError('');
          setPreview(undefined);
        }
      }}
      open={open}
    >
      <DialogTrigger asChild>
        <Button type="button" variant="outline">
          <FileUp data-icon="inline-start" />
          Importar CSV
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>Importar invitaciones</DialogTitle>
          <DialogDescription>
            Usa UTF-8 y las columnas email, given_name, family_name,
            member_type, institutional_id y roles. Los roles se separan con |.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="invitation-csv">
              Archivo CSV (máximo 500 filas)
            </Label>
            <Input
              accept=".csv,text/csv"
              id="invitation-csv"
              onChange={(event) => {
                setFile(event.target.files?.[0] ?? null);
                setPreview(undefined);
                setError('');
              }}
              type="file"
            />
          </div>
          {preview ? (
            <div className="rounded-lg border p-3 text-sm">
              <p className="font-medium">
                {preview.valid_count} invitación
                {preview.valid_count === 1 ? '' : 'es'} válida
                {preview.valid_count === 1 ? '' : 's'}.
              </p>
              {preview.issues.length ? (
                <ul className="mt-2 list-disc space-y-1 pl-5 text-destructive">
                  {preview.issues.map((issue) => (
                    <li key={`${issue.row}-${issue.field}`}>
                      Fila {issue.row}, {issue.field}: {issue.message}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="mt-1 text-xs text-muted-foreground">
                  La confirmación creará todas las invitaciones en una sola
                  transacción. No se crea ninguna membresía anticipada.
                </p>
              )}
            </div>
          ) : null}
          {error ? <p className="text-sm text-destructive">{error}</p> : null}
        </div>
        <DialogFooter>
          <Button
            onClick={() => setOpen(false)}
            type="button"
            variant="outline"
          >
            Cancelar
          </Button>
          {preview && preview.issues.length === 0 ? (
            <Button
              disabled={confirm.isPending}
              onClick={() => void confirmPreview()}
              type="button"
            >
              {confirm.isPending ? (
                <LoaderCircle className="animate-spin" />
              ) : null}
              Confirmar invitaciones
            </Button>
          ) : (
            <Button onClick={() => void createPreview()} type="button">
              Validar archivo
            </Button>
          )}
        </DialogFooter>
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
  const [status, setStatus] = useState<'active' | 'suspended' | 'revoked' | ''>(
    '',
  );
  const [role, setRole] = useState<Role | ''>('');
  const [memberType, setMemberType] = useState('');
  const [ordering, setOrdering] = useState<
    'email' | '-email' | 'joined_at' | '-joined_at'
  >('email');
  const [success, setSuccess] = useState('');
  const [page, setPage] = useState(1);
  const [selectedMembershipIds, setSelectedMembershipIds] = useState<string[]>(
    [],
  );
  const bulkTransition = useBulkMembershipTransition(slug);
  const canAssignOwner = hasCapability(capabilities, 'role.assign_owner');
  const canSuspend = hasCapability(capabilities, 'membership.suspend');
  const canReactivate = hasCapability(capabilities, 'membership.reactivate');
  const canRevoke = hasCapability(capabilities, 'membership.revoke');
  const normalizedSearch = search.trim();
  const memberQuery = useOrganizationMembers(slug, {
    ...(normalizedSearch ? { q: normalizedSearch } : {}),
    ...(status ? { status } : {}),
    ...(role ? { role } : {}),
    ...(memberType.trim() ? { member_type: memberType.trim() } : {}),
    ordering,
    page,
  });
  const visibleMembers =
    (memberQuery.data as MemberList | undefined) ?? members;
  const activeCount = visibleMembers.results.filter(
    (membership) => membership.status === 'active',
  ).length;
  const selectableMembers = visibleMembers.results.filter(
    (membership) => !membership.roles.includes('owner') || canAssignOwner,
  );
  const selectableIds = selectableMembers.map(
    (membership) => membership.membership_id,
  );
  const allVisibleSelected =
    selectableIds.length > 0 &&
    selectableIds.every((membershipId) =>
      selectedMembershipIds.includes(membershipId),
    );
  const totalPages = Math.max(1, Math.ceil(visibleMembers.count / 25));

  function resetPage() {
    setPage(1);
    setSelectedMembershipIds([]);
  }

  function toggleMembership(membershipId: string, checked: boolean) {
    setSelectedMembershipIds((current) =>
      checked
        ? current.includes(membershipId)
          ? current
          : [...current, membershipId]
        : current.filter((currentId) => currentId !== membershipId),
    );
  }

  async function transitionSelected(
    action: 'reactivate' | 'revoke' | 'suspend',
  ) {
    await bulkTransition.mutateAsync({
      action,
      membershipIds: selectedMembershipIds,
    });
    setSuccess(
      `${selectedMembershipIds.length} membresías fueron actualizadas.`,
    );
    setSelectedMembershipIds([]);
  }

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
        {hasCapability(capabilities, 'membership.invite') ? (
          <div className="flex flex-wrap gap-2">
            <Button asChild>
              <Link href={`/organizaciones/${slug}/miembros/nuevo?rol=learner`}>
                <UserPlus data-icon="inline-start" />
                Registrar estudiante
              </Link>
            </Button>
            <Button asChild variant="outline">
              <Link href={`/organizaciones/${slug}/miembros/nuevo`}>
                Registrar persona
              </Link>
            </Button>
            <BulkInvitationDialog
              onCompleted={(count) => {
                setSearch('');
                setSuccess(`${count} invitaciones fueron creadas.`);
              }}
              slug={slug}
            />
            <Button asChild size="sm" variant="ghost">
              <Link
                href={`/organizaciones/${slug}/miembros/invitaciones?status=pending`}
              >
                Invitaciones
              </Link>
            </Button>
            {hasCapability(capabilities, 'membership.join_request.manage') ? (
              <Button asChild size="sm" variant="ghost">
                <Link href={`/organizaciones/${slug}/miembros/solicitudes`}>
                  Solicitudes
                </Link>
              </Button>
            ) : null}
          </div>
        ) : null}
      </div>

      {success ? (
        <Alert className="mt-4 border-emerald-600/20 bg-emerald-500/5">
          <CircleCheck className="text-emerald-700" />
          <AlertTitle>Invitación enviada</AlertTitle>
          <AlertDescription>{success}</AlertDescription>
        </Alert>
      ) : null}

      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(15rem,1.3fr)_minmax(9rem,.7fr)_minmax(9rem,.7fr)_minmax(10rem,.8fr)_minmax(11rem,.8fr)]">
        <div className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            aria-label="Buscar persona"
            className="pl-9"
            onChange={(event) => {
              setSearch(event.target.value);
              setSuccess('');
              resetPage();
            }}
            placeholder="Nombre, correo o nombre visible"
            type="search"
            value={search}
          />
        </div>
        <select
          aria-label="Filtrar por estado"
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
          onChange={(event) => {
            setStatus(event.target.value as typeof status);
            resetPage();
          }}
          value={status}
        >
          <option value="">Todos los estados</option>
          <option value="active">Activas</option>
          <option value="suspended">Suspendidas</option>
          <option value="revoked">Revocadas</option>
        </select>
        <select
          aria-label="Filtrar por rol"
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
          onChange={(event) => {
            setRole(event.target.value as Role | '');
            resetPage();
          }}
          value={role}
        >
          <option value="">Todos los roles</option>
          {roles.map((candidate) => (
            <option key={candidate} value={candidate}>
              {roleLabel(candidate)}
            </option>
          ))}
        </select>
        <Input
          aria-label="Filtrar por tipo institucional"
          onChange={(event) => {
            setMemberType(event.target.value);
            resetPage();
          }}
          placeholder="Tipo institucional"
          value={memberType}
        />
        <select
          aria-label="Ordenar miembros"
          className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs"
          onChange={(event) => {
            setOrdering(event.target.value as typeof ordering);
            resetPage();
          }}
          value={ordering}
        >
          <option value="email">Correo A–Z</option>
          <option value="-email">Correo Z–A</option>
          <option value="-joined_at">Más recientes</option>
          <option value="joined_at">Más antiguos</option>
        </select>
      </div>

      {selectedMembershipIds.length ? (
        <div
          aria-label="Acciones para miembros seleccionados"
          className="mt-4 flex flex-col gap-3 rounded-lg border bg-muted/20 p-3 sm:flex-row sm:items-center sm:justify-between"
        >
          <p className="text-sm">
            <span className="font-medium">{selectedMembershipIds.length}</span>{' '}
            {selectedMembershipIds.length === 1
              ? 'membresía seleccionada'
              : 'membresías seleccionadas'}
          </p>
          <div className="flex flex-wrap gap-2">
            {canSuspend ? (
              <ConfirmAction
                description="Suspenderás las membresías seleccionadas. La operación es atómica: si una no puede cambiar, ninguna se modifica."
                label="Suspender seleccionadas"
                onConfirm={() => transitionSelected('suspend')}
                pending={bulkTransition.isPending}
              />
            ) : null}
            {canReactivate ? (
              <ConfirmAction
                description="Reactivarás las membresías seleccionadas de forma atómica."
                label="Reactivar seleccionadas"
                onConfirm={() => transitionSelected('reactivate')}
                pending={bulkTransition.isPending}
              />
            ) : null}
            {canRevoke ? (
              <ConfirmAction
                description="Revocarás las membresías seleccionadas de forma atómica. Sus roles activos dejarán de tener efecto."
                label="Revocar seleccionadas"
                onConfirm={() => transitionSelected('revoke')}
                pending={bulkTransition.isPending}
                variant="destructive"
              />
            ) : null}
            <Button
              onClick={() => setSelectedMembershipIds([])}
              size="sm"
              type="button"
              variant="ghost"
            >
              Limpiar selección
            </Button>
          </div>
        </div>
      ) : null}

      {visibleMembers.results.length ? (
        <div className="mt-4 overflow-hidden rounded-lg border bg-card">
          <div className="hidden grid-cols-[2rem_minmax(15rem,1.2fr)_minmax(13rem,1fr)_7rem_minmax(15rem,auto)] gap-4 border-b bg-muted/30 px-5 py-2.5 text-[0.6875rem] font-semibold tracking-wider text-muted-foreground uppercase lg:grid">
            <label
              className="flex items-center"
              title="Seleccionar resultados visibles"
            >
              <input
                aria-label="Seleccionar resultados visibles"
                checked={allVisibleSelected}
                disabled={selectableIds.length === 0}
                onChange={(event) =>
                  setSelectedMembershipIds((current) =>
                    event.target.checked
                      ? Array.from(new Set([...current, ...selectableIds]))
                      : current.filter(
                          (membershipId) =>
                            !selectableIds.includes(membershipId),
                        ),
                  )
                }
                type="checkbox"
              />
            </label>
            <span>Persona</span>
            <span>Responsabilidad</span>
            <span>Estado</span>
            <span className="text-right">Acciones</span>
          </div>
          <ul className="divide-y">
            {visibleMembers.results.map((membership) => (
              <li
                className="grid gap-4 px-5 py-4 lg:grid-cols-[2rem_minmax(15rem,1.2fr)_minmax(13rem,1fr)_7rem_minmax(15rem,auto)] lg:items-center"
                key={membership.membership_id}
              >
                <div className="flex items-center">
                  <input
                    aria-label={`Seleccionar ${membership.user.display}`}
                    checked={selectedMembershipIds.includes(
                      membership.membership_id,
                    )}
                    disabled={
                      membership.roles.includes('owner') && !canAssignOwner
                    }
                    onChange={(event) =>
                      toggleMembership(
                        membership.membership_id,
                        event.target.checked,
                      )
                    }
                    type="checkbox"
                  />
                </div>
                <div className="flex min-w-0 items-center gap-3">
                  <Avatar className="size-9">
                    <AvatarFallback className="bg-primary/5 text-xs font-semibold text-primary">
                      {initials(membership.user.display)}
                    </AvatarFallback>
                  </Avatar>
                  <div className="min-w-0">
                    <Link
                      className="block truncate text-sm font-semibold hover:underline"
                      href={`/organizaciones/${slug}/miembros/${membership.membership_id}`}
                    >
                      {membership.user.display}
                    </Link>
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
                <div className="flex flex-wrap justify-end gap-2">
                  <Button asChild size="sm" variant="ghost">
                    <Link
                      href={`/organizaciones/${slug}/miembros/${membership.membership_id}`}
                    >
                      Ver ficha
                    </Link>
                  </Button>
                  <MemberActions
                    capabilities={capabilities}
                    membership={membership as Membership}
                    organizationName={organizationName}
                    slug={slug}
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="mt-4 rounded-lg border border-dashed p-10 text-center">
          <UsersRound className="mx-auto size-6 text-muted-foreground" />
          <p className="mt-3 font-medium">
            {search || status || role || memberType
              ? 'No hay coincidencias'
              : 'No hay membresías para mostrar'}
          </p>
          {search || status || role || memberType ? (
            <Button
              className="mt-3"
              onClick={() => {
                setSearch('');
                setStatus('');
                setRole('');
                setMemberType('');
              }}
              size="sm"
              variant="outline"
            >
              Limpiar búsqueda
            </Button>
          ) : null}
        </div>
      )}
      {visibleMembers.count > 25 ? (
        <nav
          aria-label="Paginación del directorio"
          className="mt-4 flex items-center justify-between gap-3"
        >
          <p className="text-sm text-muted-foreground">
            Página {page} de {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              disabled={page <= 1}
              onClick={() => {
                setPage((current) => current - 1);
                setSelectedMembershipIds([]);
              }}
              size="sm"
              type="button"
              variant="outline"
            >
              Anterior
            </Button>
            <Button
              disabled={page >= totalPages}
              onClick={() => {
                setPage((current) => current + 1);
                setSelectedMembershipIds([]);
              }}
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
