const CSRF_COOKIE_NAME = 'csrftoken';
const CSRF_HEADER_NAME = 'X-CSRFToken';
const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

let bootstrapPromise: Promise<string> | undefined;

export function readCookie(cookieHeader: string, name: string): string | null {
  for (const entry of cookieHeader.split(';')) {
    const separator = entry.indexOf('=');
    if (separator < 1) continue;

    const cookieName = entry.slice(0, separator).trim();
    if (cookieName !== name) continue;

    try {
      return decodeURIComponent(entry.slice(separator + 1).trim());
    } catch {
      return null;
    }
  }
  return null;
}

function csrfCookie(): string | null {
  return typeof document === 'undefined'
    ? null
    : readCookie(document.cookie, CSRF_COOKIE_NAME);
}

async function bootstrapCsrfToken(force = false): Promise<string> {
  const existing = csrfCookie();
  if (existing && !force) return existing;

  const response = await fetch('/_allauth/browser/v1/config', {
    cache: 'no-store',
    credentials: 'same-origin',
    headers: { Accept: 'application/json' },
  });
  if (!response.ok) {
    throw new Error('No fue posible inicializar la protección CSRF.');
  }

  const token = csrfCookie();
  if (!token) {
    throw new Error('Django no entregó la cookie CSRF requerida.');
  }
  return token;
}

export function ensureCsrfToken(force = false): Promise<string> {
  if (!bootstrapPromise || force) {
    bootstrapPromise = bootstrapCsrfToken(force).finally(() => {
      bootstrapPromise = undefined;
    });
  }
  return bootstrapPromise;
}

function requestMethod(input: RequestInfo | URL, init?: RequestInit): string {
  if (init?.method) return init.method.toUpperCase();
  return input instanceof Request ? input.method.toUpperCase() : 'GET';
}

async function isStructuredCsrfFailure(response: Response): Promise<boolean> {
  if (
    response.status !== 403 ||
    !response.headers.get('content-type')?.includes('application/json')
  ) {
    return false;
  }
  try {
    const payload: unknown = await response.clone().json();
    if (
      payload === null ||
      typeof payload !== 'object' ||
      !('errors' in payload)
    )
      return false;
    const errors = payload.errors;
    return (
      Array.isArray(errors) &&
      errors.some(
        (error) =>
          error !== null &&
          typeof error === 'object' &&
          'code' in error &&
          error.code === 'csrf_failed',
      )
    );
  } catch {
    return false;
  }
}

async function requestWithToken(
  input: RequestInfo | URL,
  init: RequestInit | undefined,
  token: string,
): Promise<Response> {
  const headers = new Headers(
    input instanceof Request ? input.headers : undefined,
  );
  new Headers(init?.headers).forEach((value, name) => headers.set(name, value));
  headers.set(CSRF_HEADER_NAME, token);
  return fetch(input, { ...init, credentials: 'same-origin', headers });
}

export async function csrfFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const method = requestMethod(input, init);
  if (SAFE_METHODS.has(method)) {
    return fetch(input, { ...init, credentials: 'same-origin' });
  }

  const response = await requestWithToken(input, init, await ensureCsrfToken());
  if (!(await isStructuredCsrfFailure(response))) return response;

  // allauth has no structured CSRF response in the current browser contract;
  // retry only if a future explicit code confirms a stale CSRF token.
  return requestWithToken(input, init, await ensureCsrfToken(true));
}
