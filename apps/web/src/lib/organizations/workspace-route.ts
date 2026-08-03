import type { OrganizationRole } from '@/lib/organizations/labels';

export function primaryWorkspaceHref(
  slug: string,
  roles: readonly OrganizationRole[],
): string {
  const base = `/organizaciones/${slug}`;
  if (roles.includes('owner')) return `${base}/miembros`;
  if (roles.includes('administrator')) return `${base}/aprendizaje/cohortes`;
  if (roles.includes('instructor'))
    return `${base}/aprendizaje/mis-asignaturas`;
  if (roles.includes('author') || roles.includes('reviewer')) {
    return `${base}/cursos/autoria`;
  }
  if (roles.includes('learner')) return `${base}/aprendizaje`;
  return base;
}
