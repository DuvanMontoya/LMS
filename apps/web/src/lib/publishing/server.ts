import 'server-only';

import { notFound } from 'next/navigation';

import type { operations } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';
import {
  requirePublishedCourse,
  requirePublishedObjectives,
  requirePublishedSubjects,
  requirePublishedUnit,
} from '@/lib/publishing/snapshot';

type PublicationState =
  operations['organizations_courses_publication_retrieve']['responses'][200]['content']['application/json'];
type ReleaseList =
  operations['organizations_courses_releases_list']['responses'][200]['content']['application/json'];
type ReleaseDetail =
  operations['organizations_courses_releases_retrieve']['responses'][200]['content']['application/json'];
type ReleaseOutline =
  operations['organizations_courses_releases_outline_retrieve']['responses'][200]['content']['application/json'];
type Verification =
  operations['organizations_courses_releases_verify_retrieve']['responses'][200]['content']['application/json'];
type Readiness =
  operations['organizations_courses_revisions_readiness_retrieve']['responses'][200]['content']['application/json'];
type LibraryList =
  operations['organizations_library_courses_list']['responses'][200]['content']['application/json'];
type LibraryDetail =
  operations['organizations_library_courses_retrieve']['responses'][200]['content']['application/json'];
type ReleaseUnit =
  operations['organizations_library_courses_units_retrieve']['responses'][200]['content']['application/json'];

async function required<T>(
  request: Promise<{ response: Response; data?: T }>,
  message: string,
): Promise<T> {
  const { data, response } = await request;
  if (response.status === 403 || response.status === 404) notFound();
  if (!response.ok || data === undefined) throw new Error(message);
  return data;
}

export async function getPublicationWorkspace(
  slug: string,
  courseSlug: string,
) {
  const organization = await getOrganizationForPage(slug);
  if (
    !organization.access.capabilities.includes('course.release.history.view')
  ) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const path = { slug, course_slug: courseSlug };
  const state = (await required(
    client.GET(
      '/api/v1/organizations/{slug}/courses/{course_slug}/publication/',
      { params: { path } },
    ),
    'No fue posible consultar la publicación.',
  )) as PublicationState;
  const releases = state.has_publication
    ? ((await required(
        client.GET(
          '/api/v1/organizations/{slug}/courses/{course_slug}/releases/',
          { params: { path } },
        ),
        'No fue posible consultar el historial de releases.',
      )) as ReleaseList)
    : [];
  const readiness = state.approved_revision_id
    ? ((await required(
        client.GET(
          '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/readiness/',
          {
            params: {
              path: {
                ...path,
                revision_id: state.approved_revision_id,
              },
            },
          },
        ),
        'No fue posible validar la revisión aprobada.',
      )) as Readiness)
    : null;
  const verification = state.current_release_number
    ? ((await required(
        client.GET(
          '/api/v1/organizations/{slug}/courses/{course_slug}/releases/{release_number}/verify/',
          {
            params: {
              path: {
                ...path,
                release_number: state.current_release_number,
              },
            },
          },
        ),
        'No fue posible verificar el release.',
      )) as Verification)
    : null;
  return { ...organization, readiness, releases, state, verification };
}

export async function getHistoricalRelease(
  slug: string,
  courseSlug: string,
  releaseNumber: number,
) {
  const organization = await getOrganizationForPage(slug);
  if (
    !organization.access.capabilities.includes('course.release.history.view')
  ) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const path = {
    slug,
    course_slug: courseSlug,
    release_number: releaseNumber,
  };
  const [release, outline, verification, state] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{slug}/courses/{course_slug}/releases/{release_number}/',
        { params: { path } },
      ),
      'No fue posible consultar el release.',
    ) as Promise<ReleaseDetail>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/courses/{course_slug}/releases/{release_number}/outline/',
        { params: { path } },
      ),
      'No fue posible consultar el outline.',
    ) as Promise<ReleaseOutline>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/courses/{course_slug}/releases/{release_number}/verify/',
        { params: { path } },
      ),
      'No fue posible verificar el release.',
    ) as Promise<Verification>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/courses/{course_slug}/publication/',
        {
          params: {
            path: { slug, course_slug: courseSlug },
          },
        },
      ),
      'No fue posible consultar la versión de publicación.',
    ) as Promise<PublicationState>,
  ]);
  return {
    ...organization,
    outline,
    release,
    publishedCourse: requirePublishedCourse(release.course),
    state,
    verification,
  };
}

export async function getLibrary(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('course.published.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const courses = (await required(
    client.GET('/api/v1/organizations/{slug}/library/courses/', {
      params: { path: { slug } },
    }),
    'No fue posible consultar la biblioteca.',
  )) as LibraryList;
  return { ...organization, courses };
}

export async function getLibraryCourse(slug: string, courseSlug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('course.published.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const course = (await required(
    client.GET('/api/v1/organizations/{slug}/library/courses/{course_slug}/', {
      params: { path: { slug, course_slug: courseSlug } },
    }),
    'No fue posible consultar el curso publicado.',
  )) as LibraryDetail;
  return {
    ...organization,
    course,
    subjects: requirePublishedSubjects(course.subjects),
    objectives: requirePublishedObjectives(course.learning_objectives),
  };
}

export async function getLibraryUnit(
  slug: string,
  courseSlug: string,
  unitId: string,
) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('course.published.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const [payload, libraryCourse] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{slug}/library/courses/{course_slug}/units/{unit_id}/',
        {
          params: {
            path: { slug, course_slug: courseSlug, unit_id: unitId },
          },
        },
      ),
      'No fue posible consultar la unidad publicada.',
    ) as Promise<ReleaseUnit>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/library/courses/{course_slug}/',
        { params: { path: { slug, course_slug: courseSlug } } },
      ),
      'No fue posible consultar el temario publicado.',
    ) as Promise<LibraryDetail>,
  ]);
  return {
    ...organization,
    outline: libraryCourse.outline,
    payload,
    course: requirePublishedCourse(payload.course),
    unit: requirePublishedUnit(payload.unit),
  };
}
