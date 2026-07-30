'use client';

import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import { publicationErrorMessage } from './errors';

async function requireMutationData<T>(
  request: Promise<{ error?: unknown; response: Response; data?: T }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  throw new Error(publicationErrorMessage(error));
}

type PublicationPath = { slug: string; courseSlug: string };

export function publishRevision(
  path: PublicationPath & { revisionId: string },
  body: components['schemas']['Publish'],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/publish/',
      {
        body,
        params: {
          path: {
            slug: path.slug,
            course_slug: path.courseSlug,
            revision_id: path.revisionId,
          },
        },
      },
    ),
  );
}

export function withdrawPublication(
  path: PublicationPath,
  body: components['schemas']['Withdraw'],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/courses/{course_slug}/publication/withdraw/',
      {
        body,
        params: {
          path: { slug: path.slug, course_slug: path.courseSlug },
        },
      },
    ),
  );
}

export function createDraftFromRelease(
  path: PublicationPath & { releaseNumber: number },
  body: components['schemas']['CreateDraft'],
) {
  return requireMutationData(
    platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/courses/{course_slug}/releases/{release_number}/create-draft/',
      {
        body,
        params: {
          path: {
            slug: path.slug,
            course_slug: path.courseSlug,
            release_number: path.releaseNumber,
          },
        },
      },
    ),
  );
}
