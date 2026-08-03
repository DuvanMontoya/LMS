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
export type AssessmentPool = components['schemas']['AssessmentPool'];
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
export type CatalogSubject = components['schemas']['Subject'];
export type RegradeJob = components['schemas']['RegradeJob'];
export type RegradeJobAttempt = components['schemas']['RegradeJobAttempt'];
export type Gradebook = components['schemas']['Gradebook'];
export type GradebookEntry = components['schemas']['GradebookEntry'];
export type GradebookSummary = components['schemas']['GradebookSummary'];
export type GradebookStudentPayload =
  components['schemas']['GradebookStudentPayload'];
export type AnalyticsSnapshot = components['schemas']['AnalyticsSnapshot'];
export type GradingRevision = components['schemas']['GradingRevision'];
type EnrollmentPage =
  operations['learning_enrollments_list']['responses'][200]['content']['application/json'];
type CohortPage =
  operations['learning_cohorts_list']['responses'][200]['content']['application/json'];

async function required<T>(
  request: Promise<{ data?: T; response: Response }>,
  message: string,
): Promise<T> {
  const { data, response } = await request;
  if (response.status === 403 || response.status === 404) notFound();
  if (!response.ok || data === undefined) throw new Error(message);
  return data;
}

async function advancedAssessmentOptions(
  client: Awaited<ReturnType<typeof createPlatformServerClient>>,
  slug: string,
) {
  const deliveries = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/deliveries/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar las versiones entregadas.',
  )) as AssessmentDeliveryPage;
  const versions = [
    ...new Map(
      deliveries.results.map((delivery) => [
        delivery.assessment_version_id,
        {
          deliveries: [] as Array<{ id: string; label: string }>,
          id: delivery.assessment_version_id,
          number: delivery.assessment_version_number,
          title: delivery.assessment_title,
        },
      ]),
    ).values(),
  ];
  for (const version of versions) {
    version.deliveries = deliveries.results
      .filter((delivery) => delivery.assessment_version_id === version.id)
      .map((delivery) => ({
        id: delivery.id,
        label: delivery.name,
      }));
  }
  return Promise.all(
    versions.map(async (version) => {
      const revisions = (await required(
        client.GET(
          '/api/v1/organizations/{slug}/assessments/scoring-policies/{version_id}/revisions/',
          {
            params: { path: { slug, version_id: version.id } },
            cache: 'no-store',
          },
        ),
        'No fue posible consultar las revisiones de calificación.',
      )) as GradingRevision[];
      return {
        ...version,
        label: `${version.title} · versión ${version.number}`,
        revisions: revisions.map((revision) => ({
          id: revision.id,
          label:
            revision.source === 'correction'
              ? `Revisión ${revision.number} · corrección: ${revision.reason}`
              : `Revisión ${revision.number} · política original`,
          number: revision.number,
        })),
      };
    }),
  );
}

type AnalyticsAssessmentOption = {
  id: string;
  label: string;
  number: number;
  title: string;
};

async function analyticsAssessmentOptions(
  client: Awaited<ReturnType<typeof createPlatformServerClient>>,
  slug: string,
): Promise<AnalyticsAssessmentOption[]> {
  const deliveries = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/deliveries/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar las versiones entregadas.',
  )) as AssessmentDeliveryPage;
  return [
    ...new Map(
      deliveries.results.map((delivery) => [
        delivery.assessment_version_id,
        {
          id: delivery.assessment_version_id,
          label: `${delivery.assessment_title} · versión ${delivery.assessment_version_number}`,
          number: delivery.assessment_version_number,
          title: delivery.assessment_title,
        },
      ]),
    ).values(),
  ];
}

async function analyticsRevisionOptions(
  client: Awaited<ReturnType<typeof createPlatformServerClient>>,
  slug: string,
  versionId: string,
) {
  const { data, response } = await client.GET(
    '/api/v1/organizations/{slug}/assessments/scoring-policies/{version_id}/revisions/',
    {
      params: { path: { slug, version_id: versionId } },
      cache: 'no-store',
    },
  );
  if (!response.ok || !data) return [];
  return (data as GradingRevision[]).map((revision) => ({
    id: revision.id,
    label:
      revision.source === 'correction'
        ? `Revisión ${revision.number} · corrección: ${revision.reason}`
        : `Revisión ${revision.number} · política original`,
    number: revision.number,
  }));
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

export async function getApprovedAssessmentVersionOptions(slug: string) {
  const data = await getAssessments(slug);
  const client = await createPlatformServerClient();
  const options = await Promise.all(
    data.assessments.results.map(async (assessment) => {
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
        'No fue posible consultar las versiones aprobadas.',
      )) as AssessmentVersion[];
      return versions.map((version) => {
        const snapshot = version.public_snapshot as {
          objectives?: Array<{ id?: string }>;
        };
        return {
          attemptLimit: version.attempt_limit,
          description: version.description,
          durationMinutes: version.time_limit_minutes,
          id: version.id,
          label: `${version.title} · versión ${version.number}`,
          objectiveIds: (snapshot.objectives ?? [])
            .map((objective) => objective.id)
            .filter((id): id is string => Boolean(id)),
          passBasisPoints: version.pass_basis_points,
          title: version.title,
        };
      });
    }),
  );
  return options.flat();
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

export async function getQuestionBankCreationContext(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.bank.manage')) {
    notFound();
  }
  return organization;
}

export async function getQuestionBank(slug: string, bankId: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.bank.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const [bank, questions] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/',
        {
          params: { path: { bank_id: bankId, slug } },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar el banco.',
    ) as Promise<components['schemas']['QuestionBank']>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/',
        {
          params: {
            path: { bank_id: bankId, slug },
            query: { page_size: 100 },
          },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar las preguntas.',
    ) as Promise<QuestionPage>,
  ]);
  return { ...organization, bank, questions };
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
  const [question, revision] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/{question_id}/',
        {
          params: {
            path: { bank_id: bankId, question_id: questionId, slug },
          },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar la pregunta.',
    ) as Promise<components['schemas']['Question']>,
    required(
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
    ) as Promise<components['schemas']['QuestionRevision']>,
  ]);
  return { ...organization, bankId, question, questionId, revision };
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
  const rows = await required(
    client.GET(
      '/api/v1/organizations/{slug}/assessments/approved-question-version-options/',
      { params: { path: { slug } }, cache: 'no-store' },
    ),
    'No fue posible consultar las preguntas aprobadas.',
  );
  return rows.map((row) => ({
    bankName: row.bank_name,
    code: row.code,
    id: row.id,
    number: row.number,
    public: row.public,
    type: row.type,
  }));
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
  const [outline, readiness, versions, objectives, subjects, questions, pools] =
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
      required(
        client.GET('/api/v1/organizations/{slug}/catalog/subjects/', {
          params: {
            path: { slug },
            query: { ordering: 'name', status: 'active' },
          },
          cache: 'no-store',
        }),
        'No fue posible consultar las asignaturas del ámbito curricular.',
      ) as Promise<CatalogSubject[]>,
      approvedQuestionVersions(client, slug),
      required(
        client.GET(
          '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/pools/',
          { params: { path }, cache: 'no-store' },
        ),
        'No fue posible consultar los pools.',
      ) as Promise<AssessmentPool[]>,
    ]);
  return {
    ...organization,
    assessment,
    objectives,
    outline,
    pools,
    questions,
    readiness,
    subjects,
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
  const [versions, enrollments] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{slug}/assessments/approved-version-options/',
        {
          params: { path: { slug } },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar las evaluaciones aprobadas.',
    ) as Promise<AssessmentVersion[]>,
    required(
      client.GET('/api/v1/organizations/{slug}/learning/enrollments/', {
        params: { path: { slug }, query: { page_size: 100 } },
        cache: 'no-store',
      }),
      'No fue posible consultar las matrículas.',
    ) as Promise<EnrollmentPage>,
  ]);
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
  const releaseOptions = [...releaseById.values()];
  return {
    ...organization,
    canManage,
    deliveries,
    enrollments: enrollments.results,
    releaseOptions,
    versions,
  };
}

export async function getMyAssessmentDeliveries(slug: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const [deliveries, gradebooks] = await Promise.all([
    learnerDeliveries(client, slug),
    learnerGradebookResults(client, slug),
  ]);
  return { ...organization, deliveries, gradebooks };
}

export async function getMyDeliveries(slug: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const deliveries = await learnerDeliveries(client, slug);
  return { ...organization, deliveries };
}

export async function getMyGradebookResults(slug: string) {
  const organization = await getOrganizationForPage(slug);
  const client = await createPlatformServerClient();
  const gradebooks = await learnerGradebookResults(client, slug);
  return { ...organization, gradebooks };
}

async function learnerDeliveries(
  client: Awaited<ReturnType<typeof createPlatformServerClient>>,
  slug: string,
) {
  return (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/my-deliveries/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar las evaluaciones asignadas.',
  )) as LearnerDelivery[];
}

async function learnerGradebookResults(
  client: Awaited<ReturnType<typeof createPlatformServerClient>>,
  slug: string,
) {
  const gradebooks = (await required(
    client.GET('/api/v1/organizations/{slug}/assessments/me/gradebooks/', {
      params: { path: { slug } },
      cache: 'no-store',
    }),
    'No fue posible consultar los libros de calificaciones.',
  )) as Gradebook[];
  return Promise.all(
    gradebooks.map(
      (gradebook) =>
        required(
          client.GET(
            '/api/v1/organizations/{slug}/assessments/me/gradebooks/{gradebook_id}/',
            {
              params: {
                path: { gradebook_id: gradebook.id, slug },
              },
              cache: 'no-store',
            },
          ),
          'No fue posible consultar el resumen de calificaciones.',
        ) as Promise<GradebookStudentPayload>,
    ),
  );
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

export async function getRegradeJobs(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.regrading.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const [jobs, versionOptions] = await Promise.all([
    required(
      client.GET('/api/v1/organizations/{slug}/assessments/regrade-jobs/', {
        params: { path: { slug } },
        cache: 'no-store',
      }),
      'No fue posible consultar las recalificaciones.',
    ) as Promise<RegradeJob[]>,
    advancedAssessmentOptions(client, slug),
  ]);
  return { ...organization, jobs, versionOptions };
}

export async function getRegradeJob(slug: string, jobId: string) {
  const data = await getRegradeJobs(slug);
  const client = await createPlatformServerClient();
  const [job, attempts] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{slug}/assessments/regrade-jobs/{job_id}/',
        {
          params: { path: { job_id: jobId, slug } },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar la recalificación.',
    ) as Promise<RegradeJob>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/assessments/regrade-jobs/{job_id}/attempts/',
        {
          params: { path: { job_id: jobId, slug } },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar los intentos recalificados.',
    ) as Promise<RegradeJobAttempt[]>,
  ]);
  return { ...data, attempts, job };
}

export async function getGradebooks(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.gradebook.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const canManage = organization.access.capabilities.includes(
    'assessment.gradebook.manage',
  );
  const [gradebooks, deliveries, cohorts] = await Promise.all([
    required(
      client.GET('/api/v1/organizations/{slug}/assessments/gradebooks/', {
        params: { path: { slug } },
        cache: 'no-store',
      }),
      'No fue posible consultar los libros de calificaciones.',
    ) as Promise<Gradebook[]>,
    canManage
      ? (required(
          client.GET('/api/v1/organizations/{slug}/assessments/deliveries/', {
            params: { path: { slug } },
            cache: 'no-store',
          }),
          'No fue posible consultar las entregas disponibles.',
        ) as Promise<AssessmentDeliveryPage>)
      : Promise.resolve(null),
    canManage
      ? (required(
          client.GET('/api/v1/organizations/{slug}/learning/cohorts/', {
            params: {
              path: { slug },
              query: { ordering: 'name', page_size: 100, status: 'active' },
            },
            cache: 'no-store',
          }),
          'No fue posible consultar las secciones disponibles.',
        ) as Promise<CohortPage>)
      : Promise.resolve(null),
  ]);
  return {
    ...organization,
    canManage,
    cohorts: cohorts?.results ?? [],
    deliveries: deliveries?.results ?? [],
    gradebooks,
  };
}

export async function getGradebook(slug: string, gradebookId: string) {
  const data = await getGradebooks(slug);
  const client = await createPlatformServerClient();
  const [gradebook, entries, summaries] = await Promise.all([
    required(
      client.GET(
        '/api/v1/organizations/{slug}/assessments/gradebooks/{gradebook_id}/',
        {
          params: { path: { gradebook_id: gradebookId, slug } },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar el libro de calificaciones.',
    ) as Promise<Gradebook>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/assessments/gradebooks/{gradebook_id}/entries/',
        {
          params: { path: { gradebook_id: gradebookId, slug } },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar las calificaciones.',
    ) as Promise<GradebookEntry[]>,
    required(
      client.GET(
        '/api/v1/organizations/{slug}/assessments/gradebooks/{gradebook_id}/summaries/',
        {
          params: { path: { gradebook_id: gradebookId, slug } },
          cache: 'no-store',
        },
      ),
      'No fue posible consultar los resúmenes.',
    ) as Promise<GradebookSummary[]>,
  ]);
  return { ...data, entries, gradebook, summaries };
}

export async function getAssessmentAnalytics(
  slug: string,
  assessmentVersionId: string,
) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.analytics.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const [{ data, response }, versionOptions] = await Promise.all([
    client.GET(
      '/api/v1/organizations/{slug}/assessments/analytics/assessments/{version_id}/',
      {
        params: { path: { slug, version_id: assessmentVersionId } },
        cache: 'no-store',
      },
    ),
    analyticsAssessmentOptions(client, slug),
  ]);
  if (response.status === 403) notFound();
  if (!response.ok && response.status !== 404) {
    throw new Error('No fue posible consultar la analítica.');
  }
  const snapshot = (data ?? null) as AnalyticsSnapshot | null;
  const version = versionOptions.find(
    (option) => option.id === assessmentVersionId,
  );
  if (!version) notFound();
  const revisions = organization.access.capabilities.includes(
    'assessment.analytics.refresh',
  )
    ? await analyticsRevisionOptions(client, slug, assessmentVersionId)
    : [];
  return { ...organization, snapshot, version: { ...version, revisions } };
}

export async function getAnalyticsContext(slug: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('assessment.analytics.view')) {
    notFound();
  }
  const client = await createPlatformServerClient();
  const versionOptions = await analyticsAssessmentOptions(client, slug);
  return { ...organization, versionOptions };
}
