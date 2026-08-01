import { browserClient } from '@/lib/api/browser-client';
import { csrfFetch } from '@/lib/api/csrf';
import {
  AuthApiError,
  toAuthApiError,
  toNetworkAuthError,
} from '@/lib/auth/errors';

import type { components } from '@/lib/api/generated/allauth';

type AuthenticationResponse = components['schemas']['AuthenticationResponse'];
type SessionUser = components['schemas']['User'];

export type AuthSession =
  | { kind: 'authenticated'; user: SessionUser }
  | { kind: 'pending_verification' }
  | { kind: 'anonymous' }
  | { kind: 'expired' };

function isAuthenticationResponse(
  value: unknown,
): value is AuthenticationResponse {
  if (value === null || typeof value !== 'object' || !('data' in value))
    return false;
  const data = value.data;
  return (
    data !== null &&
    typeof data === 'object' &&
    'flows' in data &&
    Array.isArray(data.flows)
  );
}

function hasPendingVerification(value: AuthenticationResponse): boolean {
  return value.data.flows.some(
    (flow) => flow.id === 'verify_email' && flow.is_pending === true,
  );
}

function unwrapMutation(
  response: Response,
  payload: unknown,
  acceptedStatuses: readonly number[],
): unknown {
  if (acceptedStatuses.includes(response.status)) return payload;
  throw toAuthApiError(response.status, payload);
}

async function browserRequest<T>(
  operation: () => Promise<{ response: Response; data?: T; error?: unknown }>,
  acceptedStatuses: readonly number[],
): Promise<unknown> {
  try {
    const result = await operation();
    return unwrapMutation(
      result.response,
      result.data ?? result.error,
      acceptedStatuses,
    );
  } catch (error) {
    if (error instanceof Error && error.name === 'AuthApiError') throw error;
    throw toNetworkAuthError();
  }
}

async function generatedBodyPost(
  path:
    | '/_allauth/browser/v1/auth/email/verify'
    | '/_allauth/browser/v1/auth/password/reset',
  body:
    | components['schemas']['VerifyEmail']
    | components['schemas']['ResetPassword'],
  acceptedStatuses: readonly number[],
): Promise<unknown> {
  try {
    const response = await csrfFetch(path, {
      method: 'POST',
      headers: {
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    let payload: unknown = null;
    if (response.headers.get('content-type')?.includes('application/json')) {
      payload = await response.json();
    }
    return unwrapMutation(response, payload, acceptedStatuses);
  } catch (error) {
    if (error instanceof Error && error.name === 'AuthApiError') throw error;
    throw toNetworkAuthError();
  }
}

export function signUp(email: string, password: string): Promise<unknown> {
  return browserRequest(
    () =>
      browserClient.POST('/_allauth/browser/v1/auth/signup', {
        body: { email, password },
      }),
    [200, 401],
  );
}

export function verifyEmail(key: string): Promise<unknown> {
  // allauth marks this requestBody optional in its OpenAPI 3 document, which
  // makes openapi-fetch reject a body at compile time. Keep the path and body
  // in this generated-type boundary until upstream fixes that schema metadata.
  return generatedBodyPost(
    '/_allauth/browser/v1/auth/email/verify',
    { key },
    [200, 401],
  );
}

export function resendVerification(): Promise<unknown> {
  return browserRequest(
    () => browserClient.POST('/_allauth/browser/v1/auth/email/verify/resend'),
    [200],
  );
}

export function login(email: string, password: string): Promise<unknown> {
  return browserRequest(async () => {
    const result = await browserClient.POST('/_allauth/browser/v1/auth/login', {
      body: { email, password },
    });
    if (result.response.status === 409) {
      throw new AuthApiError('already_authenticated', 409, null, {});
    }
    return result;
  }, [200]);
}

export function logout(): Promise<unknown> {
  return browserRequest(
    () => browserClient.DELETE('/_allauth/browser/v1/auth/session'),
    [401],
  );
}

export function requestPasswordReset(email: string): Promise<unknown> {
  return browserRequest(
    () =>
      browserClient.POST('/_allauth/browser/v1/auth/password/request', {
        body: { email },
      }),
    [200, 401],
  );
}

export function resetPassword(key: string, password: string): Promise<unknown> {
  return generatedBodyPost(
    '/_allauth/browser/v1/auth/password/reset',
    { key, password },
    [200, 401],
  );
}

export async function getBrowserAuthSession(): Promise<AuthSession> {
  try {
    const { response, data, error } = await browserClient.GET(
      '/_allauth/browser/v1/auth/session',
    );
    if (response.status === 200 && data) {
      return { kind: 'authenticated', user: data.data.user };
    }
    if (response.status === 410) return { kind: 'expired' };
    if (isAuthenticationResponse(error)) {
      return hasPendingVerification(error)
        ? { kind: 'pending_verification' }
        : { kind: 'anonymous' };
    }
    if (response.status === 401) return { kind: 'anonymous' };
    throw toAuthApiError(response.status, error);
  } catch (error) {
    if (error instanceof Error && error.name === 'AuthApiError') throw error;
    throw toNetworkAuthError();
  }
}
