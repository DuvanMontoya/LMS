export const authKeys = {
  session: () => ['auth', 'session'] as const,
  config: () => ['auth', 'config'] as const,
};
