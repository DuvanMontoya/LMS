export const publicationKeys = {
  root: (slug: string, courseSlug: string) =>
    ['organizations', slug, 'courses', courseSlug, 'publication'] as const,
  status: (slug: string, courseSlug: string) =>
    [...publicationKeys.root(slug, courseSlug), 'status'] as const,
  releases: (slug: string, courseSlug: string) =>
    [...publicationKeys.root(slug, courseSlug), 'releases'] as const,
  release: (slug: string, courseSlug: string, releaseNumber: number) =>
    [...publicationKeys.releases(slug, courseSlug), releaseNumber] as const,
  verification: (slug: string, courseSlug: string, releaseNumber: number) =>
    [
      ...publicationKeys.release(slug, courseSlug, releaseNumber),
      'verification',
    ] as const,
};

export const libraryKeys = {
  root: (slug: string) => ['organizations', slug, 'library'] as const,
  courses: (slug: string) => [...libraryKeys.root(slug), 'courses'] as const,
  course: (slug: string, courseSlug: string) =>
    [...libraryKeys.courses(slug), courseSlug] as const,
  outline: (slug: string, courseSlug: string) =>
    [...libraryKeys.course(slug, courseSlug), 'outline'] as const,
  unit: (slug: string, courseSlug: string, unitId: string) =>
    [...libraryKeys.course(slug, courseSlug), 'units', unitId] as const,
};
