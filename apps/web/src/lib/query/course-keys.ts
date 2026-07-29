export const courseKeys = {
  root: (slug: string) => ['organizations', slug, 'courses'] as const,
  list: (slug: string) => [...courseKeys.root(slug), 'list'] as const,
  course: (slug: string, courseSlug: string) =>
    [...courseKeys.root(slug), courseSlug] as const,
  outline: (slug: string, courseSlug: string, revisionId: string) =>
    [...courseKeys.course(slug, courseSlug), revisionId, 'outline'] as const,
};
