import * as Sentry from '@sentry/nextjs';

import { beforeSend } from '@/lib/observability/sentry';

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  enabled: Boolean(process.env.NEXT_PUBLIC_SENTRY_DSN),
  sendDefaultPii: false,
  tracesSampleRate: Number(
    process.env.NEXT_PUBLIC_SENTRY_TRACES_SAMPLE_RATE ?? '0',
  ),
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,
  beforeSend,
});

export const onRouterTransitionStart = Sentry.captureRouterTransitionStart;
