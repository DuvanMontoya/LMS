const DEFAULT_RETURN_PATH = '/estudiar';
const AUTH_PREFIX = '/auth/';

export function sanitizeReturnPath(
  candidate: string | null | undefined,
): string {
  if (!candidate || /[\u0000-\u001F\u007F]/.test(candidate))
    return DEFAULT_RETURN_PATH;
  if (candidate.includes('\\')) return DEFAULT_RETURN_PATH;

  try {
    const parsed = new URL(candidate, 'http://lms.invalid');
    if (parsed.origin !== 'http://lms.invalid' || !candidate.startsWith('/')) {
      return DEFAULT_RETURN_PATH;
    }
    if (decodeURIComponent(parsed.pathname).startsWith('//')) {
      return DEFAULT_RETURN_PATH;
    }
    if (parsed.pathname.startsWith(AUTH_PREFIX)) return DEFAULT_RETURN_PATH;
    return `${parsed.pathname}${parsed.search}${parsed.hash}`;
  } catch {
    return DEFAULT_RETURN_PATH;
  }
}
