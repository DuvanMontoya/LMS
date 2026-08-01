import 'server-only';

import type { operations } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';

export type SearchResponse =
  operations['organizations_discovery_search']['responses'][200]['content']['application/json'];
export type SearchSuggestions =
  operations['organizations_discovery_search_suggestions']['responses'][200]['content']['application/json'];

export async function searchOrganization(
  slug: string,
  query: { page?: number; page_size?: number; q: string; types?: string },
): Promise<SearchResponse> {
  const client = await createPlatformServerClient();
  const { data, response } = await client.GET(
    '/api/v1/organizations/{organization_slug}/search/',
    { params: { path: { organization_slug: slug }, query } },
  );
  if (!response.ok || !data) {
    throw new Error('No fue posible ejecutar la búsqueda académica.');
  }
  return data;
}

export async function suggestOrganization(
  slug: string,
  query: string,
): Promise<SearchSuggestions> {
  const client = await createPlatformServerClient();
  const { data, response } = await client.GET(
    '/api/v1/organizations/{organization_slug}/search/suggestions/',
    {
      params: {
        path: { organization_slug: slug },
        query: { q: query },
      },
    },
  );
  if (!response.ok || !data) return [];
  return data;
}
