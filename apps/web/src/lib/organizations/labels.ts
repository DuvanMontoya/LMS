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
  'catalog.view': 'Ver currículo',
  'catalog.manage': 'Administrar currículo',
  'catalog.manage_prerequisites': 'Administrar prerrequisitos',
  'course.authoring.view': 'Ver cursos en autoría',
  'course.authoring.manage': 'Administrar estructuras de curso',
  'course.authoring.submit': 'Enviar estructuras a revisión',
  'course.authoring.review': 'Solicitar cambios de estructura',
  'course.authoring.approve': 'Aprobar estructuras de curso',
  'course.approved.view': 'Ver cursos aprobados',
  'assessment.bank.view': 'Ver bancos de preguntas',
  'assessment.bank.manage': 'Administrar bancos de preguntas',
  'assessment.bank.version': 'Versionar bancos de preguntas',
  'assessment.question.view': 'Ver preguntas',
  'assessment.question.manage': 'Administrar preguntas',
  'assessment.question.submit': 'Enviar preguntas a revisión',
  'assessment.question.review': 'Revisar preguntas',
  'assessment.question.approve': 'Aprobar preguntas',
  'assessment.authoring.view': 'Ver evaluaciones en autoría',
  'assessment.authoring.manage': 'Administrar evaluaciones',
  'assessment.authoring.submit': 'Enviar evaluaciones a revisión',
  'assessment.authoring.review': 'Revisar evaluaciones',
  'assessment.authoring.approve': 'Aprobar evaluaciones',
  'assessment.delivery.view': 'Ver entregas de evaluaciones',
  'assessment.delivery.manage': 'Administrar entregas de evaluaciones',
  'assessment.grading.manage': 'Calificar evaluaciones',
  'assessment.results.view': 'Ver resultados de evaluaciones',
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
