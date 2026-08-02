import 'server-only';

import { notFound } from 'next/navigation';

import type { operations } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

type CoursePage =
  operations['organizations_courses_list']['responses'][200]['content']['application/json'];
type Course =
  operations['organizations_courses_retrieve']['responses'][200]['content']['application/json'];
type RevisionList =
  operations['organizations_courses_revisions_list']['responses'][200]['content']['application/json'];
type Outline =
  operations['organizations_courses_revisions_outline_retrieve']['responses'][200]['content']['application/json'];
type TransitionList =
  operations['organizations_courses_revisions_transitions_list']['responses'][200]['content']['application/json'];
type Readiness =
  operations['organizations_courses_revisions_readiness_retrieve']['responses'][200]['content']['application/json'];
type SubjectList =
  operations['organizations_catalog_subjects_list']['responses'][200]['content']['application/json'];
type ObjectiveList =
  operations['organizations_catalog_learning_objectives_list']['responses'][200]['content']['application/json'];
type TopicList =
  operations['organizations_catalog_subjects_topics_list']['responses'][200]['content']['application/json'];

async function required<T>(
  request: Promise<{ response: Response; data?: T }>,
  message: string,
): Promise<T> {
  const { data, response } = await request;
  if (response.status === 404 || response.status === 403) notFound();
  if (!response.ok || data === undefined) throw new Error(message);
  return data;
}

function canSeeCourses(capabilities: readonly string[]) {
  return (
    capabilities.includes('course.authoring.view') ||
    capabilities.includes('course.approved.view')
  );
}

export async function getCoursesForPage(
  slug: string,
  query: {
    authoring_status?: string;
    ordering?: string;
    page?: number;
    search?: string;
    status?: string;
    subject?: string;
  },
) {
  const organization = await getOrganizationForPage(slug);
  if (!canSeeCourses(organization.access.capabilities)) notFound();
  const client = await createPlatformServerClient();
  const courses = (await required(
    client.GET('/api/v1/organizations/{slug}/courses/', {
      params: { path: { slug }, query },
    }),
    'No fue posible consultar los cursos.',
  )) as CoursePage;
  return { ...organization, courses };
}

export async function getCourseCreationContext(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('course.authoring.manage'))
    notFound();
  const client = await createPlatformServerClient();
  const [subjects, objectives] = await Promise.all([
    required(
      client.GET('/api/v1/organizations/{slug}/catalog/subjects/', {
        params: { path: { slug }, query: { status: 'active' } },
      }),
      'No fue posible consultar las asignaturas.',
    ) as Promise<SubjectList>,
    required(
      client.GET('/api/v1/organizations/{slug}/catalog/learning-objectives/', {
        params: { path: { slug }, query: { status: 'active' } },
      }),
      'No fue posible consultar los objetivos.',
    ) as Promise<ObjectiveList>,
  ]);
  return { ...organization, objectives, subjects };
}

export async function getCourseWorkspace(slug: string, courseSlug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!canSeeCourses(organization.access.capabilities)) notFound();
  const canAuthor = organization.access.capabilities.includes(
    'course.authoring.view',
  );
  const client = await createPlatformServerClient();
  const [course, revisions, subjects, objectives] = await Promise.all([
    required(
      client.GET('/api/v1/organizations/{slug}/courses/{course_slug}/', {
        params: { path: { slug, course_slug: courseSlug } },
      }),
      'No fue posible consultar el curso.',
    ) as Promise<Course>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/',
        { params: { path: { slug, course_slug: courseSlug } } },
      ),
      'No fue posible consultar las revisiones.',
    ) as Promise<RevisionList>,
    canAuthor
      ? (required(
          client.GET('/api/v1/organizations/{slug}/catalog/subjects/', {
            params: { path: { slug } },
          }),
          'No fue posible consultar las asignaturas.',
        ) as Promise<SubjectList>)
      : Promise.resolve([] as SubjectList),
    canAuthor
      ? (required(
          client.GET(
            '/api/v1/organizations/{slug}/catalog/learning-objectives/',
            { params: { path: { slug } } },
          ),
          'No fue posible consultar los objetivos.',
        ) as Promise<ObjectiveList>)
      : Promise.resolve([] as ObjectiveList),
  ]);
  const revision = [...revisions].sort(
    (left, right) => right.number - left.number,
  )[0];
  if (!revision) notFound();
  const path = { slug, course_slug: courseSlug, revision_id: revision.id };
  const [outline, transitions, readiness] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/outline/',
        { params: { path } },
      ),
      'No fue posible consultar la estructura.',
    ) as Promise<Outline>,
    canAuthor
      ? (required(
          client.GET(
            '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/transitions/',
            { params: { path } },
          ),
          'No fue posible consultar el historial.',
        ) as Promise<TransitionList>)
      : Promise.resolve([] as TransitionList),
    canAuthor
      ? (required(
          client.GET(
            '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/readiness/',
            { params: { path } },
          ),
          'No fue posible validar la revisión.',
        ) as Promise<Readiness>)
      : Promise.resolve(null),
  ]);
  const topicLists = await Promise.all(
    subjects.map(
      (subject) =>
        required(
          client.GET(
            '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/topics/',
            { params: { path: { slug, subject_id: subject.id } } },
          ),
          'No fue posible consultar los temas.',
        ) as Promise<TopicList>,
    ),
  );
  return {
    ...organization,
    canAuthor,
    course,
    objectives,
    outline,
    readiness,
    revision,
    revisions,
    subjects,
    topics: topicLists.flat(),
    transitions,
  };
}
