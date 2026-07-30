'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiErrorMessage } from '@/lib/api/api-error';
import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import { courseKeys } from '@/lib/query/course-keys';

export class RevisionConflictError extends Error {
  constructor() {
    super(
      'La revisión cambió desde que la abriste. Tus valores se conservaron; actualiza la estructura antes de volver a guardar.',
    );
  }
}

async function requireData<T>(
  request: Promise<{ error?: unknown; response: Response; data?: T }>,
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  if (response.status === 409) throw new RevisionConflictError();
  throw new Error(
    apiErrorMessage(error, 'No fue posible completar la operación.'),
  );
}

export function useCreateCourse(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: components['schemas']['CourseCreate']) =>
      requireData(
        platformBrowserClient.POST('/api/v1/organizations/{slug}/courses/', {
          body,
          params: { path: { slug } },
        }),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: courseKeys.list(slug) }),
  });
}

type RevisionPath = {
  courseSlug: string;
  revisionId: string;
  slug: string;
};

const pathFor = ({ courseSlug, revisionId, slug }: RevisionPath) => ({
  course_slug: courseSlug,
  revision_id: revisionId,
  slug,
});

export function useUpdateRevisionMetadata(path: RevisionPath) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: components['schemas']['RevisionMetadataUpdate']) =>
      requireData(
        platformBrowserClient.PATCH(
          '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/',
          { body, params: { path: pathFor(path) } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: courseKeys.course(path.slug, path.courseSlug),
      }),
  });
}

export function useCreateModule(path: RevisionPath) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: components['schemas']['ModuleCreate']) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/modules/',
          { body, params: { path: pathFor(path) } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: courseKeys.outline(
          path.slug,
          path.courseSlug,
          path.revisionId,
        ),
      }),
  });
}

export function useCreateUnit(path: RevisionPath) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      body,
      moduleId,
    }: {
      body: components['schemas']['UnitCreate'];
      moduleId: string;
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/modules/{module_id}/units/',
          {
            body,
            params: {
              path: { ...pathFor(path), module_id: moduleId },
            },
          },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: courseKeys.outline(
          path.slug,
          path.courseSlug,
          path.revisionId,
        ),
      }),
  });
}

export function useUpdateStructure(path: RevisionPath) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      body,
      id,
      kind,
    }:
      | {
          body: components['schemas']['ModuleUpdate'];
          id: string;
          kind: 'module';
        }
      | {
          body: components['schemas']['UnitUpdate'];
          id: string;
          kind: 'unit';
        }): Promise<unknown> => {
      if (kind === 'module') {
        return requireData(
          platformBrowserClient.PATCH(
            '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/modules/{module_id}/',
            {
              body,
              params: { path: { ...pathFor(path), module_id: id } },
            },
          ),
        );
      }
      return requireData(
        platformBrowserClient.PATCH(
          '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/',
          {
            body,
            params: { path: { ...pathFor(path), unit_id: id } },
          },
        ),
      );
    },
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: courseKeys.outline(
          path.slug,
          path.courseSlug,
          path.revisionId,
        ),
      }),
  });
}

export function useReorderStructure(path: RevisionPath) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      body,
      moduleId,
    }: {
      body: components['schemas']['ReplaceOrder'];
      moduleId?: string;
    }) =>
      moduleId
        ? requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/modules/{module_id}/units/order/',
              {
                body,
                params: { path: { ...pathFor(path), module_id: moduleId } },
              },
            ),
          )
        : requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/modules/order/',
              { body, params: { path: pathFor(path) } },
            ),
          ),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: courseKeys.outline(
          path.slug,
          path.courseSlug,
          path.revisionId,
        ),
      }),
  });
}

export function useSetStructureArchived(path: RevisionPath) {
  return useMutation({
    mutationFn: async ({
      expectedVersion,
      id,
      kind,
      restore,
    }: {
      expectedVersion: number;
      id: string;
      kind: 'module' | 'unit';
      restore: boolean;
    }) => {
      const body = { expected_version: expectedVersion };
      if (kind === 'module') {
        return (await requireData(
          platformBrowserClient.POST(
            restore
              ? '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/modules/{module_id}/restore/'
              : '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/modules/{module_id}/archive/',
            {
              body,
              params: { path: { ...pathFor(path), module_id: id } },
            },
          ),
        )) as unknown;
      }
      return (await requireData(
        platformBrowserClient.POST(
          restore
            ? '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/restore/'
            : '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/archive/',
          { body, params: { path: { ...pathFor(path), unit_id: id } } },
        ),
      )) as unknown;
    },
  });
}

export function useReplaceCourseAlignment(path: RevisionPath) {
  return useMutation({
    mutationFn: ({
      body,
      kind,
    }:
      | {
          body: components['schemas']['ReplaceSubjects'];
          kind: 'subjects';
        }
      | {
          body: components['schemas']['ReplaceObjectives'];
          kind: 'objectives';
        }) =>
      kind === 'subjects'
        ? requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/subjects/',
              { body, params: { path: pathFor(path) } },
            ),
          )
        : requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/learning-objectives/',
              { body, params: { path: pathFor(path) } },
            ),
          ),
  });
}

export function useReplaceUnitAlignment(path: RevisionPath) {
  return useMutation({
    mutationFn: ({
      body,
      kind,
      unitId,
    }:
      | {
          body: components['schemas']['ReplaceTopics'];
          kind: 'topics';
          unitId: string;
        }
      | {
          body: components['schemas']['ReplaceObjectives'];
          kind: 'objectives';
          unitId: string;
        }) =>
      kind === 'topics'
        ? requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/topics/',
              {
                body,
                params: { path: { ...pathFor(path), unit_id: unitId } },
              },
            ),
          )
        : requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/units/{unit_id}/learning-objectives/',
              {
                body,
                params: { path: { ...pathFor(path), unit_id: unitId } },
              },
            ),
          ),
  });
}

export function useReviewAction(path: RevisionPath) {
  return useMutation({
    mutationFn: ({
      action,
      body,
    }: {
      action: 'approve' | 'request-changes' | 'submit-review';
      body: components['schemas']['WorkflowAction'];
    }) => {
      if (action === 'approve') {
        return requireData(
          platformBrowserClient.POST(
            '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/approve/',
            { body, params: { path: pathFor(path) } },
          ),
        );
      }
      if (action === 'request-changes') {
        return requireData(
          platformBrowserClient.POST(
            '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/request-changes/',
            { body, params: { path: pathFor(path) } },
          ),
        );
      }
      return requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/courses/{course_slug}/revisions/{revision_id}/submit-review/',
          { body, params: { path: pathFor(path) } },
        ),
      );
    },
  });
}
