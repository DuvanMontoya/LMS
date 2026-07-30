type ApiErrorRecord = Record<string, unknown>;

function firstMessage(value: unknown): string | undefined {
  if (typeof value === 'string' && value.trim()) return value.trim();
  if (Array.isArray(value)) {
    for (const item of value) {
      const message = firstMessage(item);
      if (message) return message;
    }
    return undefined;
  }
  if (!value || typeof value !== 'object') return undefined;
  const record = value as ApiErrorRecord;
  for (const key of ['detail', 'message', 'non_field_errors', 'errors']) {
    const message = firstMessage(record[key]);
    if (message) return message;
  }
  for (const [key, item] of Object.entries(record)) {
    if (['code', 'status'].includes(key)) continue;
    const message = firstMessage(item);
    if (message) return message;
  }
  return undefined;
}

export function apiErrorMessage(error: unknown, fallback: string): string {
  return firstMessage(error) ?? fallback;
}

export function apiErrorCode(error: unknown): string | undefined {
  if (!error || typeof error !== 'object' || Array.isArray(error))
    return undefined;
  const code = (error as ApiErrorRecord).code;
  return typeof code === 'string' ? code : undefined;
}
