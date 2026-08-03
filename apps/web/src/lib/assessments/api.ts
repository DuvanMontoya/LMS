'use client';

import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

export class AssessmentApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export function createRegradeJob(
  slug: string,
  body: components['schemas']['RegradeJobCreate'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/regrade-jobs/',
      { body, params: { path: { slug } } },
    ),
  );
}

export function retryRegradeJob(
  slug: string,
  jobId: string,
  expectedVersion: number,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/regrade-jobs/{job_id}/retry-failed/',
      {
        body: { expected_version: expectedVersion },
        params: { path: { job_id: jobId, slug } },
      },
    ),
  );
}

export function createGradebook(
  slug: string,
  body: components['schemas']['GradebookCreate'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/gradebooks/',
      { body, params: { path: { slug } } },
    ),
  );
}

export function activateGradebook(
  slug: string,
  gradebookId: string,
  expectedVersion: number,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/gradebooks/{gradebook_id}/activate/',
      {
        body: { expected_version: expectedVersion },
        params: { path: { gradebook_id: gradebookId, slug } },
      },
    ),
  );
}

export function addGradebookColumn(
  slug: string,
  gradebookId: string,
  body: components['schemas']['GradebookColumnCreate'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/gradebooks/{gradebook_id}/columns/',
      {
        body,
        params: { path: { gradebook_id: gradebookId, slug } },
      },
    ),
  );
}

export function updateGradebookColumn(
  slug: string,
  gradebookId: string,
  columnId: string,
  body: components['schemas']['GradebookColumnUpdate'],
) {
  return required(
    platformBrowserClient.PATCH(
      '/api/v1/organizations/{slug}/assessments/gradebooks/{gradebook_id}/columns/{column_id}/',
      {
        body,
        params: {
          path: { column_id: columnId, gradebook_id: gradebookId, slug },
        },
      },
    ),
  );
}

export function reorderGradebookColumns(
  slug: string,
  gradebookId: string,
  body: components['schemas']['GradebookColumnOrder'],
) {
  return required(
    platformBrowserClient.PUT(
      '/api/v1/organizations/{slug}/assessments/gradebooks/{gradebook_id}/columns/order/',
      {
        body,
        params: { path: { gradebook_id: gradebookId, slug } },
      },
    ),
  );
}

export function archiveGradebookColumn(
  slug: string,
  gradebookId: string,
  columnId: string,
  expectedVersion: number,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/gradebooks/{gradebook_id}/columns/{column_id}/archive/',
      {
        body: { expected_version: expectedVersion },
        params: {
          path: { column_id: columnId, gradebook_id: gradebookId, slug },
        },
      },
    ),
  );
}

export function refreshAssessmentAnalytics(
  slug: string,
  body: components['schemas']['AnalyticsRefresh'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/analytics/refresh/',
      { body, params: { path: { slug } } },
    ),
  );
}

export function getAssessmentAnalyticsJob(slug: string, jobId: string) {
  return required(
    platformBrowserClient.GET(
      '/api/v1/organizations/{slug}/assessments/analytics/jobs/{job_id}/',
      { params: { path: { job_id: jobId, slug } } },
    ),
  );
}

function apiErrorMessage(value: unknown, path = ''): string | null {
  if (typeof value === 'string') {
    return path ? `${path}: ${value}` : value;
  }
  if (Array.isArray(value)) {
    for (const item of value) {
      const message = apiErrorMessage(item, path);
      if (message) return message;
    }
    return null;
  }
  if (value && typeof value === 'object') {
    const record = value as Record<string, unknown>;
    if (typeof record.detail === 'string') {
      return typeof record.path === 'string'
        ? `${record.path}: ${record.detail}`
        : record.detail;
    }
    for (const [key, item] of Object.entries(record)) {
      if (key === 'code') continue;
      const message = apiErrorMessage(item, path ? `${path}.${key}` : key);
      if (message) return message;
    }
  }
  return null;
}

async function required<T>(
  request: Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  const payload =
    error && typeof error === 'object'
      ? (error as Record<string, unknown>)
      : {};
  throw new AssessmentApiError(
    apiErrorMessage(payload) ?? `La operación falló (HTTP ${response.status}).`,
    typeof payload.code === 'string' ? payload.code : 'assessment_invalid',
    response.status,
  );
}

export function createAssessment(
  slug: string,
  body: components['schemas']['AssessmentCreate'],
) {
  return required(
    platformBrowserClient.POST('/api/v1/organizations/{slug}/assessments/', {
      body,
      params: { path: { slug } },
    }),
  );
}

export function createQuestionBank(
  slug: string,
  body: components['schemas']['QuestionBankCreate'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/question-banks/',
      { body, params: { path: { slug } } },
    ),
  );
}

export function updateQuestionBank(
  slug: string,
  bankId: string,
  body: components['schemas']['QuestionBankUpdate'],
) {
  return required(
    platformBrowserClient.PATCH(
      '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/',
      { body, params: { path: { bank_id: bankId, slug } } },
    ),
  );
}

export function createQuestion(
  slug: string,
  bankId: string,
  body: components['schemas']['QuestionCreate'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/',
      { body, params: { path: { bank_id: bankId, slug } } },
    ),
  );
}

export function createQuestionRevisionFromVersion(
  slug: string,
  bankId: string,
  questionId: string,
  versionNumber: number,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/{question_id}/versions/{version_number}/create-draft/',
      {
        params: {
          path: {
            bank_id: bankId,
            question_id: questionId,
            slug,
            version_number: versionNumber,
          },
        },
      },
    ),
  );
}

type QuestionRevisionPath = {
  bankId: string;
  questionId: string;
  revisionId: string;
  slug: string;
};

function questionRevisionPath(path: QuestionRevisionPath) {
  return {
    bank_id: path.bankId,
    question_id: path.questionId,
    revision_id: path.revisionId,
    slug: path.slug,
  };
}

export function updateQuestionRevision(
  path: QuestionRevisionPath,
  body: components['schemas']['QuestionRevisionUpdate'],
) {
  return required(
    platformBrowserClient.PATCH(
      '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/{question_id}/revisions/{revision_id}/',
      { body, params: { path: questionRevisionPath(path) } },
    ),
  );
}

export function transitionQuestionRevision(
  path: QuestionRevisionPath,
  action: 'approve' | 'request-changes' | 'submit-review',
  body: components['schemas']['AssessmentTransitionInput'],
) {
  const endpoints = {
    approve:
      '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/{question_id}/revisions/{revision_id}/approve/',
    'request-changes':
      '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/{question_id}/revisions/{revision_id}/request-changes/',
    'submit-review':
      '/api/v1/organizations/{slug}/assessments/question-banks/{bank_id}/questions/{question_id}/revisions/{revision_id}/submit-review/',
  } as const;
  return required(
    platformBrowserClient.POST(endpoints[action], {
      body,
      params: { path: questionRevisionPath(path) },
    }),
  );
}

type AssessmentRevisionPath = {
  assessmentSlug: string;
  revisionId: string;
  slug: string;
};

function assessmentRevisionPath(path: AssessmentRevisionPath) {
  return {
    assessment_slug: path.assessmentSlug,
    revision_id: path.revisionId,
    slug: path.slug,
  };
}

export function updateAssessmentRevision(
  path: AssessmentRevisionPath,
  body: components['schemas']['AssessmentRevisionUpdate'],
) {
  return required(
    platformBrowserClient.PATCH(
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/',
      { body, params: { path: assessmentRevisionPath(path) } },
    ),
  );
}

export function replaceAssessmentObjectives(
  path: AssessmentRevisionPath,
  body: components['schemas']['ObjectiveReplace'],
) {
  return required(
    platformBrowserClient.PUT(
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/objectives/',
      { body, params: { path: assessmentRevisionPath(path) } },
    ),
  );
}

export function addAssessmentSection(
  path: AssessmentRevisionPath,
  body: components['schemas']['SectionCreate'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/sections/',
      { body, params: { path: assessmentRevisionPath(path) } },
    ),
  );
}

export function reorderAssessmentSections(
  path: AssessmentRevisionPath,
  body: components['schemas']['OrderedIds'],
) {
  return required(
    platformBrowserClient.PUT(
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/sections/order/',
      { body, params: { path: assessmentRevisionPath(path) } },
    ),
  );
}

export function addAssessmentItem(
  path: AssessmentRevisionPath & { sectionId: string },
  body: components['schemas']['ItemCreate'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/sections/{section_id}/items/',
      {
        body,
        params: {
          path: {
            ...assessmentRevisionPath(path),
            section_id: path.sectionId,
          },
        },
      },
    ),
  );
}

export function reorderAssessmentItems(
  path: AssessmentRevisionPath & { sectionId: string },
  body: components['schemas']['OrderedIds'],
) {
  return required(
    platformBrowserClient.PUT(
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/sections/{section_id}/items/order/',
      {
        body,
        params: {
          path: {
            ...assessmentRevisionPath(path),
            section_id: path.sectionId,
          },
        },
      },
    ),
  );
}

export function updateAssessmentItem(
  path: AssessmentRevisionPath & { itemId: string; sectionId: string },
  body: components['schemas']['ItemUpdate'],
) {
  return required(
    platformBrowserClient.PATCH(
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/sections/{section_id}/items/{item_id}/',
      {
        body,
        params: {
          path: {
            ...assessmentRevisionPath(path),
            item_id: path.itemId,
            section_id: path.sectionId,
          },
        },
      },
    ),
  );
}

export function createAssessmentPool(
  path: AssessmentRevisionPath,
  body: components['schemas']['PoolCreate'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/pools/',
      { body, params: { path: assessmentRevisionPath(path) } },
    ),
  );
}

export function replaceAssessmentPoolCandidates(
  slug: string,
  poolId: string,
  body: components['schemas']['PoolCandidates'],
) {
  return required(
    platformBrowserClient.PUT(
      '/api/v1/organizations/{slug}/assessments/pools/{pool_id}/candidates/',
      { body, params: { path: { pool_id: poolId, slug } } },
    ),
  );
}

export function updateAssessmentPool(
  slug: string,
  poolId: string,
  body: components['schemas']['PoolUpdate'],
) {
  return required(
    platformBrowserClient.PATCH(
      '/api/v1/organizations/{slug}/assessments/pools/{pool_id}/',
      { body, params: { path: { pool_id: poolId, slug } } },
    ),
  );
}

export function transitionAssessmentRevision(
  path: AssessmentRevisionPath,
  action: 'approve' | 'request-changes' | 'submit-review',
  body: components['schemas']['AssessmentTransitionInput'],
) {
  const endpoints = {
    approve:
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/approve/',
    'request-changes':
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/request-changes/',
    'submit-review':
      '/api/v1/organizations/{slug}/assessments/{assessment_slug}/revisions/{revision_id}/submit-review/',
  } as const;
  return required(
    platformBrowserClient.POST(endpoints[action], {
      body,
      params: { path: assessmentRevisionPath(path) },
    }),
  );
}

export function createAssessmentDelivery(
  slug: string,
  body: components['schemas']['DeliveryCreate'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/deliveries/',
      { body, params: { path: { slug } } },
    ),
  );
}

export function activateAssessmentDelivery(
  slug: string,
  deliveryId: string,
  expectedVersion: number,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/deliveries/{delivery_id}/activate/',
      {
        body: { expected_version: expectedVersion },
        params: { path: { delivery_id: deliveryId, slug } },
      },
    ),
  );
}

export function assignAssessmentDelivery(
  slug: string,
  deliveryId: string,
  releaseAssignmentId: string,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/deliveries/{delivery_id}/assignments/',
      {
        body: { release_assignment_id: releaseAssignmentId },
        params: { path: { delivery_id: deliveryId, slug } },
      },
    ),
  );
}

export function assignAssessmentCohort(
  slug: string,
  deliveryId: string,
  cohortId: string,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/deliveries/{delivery_id}/assign-cohort/',
      {
        body: { cohort_id: cohortId },
        params: { path: { delivery_id: deliveryId, slug } },
      },
    ),
  );
}

export function withdrawAssessmentDelivery(
  slug: string,
  deliveryId: string,
  expectedVersion: number,
  note: string,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/deliveries/{delivery_id}/withdraw/',
      {
        body: { expected_version: expectedVersion, note },
        params: { path: { delivery_id: deliveryId, slug } },
      },
    ),
  );
}

export function startAssessmentAttempt(slug: string, assignmentId: string) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/my-deliveries/{assignment_id}/attempts/start/',
      { params: { path: { assignment_id: assignmentId, slug } } },
    ),
  );
}

export function saveAssessmentResponse(
  slug: string,
  attemptId: string,
  attemptItemId: string,
  body: components['schemas']['ResponseSave'],
) {
  return required(
    platformBrowserClient.PUT(
      '/api/v1/organizations/{slug}/assessments/attempts/{attempt_id}/responses/{attempt_item_id}/',
      {
        body,
        params: {
          path: {
            attempt_id: attemptId,
            attempt_item_id: attemptItemId,
            slug,
          },
        },
      },
    ),
  );
}

export function submitAssessmentAttempt(
  slug: string,
  attemptId: string,
  expectedVersion: number,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/attempts/{attempt_id}/submit/',
      {
        body: { expected_version: expectedVersion },
        params: { path: { attempt_id: attemptId, slug } },
      },
    ),
  );
}

export function gradeAssessmentResponse(
  slug: string,
  responseId: string,
  body: components['schemas']['ManualGrade'],
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/assessments/manual-grading/{response_id}/',
      { body, params: { path: { response_id: responseId, slug } } },
    ),
  );
}

export function getAssessmentResultBrowser(slug: string, attemptId: string) {
  return required(
    platformBrowserClient.GET(
      '/api/v1/organizations/{slug}/assessments/attempts/{attempt_id}/result/',
      {
        params: { path: { attempt_id: attemptId, slug } },
        cache: 'no-store',
      },
    ),
  );
}
