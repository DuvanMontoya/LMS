import type { ErrorEvent } from '@sentry/nextjs';

const sensitiveKeys =
  /authorization|cookie|email|password|query|token|secret|signature/i;

const emailPattern = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/gi;

function scrubString(value: string): string {
  const withoutEmail = value.replace(emailPattern, '[REDACTED]');
  if (/x-amz-|signature=/i.test(withoutEmail)) {
    try {
      const url = new URL(withoutEmail);
      return `${url.origin}${url.pathname}`;
    } catch {
      return '[REDACTED]';
    }
  }
  return withoutEmail;
}

export function scrub(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(scrub);
  if (typeof value === 'string') return scrubString(value);
  if (!value || typeof value !== 'object') return value;
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [
      key,
      sensitiveKeys.test(key) ? '[REDACTED]' : scrub(item),
    ]),
  );
}

export function beforeSend(event: ErrorEvent): ErrorEvent {
  const sanitized = scrub(event) as ErrorEvent;
  if (sanitized.request) {
    delete sanitized.request.data;
    delete sanitized.request.cookies;
    delete sanitized.request.headers;
    const cleanUrl = sanitized.request.url?.split('?')[0];
    if (cleanUrl) sanitized.request.url = cleanUrl;
  }
  if (sanitized.user?.id) sanitized.user = { id: sanitized.user.id };
  else delete sanitized.user;
  return sanitized;
}
