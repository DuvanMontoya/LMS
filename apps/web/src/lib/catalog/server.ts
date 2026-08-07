import 'server-only';

import { notFound } from 'next/navigation';

import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

export async function getTeachingResponsibilities(slug: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const [
    { data, response },
    subjectsResult,
    courseExceptionsResult,
    coursesResult,
  ] = await Promise.all([
    client.GET(
      '/api/v1/organizations/{slug}/catalog/teaching-responsibilities/',
      { params: { path: { slug } }, cache: 'no-store' },
    ),
    organization.access.capabilities.includes('catalog.manage')
      ? client.GET('/api/v1/organizations/{slug}/catalog/subjects/', {
          params: {
            path: { slug },
            query: { ordering: 'name', status: 'active' },
          },
          cache: 'no-store',
        })
      : Promise.resolve(null),
    client.GET('/api/v1/organizations/{slug}/courses/teaching-exceptions/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    organization.access.capabilities.includes('catalog.manage')
      ? client.GET('/api/v1/organizations/{slug}/courses/', {
          params: {
            path: { slug },
            query: { ordering: 'title', page_size: 100, status: 'active' },
          },
          cache: 'no-store',
        })
      : Promise.resolve(null),
  ]);
  if (response.status === 403 || response.status === 404) notFound();
  if (!response.ok || !data) {
    throw new Error('No fue posible consultar las responsabilidades docentes.');
  }
  const subjects =
    subjectsResult?.response.ok && subjectsResult.data
      ? subjectsResult.data
      : [];
  const courseExceptions =
    courseExceptionsResult.response.ok && courseExceptionsResult.data
      ? courseExceptionsResult.data
      : [];
  const courses =
    coursesResult?.response.ok && coursesResult.data
      ? coursesResult.data.results
      : [];
  return {
    ...organization,
    courseExceptions,
    courses,
    responsibilities: data,
    subjects,
  };
}
