import createClient from 'openapi-fetch';

import { csrfFetch } from './csrf';
import type { paths } from './generated/allauth';

export function createBrowserClient() {
  return createClient<paths>({
    baseUrl: '',
    credentials: 'same-origin',
    fetch: csrfFetch,
  });
}

export const browserClient = createBrowserClient();
