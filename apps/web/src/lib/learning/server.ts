import 'server-only';

import { notFound } from 'next/navigation';

import type { components, operations } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

export type MyLearning =
  operations['organizations_learning_me_list']['responses'][200]['content']['application/json'][number];
export type LearningOutline =
  operations['organizations_learning_me_enrollments_outline_retrieve']['responses'][200]['content']['application/json'];
export type LearningUnit =
  operations['organizations_learning_me_enrollments_units_retrieve']['responses'][200]['content']['application/json'];
export type LearningActivity =
  operations['organizations_learning_me_enrollments_activities_retrieve']['responses'][200]['content']['application/json'];
export type CohortPage =
  operations['learning_cohorts_list']['responses'][200]['content']['application/json'];
export type AcademicGroupPage =
  operations['learning_academic_groups_list']['responses'][200]['content']['application/json'];
export type EnrollmentPage =
  operations['learning_enrollments_list']['responses'][200]['content']['application/json'];
export type Cohort =
  operations['learning_cohorts_retrieve']['responses'][200]['content']['application/json'];
export type Enrollment =
  operations['learning_enrollments_retrieve']['responses'][200]['content']['application/json'];
export type CohortProgress =
  operations['organizations_learning_cohorts_progress_retrieve']['responses'][200]['content']['application/json'];
export type EnrollmentProgress =
  operations['organizations_learning_enrollments_progress_retrieve']['responses'][200]['content']['application/json'];
type CoursePage =
  operations['organizations_courses_list']['responses'][200]['content']['application/json'];
type ReleaseList =
  operations['organizations_courses_releases_list']['responses'][200]['content']['application/json'];
export type LearningCourseOption = {
  releases: Array<{
    createdAt: string;
    current: boolean;
    number: number;
    unitCount: number;
  }>;
  slug: string;
  title: string;
};

export type LearningCohortOption = {
  courseSlug: string;
  courseTitle: string;
  courseGroupVersion: number;
  id: string;
  name: string;
  releaseNumber: number;
};

export type LearningAcademicGroupOption = {
  academicYear: number;
  id: string;
  level: components['schemas']['AcademicGroupLevel'];
  lockVersion: number;
  name: string;
  section: string;
};

export type LearningAcademicPeriodOption = {
  endsOn: string;
  id: string;
  name: string;
  startsOn: string;
  type: components['schemas']['PeriodTypeEnum'];
};

export type LearningAdminOptions = {
  academicGroups: LearningAcademicGroupOption[];
  academicPeriods: LearningAcademicPeriodOption[];
  cohorts: LearningCohortOption[];
  courses: LearningCourseOption[];
};

type CohortQuery = NonNullable<
  operations['learning_cohorts_list']['parameters']['query']
>;
type EnrollmentQuery = NonNullable<
  operations['learning_enrollments_list']['parameters']['query']
>;

async function required<T>(
  request: Promise<{ response: Response; data?: T }>,
  message: string,
): Promise<T> {
  const { data, response } = await request;
  if (
    response.status === 400 ||
    response.status === 403 ||
    response.status === 404 ||
    response.status === 422
  ) {
    notFound();
  }
  if (!response.ok || data === undefined) throw new Error(message);
  return data;
}

export async function getMyLearning(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.roles.includes('learner')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const enrollments = (await required(
    client.GET('/api/v1/organizations/{slug}/learning/me/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar Mi aprendizaje.',
  )) as MyLearning[];
  return { ...organization, enrollments };
}

export async function getAcademicGroups(slug: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const groups = (await required(
    client.GET('/api/v1/organizations/{slug}/learning/academic-groups/', {
      params: { path: { slug }, query: { page_size: 100 } },
      cache: 'no-store',
    }),
    'No fue posible consultar los grupos académicos.',
  )) as AcademicGroupPage;
  return { ...organization, groups };
}

export async function getAcademicPeriods(slug: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const periods = await required(
    client.GET('/api/v1/organizations/{slug}/learning/academic-periods/', {
      params: { path: { slug }, query: { page_size: 100 } },
      cache: 'no-store',
    }),
    'No fue posible consultar los periodos académicos.',
  );
  return { ...organization, periods };
}

export async function getLearningOutline(slug: string, enrollmentId: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const outline = (await required(
    client.GET(
      '/api/v1/organizations/{slug}/learning/me/enrollments/{enrollment_id}/outline/',
      {
        params: { path: { slug, enrollment_id: enrollmentId } },
        cache: 'no-store',
      },
    ),
    'No fue posible consultar la ruta de aprendizaje.',
  )) as LearningOutline;
  return { ...organization, enrollmentId, outline };
}

export async function getLearningUnit(
  slug: string,
  enrollmentId: string,
  unitId: string,
) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const payload = (await required(
    client.GET(
      '/api/v1/organizations/{slug}/learning/me/enrollments/{enrollment_id}/units/{unit_id}/',
      {
        params: {
          path: { slug, enrollment_id: enrollmentId, unit_id: unitId },
        },
        cache: 'no-store',
      },
    ),
    'No fue posible consultar la unidad asignada.',
  )) as LearningUnit;
  return { ...organization, enrollmentId, payload };
}

export async function getLearningActivity(
  slug: string,
  enrollmentId: string,
  activityId: string,
) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const payload = (await required(
    client.GET(
      '/api/v1/organizations/{slug}/learning/me/enrollments/{enrollment_id}/activities/{activity_instance_id}/',
      {
        params: {
          path: {
            slug,
            enrollment_id: enrollmentId,
            activity_instance_id: activityId,
          },
        },
        cache: 'no-store',
      },
    ),
    'No fue posible consultar la actividad asignada.',
  )) as LearningActivity;
  return { ...organization, enrollmentId, payload };
}

export async function getEnrollmentForCourse(slug: string, courseSlug: string) {
  const data = await getMyLearning(slug);
  const matches = data.enrollments.filter(
    (enrollment) => enrollment.course.slug === courseSlug,
  );
  if (matches.length !== 1) notFound();
  const enrollment = matches[0];
  if (!enrollment) notFound();
  return { ...data, enrollment };
}

/**
 * Resolves an effective learner enrollment without turning a published-course
 * preview into a learner-only route. Authors and reviewers can therefore use
 * the immutable release reader, while an enrolled learner is sent to the
 * canonical learning workspace that owns progress and activity state.
 */
export async function getOptionalEnrollmentForCourse(
  slug: string,
  courseSlug: string,
) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.roles.includes('learner')) {
    return null;
  }

  const client = await createPlatformServerClient();
  const { data, response } = await client.GET(
    '/api/v1/organizations/{slug}/learning/me/',
    {
      params: { path: { slug } },
      cache: 'no-store',
    },
  );
  if (!response.ok || !data) return null;

  const matches = (data as MyLearning[]).filter(
    (enrollment) => enrollment.course.slug === courseSlug,
  );
  return matches.length === 1 ? matches[0] : null;
}

export async function getCohorts(slug: string, query: CohortQuery = {}) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('learning.cohort.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const cohorts = (await required(
    client.GET('/api/v1/organizations/{slug}/learning/cohorts/', {
      params: { path: { slug }, query },
      cache: 'no-store',
    }),
    'No fue posible consultar las secciones.',
  )) as CohortPage;
  return { ...organization, cohorts };
}

export async function getEnrollments(
  slug: string,
  query: EnrollmentQuery = {},
) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('learning.enrollment.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const canManage = organization.access.capabilities.includes(
    'learning.enrollment.manage',
  );
  const [enrollments, options] = await Promise.all([
    required(
      client.GET('/api/v1/organizations/{slug}/learning/enrollments/', {
        params: { path: { slug }, query },
        cache: 'no-store',
      }),
      'No fue posible consultar las matrículas.',
    ) as Promise<EnrollmentPage>,
    canManage
      ? getLearningAdminOptionsFromClient(client, slug)
      : Promise.resolve(emptyAdminOptions()),
  ]);
  return { ...organization, enrollments, options };
}

export async function getCohort(slug: string, cohortId: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('learning.cohort.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const path = { slug, cohort_id: cohortId };
  const canManage = organization.access.capabilities.includes(
    'learning.cohort.manage',
  );
  const [cohort, progress, enrollments, options] = await Promise.all([
    required(
      client.GET('/api/v1/organizations/{slug}/learning/cohorts/{cohort_id}/', {
        params: { path },
        cache: 'no-store',
      }),
      'No fue posible consultar la sección.',
    ) as Promise<Cohort>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/learning/cohorts/{cohort_id}/progress/',
        {
          params: { path, query: { page_size: 100 } },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar el progreso de la sección.',
    ) as Promise<CohortProgress>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/learning/cohorts/{cohort_id}/enrollments/',
        {
          params: { path, query: { page_size: 100 } },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar las matrículas de la sección.',
    ),
    canManage
      ? getLearningAdminOptionsFromClient(client, slug)
      : Promise.resolve(emptyAdminOptions()),
  ]);
  return { ...organization, cohort, enrollments, options, progress };
}

export async function getEnrollment(slug: string, enrollmentId: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('learning.enrollment.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const path = { slug, enrollment_id: enrollmentId };
  const canManage = organization.access.capabilities.includes(
    'learning.enrollment.manage',
  );
  const [enrollment, progress, options] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{slug}/learning/enrollments/{enrollment_id}/',
        { params: { path }, cache: 'no-store' },
      ),
      'No fue posible consultar la matrícula.',
    ) as Promise<Enrollment>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/learning/enrollments/{enrollment_id}/progress/',
        { params: { path }, cache: 'no-store' },
      ),
      'No fue posible consultar el progreso.',
    ) as Promise<EnrollmentProgress>,
    canManage
      ? getLearningAdminOptionsFromClient(client, slug)
      : Promise.resolve(emptyAdminOptions()),
  ]);
  return { ...organization, enrollment, options, progress };
}

export async function getLearningAdminOptions(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (
    !organization.access.capabilities.includes('learning.cohort.manage') &&
    !organization.access.capabilities.includes('learning.enrollment.manage')
  ) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const options = await getLearningAdminOptionsFromClient(client, slug);
  return { ...organization, options };
}

type PlatformServerClient = Awaited<
  ReturnType<typeof createPlatformServerClient>
>;

async function getLearningAdminOptionsFromClient(
  client: PlatformServerClient,
  slug: string,
): Promise<LearningAdminOptions> {
  const [courses, cohorts, academicGroups, academicPeriods] = await Promise.all(
    [
      required(
        client.GET('/api/v1/organizations/{slug}/courses/', {
          params: {
            path: { slug },
            query: { ordering: 'title', page_size: 100, status: 'active' },
          },
          cache: 'no-store',
        }),
        'No fue posible consultar los cursos disponibles.',
      ) as Promise<CoursePage>,
      required(
        client.GET('/api/v1/organizations/{slug}/learning/cohorts/', {
          params: {
            path: { slug },
            query: { ordering: 'name', page_size: 100, status: 'active' },
          },
          cache: 'no-store',
        }),
        'No fue posible consultar las secciones disponibles.',
      ) as Promise<CohortPage>,
      required(
        client.GET('/api/v1/organizations/{slug}/learning/academic-groups/', {
          params: { path: { slug }, query: { page_size: 100 } },
          cache: 'no-store',
        }),
        'No fue posible consultar los grupos académicos disponibles.',
      ) as Promise<AcademicGroupPage>,
      required(
        client.GET('/api/v1/organizations/{slug}/learning/academic-periods/', {
          params: { path: { slug }, query: { page_size: 100 } },
          cache: 'no-store',
        }),
        'No fue posible consultar los periodos académicos disponibles.',
      ) as Promise<
        operations['learning_academic_periods_list']['responses'][200]['content']['application/json']
      >,
    ],
  );

  const courseOptions = await Promise.all(
    courses.results.map(async (course) => {
      const { data, response } = await client.GET(
        '/api/v1/organizations/{slug}/courses/{course_slug}/releases/',
        {
          params: {
            path: { course_slug: course.slug, slug },
          },
          cache: 'no-store',
        },
      );
      const releases =
        response.ok && data
          ? ([...data] as ReleaseList).sort(
              (left, right) =>
                Number(right.is_current) - Number(left.is_current) ||
                right.number - left.number,
            )
          : [];
      return {
        releases: releases.map((release) => ({
          createdAt: release.created_at,
          current: release.is_current,
          number: release.number,
          unitCount: release.unit_count,
        })),
        slug: course.slug,
        title: course.title,
      };
    }),
  );

  return {
    academicGroups: academicGroups.results
      .filter((group) => group.status === 'active')
      .map((group) => ({
        academicYear: group.academic_year,
        id: group.id,
        level: group.level,
        lockVersion: group.lock_version,
        name: group.name,
        section: group.section ?? '',
      })),
    academicPeriods: academicPeriods.results
      .filter((period) => period.status === 'active')
      .map((period) => ({
        endsOn: period.ends_on,
        id: period.id,
        name: period.name,
        startsOn: period.starts_on,
        type: period.period_type,
      })),
    cohorts: cohorts.results.map((cohort) => ({
      courseSlug: cohort.course_slug,
      courseTitle: cohort.course_title,
      courseGroupVersion: cohort.course_group_version,
      id: cohort.id,
      name: cohort.name,
      releaseNumber: cohort.release_number,
    })),
    courses: courseOptions.filter((course) => course.releases.length > 0),
  };
}

function emptyAdminOptions(): LearningAdminOptions {
  return {
    academicGroups: [],
    academicPeriods: [],
    cohorts: [],
    courses: [],
  };
}
