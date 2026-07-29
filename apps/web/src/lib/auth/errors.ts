export type AuthErrorKind =
  | 'csrf'
  | 'network'
  | 'rate_limited'
  | 'session_expired'
  | 'pending_flow'
  | 'invalid_response'
  | 'validation'
  | 'unknown';

export class AuthApiError extends Error {
  constructor(
    readonly kind: AuthErrorKind,
    readonly status: number,
    readonly code: string | null,
    readonly fieldErrors: Readonly<Record<string, string>>,
  ) {
    super(mapAllauthErrorToSpanish(kind, code));
    this.name = 'AuthApiError';
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object';
}

function readErrors(payload: unknown): {
  code: string | null;
  fields: Record<string, string>;
} {
  if (!isRecord(payload) || !Array.isArray(payload.errors)) {
    return { code: null, fields: {} };
  }

  const fields: Record<string, string> = {};
  let code: string | null = null;
  for (const item of payload.errors) {
    if (!isRecord(item)) continue;
    const itemCode = typeof item.code === 'string' ? item.code : null;
    const parameter = typeof item.param === 'string' ? item.param : null;
    if (!code && itemCode) code = itemCode;
    if (parameter && itemCode) fields[parameter] = itemCode;
  }
  return { code, fields };
}

export function toAuthApiError(status: number, payload: unknown): AuthApiError {
  const { code, fields } = readErrors(payload);
  if (status === 429)
    return new AuthApiError('rate_limited', status, code, fields);
  if (status === 410)
    return new AuthApiError('session_expired', status, code, fields);
  if (status === 403 && code === 'csrf_failed')
    return new AuthApiError('csrf', status, code, fields);
  if (status === 401 || status === 409)
    return new AuthApiError('pending_flow', status, code, fields);
  if (status === 400 || status === 422)
    return new AuthApiError('validation', status, code, fields);
  return new AuthApiError('unknown', status, code, fields);
}

export function toNetworkAuthError(): AuthApiError {
  return new AuthApiError('network', 0, null, {});
}

export function mapAllauthErrorToSpanish(
  kind: AuthErrorKind,
  code: string | null,
): string {
  if (kind === 'rate_limited')
    return 'Demasiados intentos. Espera un momento antes de continuar.';
  if (kind === 'csrf')
    return 'La protección de seguridad expiró. Inténtalo nuevamente.';
  if (kind === 'network')
    return 'No fue posible conectar con la plataforma. Comprueba tu conexión e inténtalo nuevamente.';
  if (kind === 'session_expired')
    return 'Tu sesión ya no está disponible. Inicia sesión nuevamente.';
  if (code === 'email_password_mismatch' || code === 'incorrect_password') {
    return 'El correo o la contraseña no son correctos.';
  }
  if (code === 'incorrect_code' || code === 'invalid')
    return 'El código no es válido o ya expiró.';
  if (kind === 'pending_flow')
    return 'Completa el paso de autenticación pendiente para continuar.';
  return 'No fue posible completar la solicitud. Inténtalo nuevamente.';
}
