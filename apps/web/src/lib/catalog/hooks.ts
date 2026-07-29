'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import type { components } from '@/lib/api/generated/platform';
import { catalogKeys } from '@/lib/query/catalog-keys';

type Prerequisite = components['schemas']['SubjectPrerequisite'];

export type CreateConceptInput = {
  definition: string;
  name: string;
  slug: string;
};

export type CreateAreaInput = {
  description?: string;
  name: string;
  slug: string;
};

async function requireData<T>(
  request: Promise<{ error?: unknown; response: Response; data?: T }>,
): Promise<T> {
  const { error, response, data } = await request;
  if (response.ok && data) return data;
  let message = 'No fue posible guardar el concepto.';
  if (error && typeof error === 'object' && 'detail' in error) {
    const detail = error.detail;
    if (typeof detail === 'string') message = detail;
  }
  try {
    const body: unknown = await response.clone().json();
    if (body && typeof body === 'object' && 'detail' in body) {
      const detail = body.detail;
      if (typeof detail === 'string') message = detail;
    }
  } catch {
    // The neutral Spanish message is safe if the API cannot provide details.
  }
  throw new Error(message);
}

export function useCreateConcept(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateConceptInput) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/catalog/concepts/',
          { params: { path: { slug } }, body: input },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.concepts(slug) }),
  });
}

export function useCreateArea(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateAreaInput) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/catalog/areas/',
          { params: { path: { slug } }, body: input },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.structure(slug) }),
  });
}

type NamedEntityKind = 'area' | 'discipline' | 'subject';

export function useUpdateNamedEntity(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      entityId,
      kind,
      name,
    }: {
      entityId: string;
      kind: NamedEntityKind;
      name: string;
    }) => {
      if (kind === 'area') {
        return requireData<unknown>(
          platformBrowserClient.PATCH(
            '/api/v1/organizations/{slug}/catalog/areas/{area_id}/',
            { body: { name }, params: { path: { slug, area_id: entityId } } },
          ),
        );
      }
      if (kind === 'discipline') {
        return requireData<unknown>(
          platformBrowserClient.PATCH(
            '/api/v1/organizations/{slug}/catalog/disciplines/{discipline_id}/',
            {
              body: { name },
              params: { path: { slug, discipline_id: entityId } },
            },
          ),
        );
      }
      return requireData<unknown>(
        platformBrowserClient.PATCH(
          '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/',
          { body: { name }, params: { path: { slug, subject_id: entityId } } },
        ),
      );
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.structure(slug) }),
  });
}

export function useSetNamedEntityArchived(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      entityId,
      kind,
      restore,
    }: {
      entityId: string;
      kind: NamedEntityKind;
      restore: boolean;
    }) => {
      if (kind === 'area') {
        return requireData<unknown>(
          platformBrowserClient.POST(
            restore
              ? '/api/v1/organizations/{slug}/catalog/areas/{area_id}/restore/'
              : '/api/v1/organizations/{slug}/catalog/areas/{area_id}/archive/',
            { params: { path: { slug, area_id: entityId } } },
          ),
        );
      }
      if (kind === 'discipline') {
        return requireData<unknown>(
          platformBrowserClient.POST(
            restore
              ? '/api/v1/organizations/{slug}/catalog/disciplines/{discipline_id}/restore/'
              : '/api/v1/organizations/{slug}/catalog/disciplines/{discipline_id}/archive/',
            { params: { path: { slug, discipline_id: entityId } } },
          ),
        );
      }
      return requireData<unknown>(
        platformBrowserClient.POST(
          restore
            ? '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/restore/'
            : '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/archive/',
          { params: { path: { slug, subject_id: entityId } } },
        ),
      );
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.structure(slug) }),
  });
}

export function useUpdateConcept(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conceptId,
      definition,
      name,
    }: {
      conceptId: string;
      definition: string;
      name: string;
    }) =>
      requireData(
        platformBrowserClient.PATCH(
          '/api/v1/organizations/{slug}/catalog/concepts/{concept_id}/',
          {
            body: { definition, name },
            params: { path: { slug, concept_id: conceptId } },
          },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.concepts(slug) }),
  });
}

export function useSetConceptArchived(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conceptId,
      restore,
    }: {
      conceptId: string;
      restore: boolean;
    }) =>
      requireData(
        platformBrowserClient.POST(
          restore
            ? '/api/v1/organizations/{slug}/catalog/concepts/{concept_id}/restore/'
            : '/api/v1/organizations/{slug}/catalog/concepts/{concept_id}/archive/',
          { params: { path: { slug, concept_id: conceptId } } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.concepts(slug) }),
  });
}

export function useCreateDiscipline(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      area_id: string;
      description?: string;
      name: string;
      slug: string;
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/catalog/disciplines/',
          { params: { path: { slug } }, body: input },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.structure(slug) }),
  });
}

export function useCreateSubject(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      description?: string;
      discipline_id: string;
      name: string;
      slug: string;
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/catalog/subjects/',
          { params: { path: { slug } }, body: input },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.structure(slug) }),
  });
}

export function useCreateTopic(slug: string, subjectId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      description?: string;
      parent_id?: string;
      slug: string;
      title: string;
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/topics/',
          { params: { path: { slug, subject_id: subjectId } }, body: input },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.structure(slug) }),
  });
}

export function useUpdateTopic(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ title, topicId }: { title: string; topicId: string }) =>
      requireData(
        platformBrowserClient.PATCH(
          '/api/v1/organizations/{slug}/catalog/topics/{topic_id}/',
          { body: { title }, params: { path: { slug, topic_id: topicId } } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.structure(slug) }),
  });
}

export function useCreateObjective(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: {
      code: string;
      cognitive_level?:
        'analyze' | 'apply' | 'create' | 'evaluate' | 'remember' | 'understand';
      description?: string;
      statement: string;
      subject_id: string;
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/catalog/learning-objectives/',
          { params: { path: { slug } }, body: input },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.root(slug) }),
  });
}

export function useUpdateObjective(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      objectiveId,
      statement,
    }: {
      objectiveId: string;
      statement: string;
    }) =>
      requireData(
        platformBrowserClient.PATCH(
          '/api/v1/organizations/{slug}/catalog/learning-objectives/{objective_id}/',
          {
            body: { statement },
            params: { path: { slug, objective_id: objectiveId } },
          },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.root(slug) }),
  });
}

export function useSetObjectiveArchived(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      objectiveId,
      restore,
    }: {
      objectiveId: string;
      restore: boolean;
    }) =>
      requireData(
        platformBrowserClient.POST(
          restore
            ? '/api/v1/organizations/{slug}/catalog/learning-objectives/{objective_id}/restore/'
            : '/api/v1/organizations/{slug}/catalog/learning-objectives/{objective_id}/archive/',
          { params: { path: { slug, objective_id: objectiveId } } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.root(slug) }),
  });
}

export function useReplaceSubjectPrerequisites(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      prerequisites,
      subjectId,
    }: {
      prerequisites: Prerequisite[];
      subjectId: string;
    }) =>
      requireData(
        platformBrowserClient.PUT(
          '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/prerequisites/',
          {
            body: { prerequisites },
            params: { path: { slug, subject_id: subjectId } },
          },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.root(slug) }),
  });
}

function useReplacePrerequisites(slug: string, entity: 'concept' | 'subject') {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      entityId,
      prerequisites,
    }: {
      entityId: string;
      prerequisites: Prerequisite[];
    }) =>
      entity === 'subject'
        ? requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/catalog/subjects/{subject_id}/prerequisites/',
              {
                body: { prerequisites },
                params: { path: { slug, subject_id: entityId } },
              },
            ),
          )
        : requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/catalog/concepts/{concept_id}/prerequisites/',
              {
                body: { prerequisites },
                params: { path: { slug, concept_id: entityId } },
              },
            ),
          ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.root(slug) }),
  });
}

export function useReplaceConceptPrerequisites(slug: string) {
  return useReplacePrerequisites(slug, 'concept');
}

function useReplaceConceptAssociations(
  slug: string,
  entity: 'topic' | 'objective',
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      conceptIds,
      entityId,
    }: {
      conceptIds: string[];
      entityId: string;
    }) =>
      entity === 'topic'
        ? requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/catalog/topics/{topic_id}/concepts/',
              {
                body: { concept_ids: conceptIds },
                params: { path: { slug, topic_id: entityId } },
              },
            ),
          )
        : requireData(
            platformBrowserClient.PUT(
              '/api/v1/organizations/{slug}/catalog/learning-objectives/{objective_id}/concepts/',
              {
                body: { concept_ids: conceptIds },
                params: { path: { slug, objective_id: entityId } },
              },
            ),
          ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.root(slug) }),
  });
}

export function useReplaceTopicConcepts(slug: string) {
  return useReplaceConceptAssociations(slug, 'topic');
}

export function useReplaceObjectiveConcepts(slug: string) {
  return useReplaceConceptAssociations(slug, 'objective');
}

export function useMoveTopic(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({
      position = 'last-child',
      targetId,
      topicId,
    }: {
      position?: components['schemas']['PositionEnum'];
      targetId: string;
      topicId: string;
    }) =>
      requireData(
        platformBrowserClient.POST(
          '/api/v1/organizations/{slug}/catalog/topics/{topic_id}/move/',
          {
            body: { position, target_id: targetId },
            params: { path: { slug, topic_id: topicId } },
          },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.structure(slug) }),
  });
}

export function useSetTopicArchived(slug: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ restore, topicId }: { restore: boolean; topicId: string }) =>
      requireData(
        platformBrowserClient.POST(
          restore
            ? '/api/v1/organizations/{slug}/catalog/topics/{topic_id}/restore/'
            : '/api/v1/organizations/{slug}/catalog/topics/{topic_id}/archive/',
          { params: { path: { slug, topic_id: topicId } } },
        ),
      ),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: catalogKeys.structure(slug) }),
  });
}
