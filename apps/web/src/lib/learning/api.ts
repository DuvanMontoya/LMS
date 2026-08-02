'use client';

import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import { csrfFetch } from '@/lib/api/csrf';

export class LearningApiError extends Error {
  constructor(
    message: string,
    readonly code: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function requireMutationData<T>(
  request: Promise<{ error?: unknown; response: Response; data?: T }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  const payload =
    error && typeof error === 'object'
      ? (error as Record<string, unknown>)
      : {};
  throw new LearningApiError(
    typeof payload.detail === 'string'
      ? payload.detail
      : 'No fue posible actualizar el aprendizaje.',
    typeof payload.code === 'string' ? payload.code : 'learning_invalid',
    response.status,
  );
}

type UnitPath = {
  slug: string;
  enrollmentId: string;
  unitId: string;
};

export function openLearningUnit(path: UnitPath) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/me/enrollments/{enrollment_id}/units/{unit_id}/open/',
      {
        params: {
          path: {
            slug: path.slug,
            enrollment_id: path.enrollmentId,
            unit_id: path.unitId,
          },
        },
      },
    ),
  );
}

export function completeLearningUnit(
  path: UnitPath,
  body: components['schemas']['CompleteUnit'],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/me/enrollments/{enrollment_id}/units/{unit_id}/complete/',
      {
        body,
        params: {
          path: {
            slug: path.slug,
            enrollment_id: path.enrollmentId,
            unit_id: path.unitId,
          },
        },
      },
    ),
  );
}

export function reopenLearningUnit(
  path: UnitPath,
  body: components['schemas']['CompleteUnit'],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/me/enrollments/{enrollment_id}/units/{unit_id}/reopen/',
      {
        body,
        params: {
          path: {
            slug: path.slug,
            enrollment_id: path.enrollmentId,
            unit_id: path.unitId,
          },
        },
      },
    ),
  );
}

export function updateLearningPosition(
  path: Omit<UnitPath, 'unitId'>,
  body: components['schemas']['Position'],
) {
  return requireMutationData(
    platformBrowserClient.PUT(
      '/api/v1/organizations/{slug}/learning/me/enrollments/{enrollment_id}/position/',
      {
        body,
        params: {
          path: { slug: path.slug, enrollment_id: path.enrollmentId },
        },
      },
    ),
  );
}

export async function flushLearningPosition(
  path: Omit<UnitPath, 'unitId'>,
  body: components['schemas']['Position'],
) {
  return csrfFetch(
    `/api/v1/organizations/${encodeURIComponent(path.slug)}/learning/me/enrollments/${encodeURIComponent(path.enrollmentId)}/position/`,
    {
      body: JSON.stringify(body),
      headers: { 'Content-Type': 'application/json' },
      keepalive: true,
      method: 'PUT',
    },
  );
}

export function createLearningCohort(
  slug: string,
  body: components['schemas']['CohortCreate'],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/cohorts/',
      { body, params: { path: { slug } } },
    ),
  );
}

export function createLearningEnrollment(
  slug: string,
  body: components['schemas']['EnrollmentCreate'],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/enrollments/',
      { body, params: { path: { slug } } },
    ),
  );
}

export function archiveLearningCohort(
  slug: string,
  cohortId: string,
  expectedCohortVersion: number,
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/cohorts/{cohort_id}/archive/',
      {
        body: { expected_cohort_version: expectedCohortVersion },
        params: { path: { slug, cohort_id: cohortId } },
      },
    ),
  );
}

export function enrollLearningCohort(
  slug: string,
  cohortId: string,
  expectedCohortVersion: number,
  membershipIds: string[],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/cohorts/{cohort_id}/enrollments/',
      {
        body: {
          expected_cohort_version: expectedCohortVersion,
          membership_ids: membershipIds,
        },
        params: { path: { slug, cohort_id: cohortId } },
      },
    ),
  );
}

export function previewLearningCohortRosterSync(
  slug: string,
  cohortId: string,
  body: components['schemas']['CohortSyncRequest'],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/cohorts/{cohort_id}/sync-preview/',
      { body, params: { path: { slug, cohort_id: cohortId } } },
    ),
  );
}

export function confirmLearningCohortRosterSync(
  slug: string,
  cohortId: string,
  body: components['schemas']['CohortSyncRequest'],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/cohorts/{cohort_id}/sync-confirm/',
      { body, params: { path: { slug, cohort_id: cohortId } } },
    ),
  );
}

type EnrollmentAction = 'reactivate' | 'revoke' | 'suspend';

export function changeLearningEnrollmentStatus(
  slug: string,
  enrollmentId: string,
  action: EnrollmentAction,
  expectedEnrollmentVersion: number,
) {
  const paths = {
    reactivate:
      '/api/v1/organizations/{slug}/learning/enrollments/{enrollment_id}/reactivate/',
    revoke:
      '/api/v1/organizations/{slug}/learning/enrollments/{enrollment_id}/revoke/',
    suspend:
      '/api/v1/organizations/{slug}/learning/enrollments/{enrollment_id}/suspend/',
  } as const;
  return requireMutationData(
    platformBrowserClient.POST(paths[action], {
      body: { expected_enrollment_version: expectedEnrollmentVersion },
      params: { path: { slug, enrollment_id: enrollmentId } },
    }),
  );
}

export function upgradeLearningEnrollment(
  slug: string,
  enrollmentId: string,
  expectedEnrollmentVersion: number,
  targetReleaseNumber: number,
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/enrollments/{enrollment_id}/upgrade-release/',
      {
        body: {
          expected_enrollment_version: expectedEnrollmentVersion,
          target_release_number: targetReleaseNumber,
        },
        params: { path: { slug, enrollment_id: enrollmentId } },
      },
    ),
  );
}

export function makeLearningEnrollmentIndividual(
  slug: string,
  enrollmentId: string,
  expectedEnrollmentVersion: number,
  reason: string,
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/learning/enrollments/{enrollment_id}/make-individual/',
      {
        body: {
          expected_enrollment_version: expectedEnrollmentVersion,
          reason,
        },
        params: { path: { slug, enrollment_id: enrollmentId } },
      },
    ),
  );
}
