'use client';

import createClient from 'openapi-fetch';

import { csrfFetch } from './csrf';
import type { paths } from './generated/platform';

export const platformBrowserClient = createClient<paths>({
  baseUrl: '',
  credentials: 'same-origin',
  fetch: csrfFetch,
});
