import 'server-only';

import { notFound } from 'next/navigation';

import type { components, operations } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

export type AssessmentPage =
  operations['assessments_list']['responses'][200]['content']['application/json'];
export type AssessmentSummary = components['schemas']['Assessment'];
export type AssessmentRevision = components['schemas']['AssessmentRevision'];
export type AssessmentOutline = components['schemas']['AssessmentOutline'];
export type AssessmentReadiness = components['schemas']['AssessmentReadiness'];
export type AssessmentVersion = components['schemas']['AssessmentVersion'];
export type QuestionBankPage =
  operations['assessment_question_banks_list']['responses'][200]['content']['application/json'];
export type QuestionPage =
  operations['assessment_questions_list']['responses'][200]['content']['application/json'];
export type QuestionVersion = components['schemas']['QuestionVersion'];
export type AssessmentDeliveryPage =
  operations['assessment_deliveries_list']['responses'][200]['content']['application/json'];
export type LearnerDelivery = components['schemas']['LearnerDelivery'];
export type AssessmentAttempt = components['schemas']['Attempt'];
export type AssessmentResult = components['schemas']['AttemptResult'];
export type PendingManual = components['schemas']['PendingManual'];
export type LearningObjective = components['schemas']['Objective'];
type EnrollmentPage =
  operations['learning_enrollments_list']['responses'][200]['content']['application/json'];

async function required<T>(
  request: Promise<{ data?: T; response: Response }>,
  message: string,
): Promise<T> {
  const { data, response } = await request;
  if (response.status === 403 || response.status === 404) notFound();
  if (!response.ok || data === undefined) throw new Error(message);
  return data;
}

export async function getAssessments(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.authoring.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const assessments = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar las evaluaciones.',
  )) as AssessmentPage;
  return { ...organization, assessments };
}

export async function getAssessmentCreationContext(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (
    !organization.access.capabilities.includes('assessment.authoring.manage')
  ) {
    notFound();
  }
  return organization;
}

export async function getQuestionBanks(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.bank.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const banks = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/question-banks/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar los bancos.',
  )) as QuestionBankPage;
  return { ...organization, banks };
}

export async function getQuestionBank(slug: string, bankId: string) {
  const data = await getQuestionBanks(slug);
  const bank = data.banks.results.find((item) => item.id === bankId);
  if (!bank) notFound();
  const client = await createPlatformServerClient();
  const questions = (await required(
    client.GET(
      '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/',
      { params: { path: { bank_id: bankId, slug } }, cache: 'no-store' },
    ),
    'No fue posible consultar las preguntas.',
  )) as QuestionPage;
  return { ...data, bank, questions };
}

export async function getQuestionRevision(
  slug: string,
  bankId: string,
  questionId: string,
  revisionId: string,
) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.question.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const revision = (await required(
    client.GET(
      '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/{question_id}/revisions/{revision_id}/',
      {
        params: {
          path: {
            bank_id: bankId,
            question_id: questionId,
            revision_id: revisionId,
            slug,
          },
        },
        cache: 'no-store',
      },
    ),
    'No fue posible consultar la revisión de pregunta.',
  )) as components['schemas']['QuestionRevision'];
  return { ...organization, bankId, questionId, revision };
}

async function objectiveOptions(
  client: Awaited<ReturnType<typeof createPlatformServerClient>>,
  slug: string,
) {
  return (await required(
    client.GET('/api/v1/organizations/{slug}/catalog/learning-objectives/', {
      params: {
        path: { slug },
        query: { ordering: 'code', status: 'active' },
      },
      cache: 'no-store',
    }),
    'No fue posible consultar los objetivos.',
  )) as LearningObjective[];
}

async function approvedQuestionVersions(
  client: Awaited<ReturnType<typeof createPlatformServerClient>>,
  slug: string,
) {
  const banks = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/question-banks/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar los bancos.',
  )) as QuestionBankPage;
  const groups = await Promise.all(
    banks.results.map(async (bank) => {
      const questions = (await required(
        client.GET(
          '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/',
          {
            params: { path: { bank_id: bank.id, slug } },
            cache: 'no-store',
          },
        ),
        'No fue posible consultar las preguntas.',
      )) as QuestionPage;
      const versions = await Promise.all(
        questions.results.map(async (question) => {
          const rows = (await required(
            client.GET(
              '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/{question_id}/versions/',
              {
                params: {
                  path: {
                    bank_id: bank.id,
                    question_id: question.id,
                    slug,
                  },
                },
                cache: 'no-store',
              },
            ),
            'No fue posible consultar las versiones de pregunta.',
          )) as QuestionVersion[];
          return rows.map((version) => ({
            bankName: bank.name,
            code: question.code,
            id: version.id,
            number: version.number,
            public: version.public,
            type: version.type,
          }));
        }),
      );
      return versions.flat();
    }),
  );
  return groups.flat();
}

export async function getAssessmentWorkspace(
  slug: string,
  assessmentSlug: string,
) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.authoring.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const assessment = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/{assessment_slug}/', {
      params: { path: { assessment_slug: assessmentSlug, slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar la evaluación.',
  )) as AssessmentSummary;
  if (!assessment.latest_revision_id) notFound();
  const path = {
    assessment_slug: assessmentSlug,
    revision_id: assessment.latest_revision_id,
    slug,
  };
  const [outline, readiness, versions, objectives, questions] =
    await Promise.all([
      required(
        client.GET(
          '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/outline/',
          { params: { path }, cache: 'no-store' },
        ),
        'No fue posible consultar la composición.',
      ) as Promise<AssessmentOutline>,
      required(
        client.GET(
          '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/readiness/',
          { params: { path }, cache: 'no-store' },
        ),
        'No fue posible consultar la preparación.',
      ) as Promise<AssessmentReadiness>,
      required(
        client.GET(
          '/api/v1/organizations/{slug}/assessments/{assessment_slug}/versions/',
          {
            params: { path: { assessment_slug: assessmentSlug, slug } },
            cache: 'no-store',
          },
        ),
        'No fue posible consultar el historial.',
      ) as Promise<AssessmentVersion[]>,
      objectiveOptions(client, slug),
      approvedQuestionVersions(client, slug),
    ]);
  return {
    ...organization,
    assessment,
    objectives,
    outline,
    questions,
    readiness,
    versions,
  };
}

export async function getAssessmentDeliveries(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.delivery.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const canManage = organization.access.capabilities.includes(
    'assessment.delivery.manage',
  );
  const deliveries = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/deliveries/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar las entregas.',
  )) as AssessmentDeliveryPage;
  if (!canManage) {
    return {
      ...organization,
      canManage,
      deliveries,
      enrollments: [],
      releaseOptions: [],
      versions: [],
    };
  }
  const [assessments, enrollments] = await Promise.all([
    required(
      client.GET('/api/v1/organizations/{slug}/assessments/', {
        params: { path: { slug } },
        cache: 'no-store',
      }),
      'No fue posible consultar las evaluaciones.',
    ) as Promise<AssessmentPage>,
    required(
      client.GET('/api/v1/organizations/{slug}/learning/enrollments/', {
        params: { path: { slug }, query: { page_size: 100 } },
        cache: 'no-store',
      }),
      'No fue posible consultar las matrículas.',
    ) as Promise<EnrollmentPage>,
  ]);
  const versionGroups = await Promise.all(
    assessments.results.map(async (assessment) => {
      const versions = (await required(
        client.GET(
          '/api/v1/organizations/{slug}/assessments/{assessment_slug}/versions/',
          {
            params: {
              path: { assessment_slug: assessment.slug, slug },
            },
            cache: 'no-store',
          },
        ),
        'No fue posible consultar las versiones.',
      )) as AssessmentVersion[];
      return versions;
    }),
  );
  const releaseById = new Map<
    string,
    {
      courseSlug: string;
      courseTitle: string;
      id: string;
      number: number;
    }
  >();
  for (const enrollment of enrollments.results) {
    if (enrollment.current_release_id) {
      releaseById.set(enrollment.current_release_id, {
        courseSlug: enrollment.course_slug,
        courseTitle: enrollment.course_title,
        id: enrollment.current_release_id,
        number: enrollment.release_number,
      });
    }
  }
  const releaseOptions = await Promise.all(
    [...releaseById.values()].map(async (release) => {
      const { data, response } = await client.GET(
        '/api/v1/organizations/{slug}/courses/{course_slug}/releases/{release_number}/outline/',
        {
          params: {
            path: {
              course_slug: release.courseSlug,
              release_number: release.number,
              slug,
            },
          },
          cache: 'no-store',
        },
      );
      return {
        ...release,
        units:
          response.ok && data
            ? data.modules.flatMap((module) =>
                module.units.map((unit) => ({
                  id: unit.id,
                  title: unit.title,
                })),
              )
            : [],
      };
    }),
  );
  return {
    ...organization,
    canManage,
    deliveries,
    enrollments: enrollments.results,
    releaseOptions,
    versions: versionGroups.flat(),
  };
}

export async function getMyAssessmentDeliveries(slug: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const deliveries = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/my-deliveries/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar las evaluaciones asignadas.',
  )) as LearnerDelivery[];
  return { ...organization, deliveries };
}

export async function getAssessmentAttempt(slug: string, attemptId: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const attempt = (await required(
    client.GET(
      '/api/v1/organizations/{slug}/assessments/attempts/{attempt_id}/',
      {
        params: { path: { attempt_id: attemptId, slug } },
        cache: 'no-store',
      },
    ),
    'No fue posible consultar el intento.',
  )) as AssessmentAttempt;
  return { ...organization, attempt };
}

export async function getAssessmentResult(slug: string, attemptId: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const result = (await required(
    client.GET(
      '/api/v1/organizations/{slug}/assessments/attempts/{attempt_id}/result/',
      {
        params: { path: { attempt_id: attemptId, slug } },
        cache: 'no-store',
      },
    ),
    'No fue posible consultar el resultado.',
  )) as AssessmentResult;
  return { ...organization, result };
}

export async function getAssessmentResults(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.results.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const results = await required(
    client.GET('/api/v1/organizations/{slug}/assessments/results/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar los resultados.',
  );
  return { ...organization, results };
}

export async function getPendingManualGrades(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.grading.manage')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const responses = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/manual-grading/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar la cola manual.',
  )) as PendingManual[];
  return { ...organization, responses };
}
