import { primaryWorkspaceHref } from '@/lib/organizations/workspace-route';

import { sanitizeReturnPath } from './return-path';

type OrganizationAccess = {
  capabilities: readonly string[];
  roles: readonly (
    'owner' | 'administrator' | 'author' | 'reviewer' | 'instructor' | 'learner'
  )[];
  slug: string;
};

type AccessContext = {
  is_platform_operator: boolean;
  organizations: readonly OrganizationAccess[];
};

const DEFAULT_DESTINATION = '/estudiar';

function hasAnyCapability(
  capabilities: readonly string[],
  required: readonly string[],
) {
  return required.some((capability) => capabilities.includes(capability));
}

function hasPathPrefix(pathname: string, prefix: string) {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

function canOpenOrganizationPath(
  pathname: string,
  organization: OrganizationAccess,
): boolean {
  const base = `/organizaciones/${organization.slug}`;
  const relativePath = pathname.slice(base.length) || '/';
  const { capabilities, roles } = organization;

  if (
    relativePath === '/' ||
    hasPathPrefix(relativePath, '/notificaciones') ||
    hasPathPrefix(relativePath, '/ayuda') ||
    /^\/miembros\/[^/]+\/?$/.test(relativePath)
  ) {
    return true;
  }
  if (hasPathPrefix(relativePath, '/miembros'))
    return capabilities.includes('membership.view');
  if (hasPathPrefix(relativePath, '/configuracion'))
    return hasAnyCapability(capabilities, [
      'membership.settings.view',
      'integration.view',
    ]);
  if (hasPathPrefix(relativePath, '/curriculo'))
    return capabilities.includes('catalog.view');
  if (hasPathPrefix(relativePath, '/cursos'))
    return hasAnyCapability(capabilities, [
      'course.authoring.view',
      'course.approved.view',
    ]);
  if (hasPathPrefix(relativePath, '/aprendizaje/mis-asignaturas'))
    return hasAnyCapability(capabilities, [
      'catalog.teaching_responsibility.view',
      'catalog.teaching_responsibility.manage',
    ]);
  if (
    hasPathPrefix(relativePath, '/aprendizaje/cohortes') ||
    hasPathPrefix(relativePath, '/aprendizaje/periodos') ||
    hasPathPrefix(relativePath, '/aprendizaje/grupos')
  ) {
    return capabilities.includes('learning.cohort.view');
  }
  if (hasPathPrefix(relativePath, '/aprendizaje/matriculas'))
    return capabilities.includes('learning.enrollment.view');
  if (
    hasPathPrefix(relativePath, '/aprendizaje') ||
    hasPathPrefix(relativePath, '/aprender')
  )
    return roles.includes('learner');
  if (
    hasPathPrefix(relativePath, '/calendario') ||
    hasPathPrefix(relativePath, '/clases')
  ) {
    return capabilities.includes('scheduling.view');
  }
  if (hasPathPrefix(relativePath, '/recursos'))
    return capabilities.includes('asset.library.view');
  if (hasPathPrefix(relativePath, '/biblioteca'))
    return capabilities.includes('course.published.view');
  if (hasPathPrefix(relativePath, '/buscar'))
    return hasAnyCapability(capabilities, [
      'search.authoring.use',
      'search.institutional.use',
    ]);
  if (hasPathPrefix(relativePath, '/evaluaciones/asignadas'))
    return capabilities.includes('assessment.attempt');
  if (hasPathPrefix(relativePath, '/evaluaciones/calificaciones'))
    return capabilities.includes('assessment.attempt');
  if (hasPathPrefix(relativePath, '/evaluaciones/entregas'))
    return capabilities.includes('assessment.delivery.view');
  if (hasPathPrefix(relativePath, '/evaluaciones/resultados'))
    return capabilities.includes('assessment.results.view');
  if (hasPathPrefix(relativePath, '/evaluaciones/calificacion-manual'))
    return capabilities.includes('assessment.grading.manage');
  if (hasPathPrefix(relativePath, '/evaluaciones/regrading'))
    return capabilities.includes('assessment.regrading.view');
  if (hasPathPrefix(relativePath, '/evaluaciones/gradebooks'))
    return capabilities.includes('assessment.gradebook.view');
  if (hasPathPrefix(relativePath, '/evaluaciones/analitica'))
    return capabilities.includes('assessment.analytics.view');
  if (hasPathPrefix(relativePath, '/evaluaciones/bancos'))
    return hasAnyCapability(capabilities, [
      'assessment.bank.view',
      'assessment.question.view',
    ]);
  if (hasPathPrefix(relativePath, '/evaluaciones'))
    return capabilities.includes('assessment.authoring.view');
  return false;
}

function fallbackDestination(context: AccessContext, slug?: string) {
  const organization = slug
    ? context.organizations.find((item) => item.slug === slug)
    : undefined;
  if (organization)
    return primaryWorkspaceHref(organization.slug, organization.roles);
  if (context.is_platform_operator) return '/administracion/organizaciones';
  return DEFAULT_DESTINATION;
}

/**
 * Keeps a post-login redirect inside the authenticated user's effective
 * workspace. This is a UX guard only: each destination is still authorized by
 * its server component and API endpoint.
 */
export function resolvePostLoginDestination(
  candidate: string | null | undefined,
  context: AccessContext,
): string {
  const safePath = sanitizeReturnPath(candidate);
  const parsed = new URL(safePath, 'http://lms.invalid');
  const pathname = parsed.pathname;

  if (hasPathPrefix(pathname, '/administracion')) {
    return context.is_platform_operator
      ? safePath
      : fallbackDestination(context);
  }

  const match = /^\/organizaciones\/([^/]+)(?:\/|$)/.exec(pathname);
  if (!match) return safePath;
  const slug = decodeURIComponent(match[1] ?? '');
  const organization = context.organizations.find((item) => item.slug === slug);
  if (!organization || !canOpenOrganizationPath(pathname, organization)) {
    return fallbackDestination(context, slug);
  }
  return safePath;
}
