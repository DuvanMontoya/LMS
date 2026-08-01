import * as Sentry from '@sentry/nextjs';

import { beforeSend } from './src/lib/observability/sentry';

Sentry.init({
  dsn: process.env.SENTRY_DSN,
  enabled: Boolean(process.env.SENTRY_DSN),
  environment: process.env.SENTRY_ENVIRONMENT ?? 'development',
  release: process.env.SENTRY_RELEASE,
  sendDefaultPii: false,
  tracesSampleRate: Number(process.env.SENTRY_TRACES_SAMPLE_RATE ?? '0'),
  beforeSend,
});
