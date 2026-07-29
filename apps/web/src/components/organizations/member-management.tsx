'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

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
type Membership = MemberList['results'][number];

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
  initialRoles,
}: Readonly<{
  register: ReturnType<typeof useForm<AddMemberValues>>['register'];
  error?: string;
  canAssignOwner: boolean;
  initialRoles?: readonly string[];
}>) {
  return (
    <fieldset className="rounded-lg border border-slate-300 p-4">
      <legend className="px-1 font-medium text-slate-900">
        Roles institucionales
      </legend>
      <p className="mb-3 text-sm text-slate-600">
        Selecciona uno o más roles para esta membresía.
      </p>
      <div className="grid gap-2 sm:grid-cols-2">
        {visibleRoles(canAssignOwner).map((role) => (
          <label className="flex items-center gap-2" key={role}>
            <input
              defaultChecked={initialRoles?.includes(role)}
              type="checkbox"
              value={role}
              {...register('roles')}
            />
            {roleLabel(role)}
          </label>
        ))}
      </div>
      <p className="mt-2 min-h-5 text-sm text-red-700">{error ?? ''}</p>
    </fieldset>
  );
}

function AddMemberForm({
  slug,
  capabilities,
}: Readonly<{ slug: string; capabilities: readonly string[] }>) {
  const addMember = useAddOrganizationMember(slug);
  const canAssignOwner = hasCapability(capabilities, 'role.assign_owner');
  const form = useForm<AddMemberValues>({
    resolver: zodResolver(addMemberSchema),
    defaultValues: { email: '', roles: ['learner'] },
  });
  async function onSubmit(values: AddMemberValues) {
    await addMember.mutateAsync(values);
    form.reset({ email: '', roles: ['learner'] });
  }
  return (
    <form
      className="mt-8 space-y-4 rounded-xl border border-slate-200 p-5"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <h2 className="text-xl font-semibold text-slate-950">
        Añadir miembro existente
      </h2>
      <div>
        <label className="block font-medium" htmlFor="member-email">
          Correo electrónico
        </label>
        <input
          autoComplete="email"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          id="member-email"
          type="email"
          {...form.register('email')}
        />
        <p className="mt-1 min-h-5 text-sm text-red-700">
          {form.formState.errors.email?.message}
        </p>
      </div>
      <RolesFieldset
        canAssignOwner={canAssignOwner}
        error={form.formState.errors.roles?.message ?? ''}
        register={form.register}
      />
      <button
        className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={addMember.isPending}
        type="submit"
      >
        {addMember.isPending ? 'Añadiendo…' : 'Añadir miembro'}
      </button>
      <p aria-live="polite" className="text-sm text-slate-700">
        {addMember.isSuccess ? 'La membresía fue creada.' : ''}
        {addMember.error instanceof Error ? addMember.error.message : ''}
      </p>
    </form>
  );
}

function ConfirmAction({
  label,
  description,
  onConfirm,
  pending,
}: Readonly<{
  label: string;
  description: string;
  onConfirm: () => Promise<unknown>;
  pending: boolean;
}>) {
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState('');
  if (!confirming)
    return (
      <button
        className="underline"
        onClick={() => setConfirming(true)}
        type="button"
      >
        {label}
      </button>
    );
  return (
    <div className="space-y-2 rounded border border-amber-300 p-3" role="alert">
      <p>{description}</p>
      <button
        className="mr-3 rounded bg-slate-900 px-3 py-1 text-white"
        disabled={pending}
        onClick={() =>
          void onConfirm().catch((reason: unknown) =>
            setError(
              reason instanceof Error
                ? reason.message
                : 'No fue posible completar la acción.',
            ),
          )
        }
        type="button"
      >
        Confirmar {label.toLowerCase()}
      </button>
      <button
        className="underline"
        disabled={pending}
        onClick={() => setConfirming(false)}
        type="button"
      >
        Cancelar
      </button>
      <p aria-live="polite" className="text-sm text-red-700">
        {error}
      </p>
    </div>
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
  return (
    <div className="space-y-3">
      {canAssignRoles && canManageTarget ? (
        <form
          noValidate
          onSubmit={roleForm.handleSubmit(async (values) =>
            replaceRoles.mutateAsync({
              membershipId: membership.membership_id,
              roles: values.roles,
            }),
          )}
        >
          <RolesFieldset
            canAssignOwner={canAssignOwner}
            error={roleForm.formState.errors.roles?.message ?? ''}
            initialRoles={membership.roles}
            register={roleForm.register}
          />
          <button
            className="mt-2 underline"
            disabled={replaceRoles.isPending}
            type="submit"
          >
            Guardar roles
          </button>
        </form>
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
  const memberQuery = useOrganizationMembers(slug, { page: 1 });
  const visibleMembers = memberQuery.data ?? members;
  return (
    <section aria-labelledby="members-title" className="space-y-6">
      <h1 className="text-3xl font-semibold text-slate-950" id="members-title">
        Miembros de {organizationName}
      </h1>
      {hasCapability(capabilities, 'membership.add') ? (
        <AddMemberForm capabilities={capabilities} slug={slug} />
      ) : null}
      <div className="overflow-x-auto rounded-xl border border-slate-200">
        <table className="w-full text-left">
          <caption className="p-4 text-left text-sm text-slate-600">
            Membresías activas, suspendidas y revocadas de la organización.
          </caption>
          <thead className="bg-slate-50">
            <tr>
              <th className="p-3" scope="col">
                Persona
              </th>
              <th className="p-3" scope="col">
                Estado
              </th>
              <th className="p-3" scope="col">
                Roles
              </th>
              <th className="p-3" scope="col">
                Acciones
              </th>
            </tr>
          </thead>
          <tbody>
            {visibleMembers.results.map((membership) => (
              <tr
                className="border-t border-slate-200"
                key={membership.membership_id}
              >
                <td className="p-3">
                  <span className="block font-medium">
                    {membership.user.display}
                  </span>
                  <span className="text-sm text-slate-600">
                    {membership.user.email}
                  </span>
                </td>
                <td className="p-3">
                  {membership.status === 'active'
                    ? 'Activa'
                    : membership.status === 'suspended'
                      ? 'Suspendida'
                      : 'Revocada'}
                </td>
                <td className="p-3">
                  {sortRoles(membership.roles as Role[])
                    .map(roleLabel)
                    .join(', ')}
                </td>
                <td className="p-3">
                  <MemberActions
                    capabilities={capabilities}
                    membership={membership}
                    organizationName={organizationName}
                    slug={slug}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {visibleMembers.results.length === 0 ? (
        <p>No hay membresías para mostrar.</p>
      ) : null}
    </section>
  );
}
