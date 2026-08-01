import type { ErrorEvent } from '@sentry/nextjs';
import { describe, expect, it } from 'vitest';

import { beforeSend, scrub } from './sentry';

describe('observability privacy scrubber', () => {
  it('redacts nested secrets, email and signed URL query values', () => {
    const value = scrub({
      nested: {
        password: 'secret-value',
        note: 'contact person@example.test',
        link: 'https://storage.test/object?X-Amz-Signature=secret',
      },
    });
    expect(JSON.stringify(value)).not.toContain('secret-value');
    expect(JSON.stringify(value)).not.toContain('person@example.test');
    expect(JSON.stringify(value)).not.toContain('X-Amz-Signature');
    expect(value).toMatchObject({
      nested: {
        password: '[REDACTED]',
        note: 'contact [REDACTED]',
        link: 'https://storage.test/object',
      },
    });
  });

  it('removes request data, cookies, headers and query while retaining UUID user id', () => {
    const event = beforeSend({
      event_id: 'event',
      request: {
        cookies: { sessionid: 'secret' },
        data: { grading_payload: 'answer-key' },
        headers: { authorization: 'Bearer secret' },
        url: 'https://lms.test/buscar?q=private',
      },
      user: {
        email: 'person@example.test',
        id: '00000000-0000-4000-8000-000000000001',
      },
      type: undefined,
    } as unknown as ErrorEvent);
    expect(event.request).toEqual({ url: 'https://lms.test/buscar' });
    expect(event.user).toEqual({ id: '00000000-0000-4000-8000-000000000001' });
    expect(JSON.stringify(event)).not.toMatch(
      /private|answer-key|person@example/i,
    );
  });
});
