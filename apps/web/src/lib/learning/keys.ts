export const learningKeys = {
  all: (slug: string) => ['organizations', slug, 'learning'] as const,
  mine: (slug: string) => [...learningKeys.all(slug), 'me'] as const,
  enrollment: (slug: string, enrollmentId: string) =>
    [...learningKeys.mine(slug), enrollmentId] as const,
  outline: (slug: string, enrollmentId: string) =>
    [...learningKeys.enrollment(slug, enrollmentId), 'outline'] as const,
  unit: (slug: string, enrollmentId: string, unitId: string) =>
    [...learningKeys.enrollment(slug, enrollmentId), 'units', unitId] as const,
  progress: (slug: string, enrollmentId: string) =>
    [...learningKeys.enrollment(slug, enrollmentId), 'progress'] as const,
};

export const cohortKeys = {
  all: (slug: string) =>
    ['organizations', slug, 'learning', 'cohorts'] as const,
  detail: (slug: string, cohortId: string) =>
    [...cohortKeys.all(slug), cohortId] as const,
  enrollments: (slug: string, cohortId: string) =>
    [...cohortKeys.detail(slug, cohortId), 'enrollments'] as const,
  progress: (slug: string, cohortId: string) =>
    [...cohortKeys.detail(slug, cohortId), 'progress'] as const,
};

export const enrollmentAdminKeys = {
  all: (slug: string) =>
    ['organizations', slug, 'learning', 'enrollments'] as const,
  detail: (slug: string, enrollmentId: string) =>
    [...enrollmentAdminKeys.all(slug), enrollmentId] as const,
  progress: (slug: string, enrollmentId: string) =>
    [...enrollmentAdminKeys.detail(slug, enrollmentId), 'progress'] as const,
};
