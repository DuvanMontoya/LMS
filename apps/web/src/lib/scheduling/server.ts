import 'server-only';

import { notFound } from 'next/navigation';

import type { components, operations } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

export type LiveSessionDetail = components['schemas']['LiveSessionDetail'];
type CoursePage = components['schemas']['CoursePage'];

export async function getSchedulingPage(slug: string) {
  const organization = await getOrganizationForPage(slug);
  const canCreate =
    organization.access.capabilities.includes('scheduling.create');
  let courses: components['schemas']['CourseList'][] = [];
  if (canCreate) {
    const client = await createPlatformServerClient();
    const { data, response } = await client.GET(
      '/api/v1/organizations/{slug}/courses/',
      {
        params: {
          path: { slug },
          query: { page_size: 100, status: 'active' },
        },
        cache: 'no-store',
      },
    );
    if (!response.ok || !data)
      throw new Error('No fue posible consultar los cursos.');
    courses = (data as CoursePage).results;
  }
  return { ...organization, canCreate, courses };
}

export async function getLiveSession(slug: string, sessionId: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const { data, response } = await client.GET(
    '/api/v1/organizations/{slug}/scheduling/live-sessions/{session_id}/',
    { params: { path: { slug, session_id: sessionId } }, cache: 'no-store' },
  );
  if (response.status === 403 || response.status === 404) notFound();
  if (!response.ok || !data)
    throw new Error('No fue posible consultar la clase.');
  return {
    ...organization,
    session:
      data as operations['scheduling_live_session_retrieve']['responses'][200]['content']['application/json'],
  };
}
