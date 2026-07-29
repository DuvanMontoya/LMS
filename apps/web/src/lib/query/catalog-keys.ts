export const catalogKeys = {
  root: (slug: string) => ['organizations', slug, 'catalog'] as const,
  concepts: (slug: string) =>
    ['organizations', slug, 'catalog', 'concepts'] as const,
  structure: (slug: string) =>
    ['organizations', slug, 'catalog', 'structure'] as const,
};
