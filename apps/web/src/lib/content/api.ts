'use client';

import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

export type ContentPath = {
  courseSlug: string;
  organizationSlug: string;
  revisionId: string;
  unitId: string;
};

export class ContentConflictError extends Error {
  currentVersion: number | undefined;

  constructor(message: string, currentVersion?: number) {
    super(message);
    this.currentVersion = currentVersion;
  }
}

const apiPath = ({
  courseSlug,
  organizationSlug,
  revisionId,
  unitId,
}: ContentPath) => ({
  course_slug: courseSlug,
  organization_slug: organizationSlug,
  revision_id: revisionId,
  unit_id: unitId,
});

async function requireData<T>(
  request: Promise<{
    data?: T;
    error?: unknown;
    response: Response;
  }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  let detail = 'No fue posible completar la operación.';
  let currentVersion: number | undefined;
  if (error && typeof error === 'object') {
    if ('detail' in error && typeof error.detail === 'string')
      detail = error.detail;
    if (
      'current_document_version' in error &&
      typeof error.current_document_version === 'number'
    )
      currentVersion = error.current_document_version;
  }
  if (response.status === 409)
    throw new ContentConflictError(detail, currentVersion);
  throw new Error(detail);
}

export function fetchCurrentContent(path: ContentPath) {
  return requireData(
    platformBrowserClient.GET(
      '/api/v1/organizations/{organization_slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/content/',
      { params: { path: apiPath(path) } },
    ),
  );
}

export function saveContent(
  path: ContentPath,
  body: components['schemas']['ContentWrite'],
) {
  return requireData(
    platformBrowserClient.PUT(
      '/api/v1/organizations/{organization_slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/content/',
      { body, params: { path: apiPath(path) } },
    ),
  );
}

export function fetchContentVersion(path: ContentPath, versionNumber: number) {
  return requireData(
    platformBrowserClient.GET(
      '/api/v1/organizations/{organization_slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/content/versions/{version_number}/',
      {
        params: {
          path: { ...apiPath(path), version_number: versionNumber },
        },
      },
    ),
  );
}

export function restoreContentVersion(
  path: ContentPath,
  versionNumber: number,
  expectedDocumentVersion: number,
) {
  return requireData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{organization_slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/content/versions/{version_number}/restore/',
      {
        body: { expected_document_version: expectedDocumentVersion },
        params: {
          path: { ...apiPath(path), version_number: versionNumber },
        },
      },
    ),
  );
}
