import 'server-only';

import { notFound } from 'next/navigation';

import type { components, operations } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

export type LiveSessionDetail = components['schemas']['LiveSessionDetail'];
export type LiveClassActivityBinding =
  components['schemas']['LiveClassActivityBinding'];

export async function getLiveClassActivityBindings(
  slug: string,
  activityIds: string[],
) {
  const client = await createPlatformServerClient();
  const bindings = await Promise.all(
    activityIds.map(async (activityId) => {
      const { data, response } = await client.GET(
        '/api/v1/organizations/{slug}/scheduling/course-activities/{activity_id}/binding/',
        {
          params: { path: { activity_id: activityId, slug } },
          cache: 'no-store',
        },
      );
      if (response.status === 404 || response.status === 405) return null;
      if (response.status === 403) notFound();
      if (!response.ok || !data)
        throw new Error('No fue posible consultar la política LiveKit.');
      return data;
    }),
  );
  return bindings.filter(
    (binding): binding is LiveClassActivityBinding => binding !== null,
  );
}

export async function getSchedulingPage(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('scheduling.view')) {
    notFound();
  }
  const canCreate =
    organization.access.capabilities.includes('scheduling.create');
  let courseActivities: components['schemas']['CourseGroupActivityRead'][] = [];
  let participantOptions: components['schemas']['ParticipantOption'][] = [];
  if (canCreate) {
    const client = await createPlatformServerClient();
    const [activityRequest, participantRequest] = await Promise.all([
      client.GET(
        '/api/v1/organizations/{slug}/learning/course-group-activities/',
        {
          params: {
            path: { slug },
            query: { activity_type: 'live_class' },
          },
          cache: 'no-store',
        },
      ),
      client.GET(
        '/api/v1/organizations/{slug}/scheduling/participant-options/',
        { params: { path: { slug } }, cache: 'no-store' },
      ),
    ]);
    if (
      activityRequest.response.status === 403 ||
      activityRequest.response.status === 404
    ) {
      notFound();
    }
    if (!activityRequest.response.ok || !activityRequest.data)
      throw new Error(
        'No fue posible consultar las actividades de tus grupos.',
      );
    if (
      participantRequest.response.status === 403 ||
      participantRequest.response.status === 404
    ) {
      notFound();
    }
    if (!participantRequest.response.ok || !participantRequest.data)
      throw new Error('No fue posible consultar los participantes.');
    courseActivities = activityRequest.data;
    participantOptions = participantRequest.data;
  }
  return { ...organization, canCreate, courseActivities, participantOptions };
}

export async function getLiveSession(slug: string, sessionId: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('scheduling.view')) {
    notFound();
  }
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

export async function getLiveSessions(
  slug: string,
  options: { courseSlug?: string; scope?: 'all' | 'past' | 'upcoming' } = {},
) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('scheduling.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const { data, response } = await client.GET(
    '/api/v1/organizations/{slug}/scheduling/live-sessions/',
    {
      params: {
        path: { slug },
        query: {
          course_slug: options.courseSlug ?? '',
          scope: options.scope ?? 'upcoming',
        },
      },
      cache: 'no-store',
    },
  );
  if (response.status === 403 || response.status === 404) notFound();
  if (!response.ok || !data)
    throw new Error('No fue posible consultar las clases en vivo.');
  return { ...organization, sessions: data };
}
