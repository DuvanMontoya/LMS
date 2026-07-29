import type { components } from '@/lib/api/generated/platform';

export type OrganizationRole = components['schemas']['OrganizationRole'];
export type OrganizationCapability = string;

const roleLabels: Record<OrganizationRole, string> = {
  owner: 'Propietario',
  administrator: 'Administrador',
  author: 'Autor',
  reviewer: 'Revisor',
  instructor: 'Docente',
  learner: 'Estudiante',
};

const capabilityLabels: Record<string, string> = {
  'organization.view': 'Ver la organización',
  'organization.update': 'Editar el nombre institucional',
  'membership.view': 'Ver miembros',
  'membership.add': 'Añadir miembros',
  'membership.suspend': 'Suspender membresías',
  'membership.reactivate': 'Reactivar membresías',
  'membership.revoke': 'Revocar membresías',
  'role.view': 'Ver roles',
  'role.assign': 'Asignar roles institucionales',
  'role.assign_owner': 'Asignar o gestionar propietarios',
  'membership_event.view': 'Ver historial de membresía',
};

export function roleLabel(role: OrganizationRole): string {
  return roleLabels[role];
}

export function capabilityLabel(capability: OrganizationCapability): string {
  return capabilityLabels[capability] ?? 'Permiso institucional';
}

export function hasCapability(
  capabilities: readonly string[],
  capability: string,
): boolean {
  return capabilities.includes(capability);
}

export function sortRoles(
  roles: readonly OrganizationRole[],
): OrganizationRole[] {
  return [...roles].sort((left, right) =>
    roleLabel(left).localeCompare(roleLabel(right), 'es'),
  );
}
