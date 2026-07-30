'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  createDraftFromRelease,
  publishRevision,
  withdrawPublication,
} from '@/lib/publishing/api';
import { courseKeys } from '@/lib/query/course-keys';
import { libraryKeys, publicationKeys } from '@/lib/query/publication-keys';

type PublicationPath = { slug: string; courseSlug: string };

export function usePublishRevision(
  path: PublicationPath & { revisionId: string },
) {
  const queryClient = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: (expectedPublicationVersion: number) =>
      publishRevision(path, {
        expected_publication_version: expectedPublicationVersion,
      }),
    onSuccess: async (result) => {
      queryClient.setQueryData(
        publicationKeys.release(
          path.slug,
          path.courseSlug,
          result.release_number,
        ),
        result,
      );
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: publicationKeys.status(path.slug, path.courseSlug),
        }),
        queryClient.invalidateQueries({
          queryKey: publicationKeys.releases(path.slug, path.courseSlug),
        }),
        queryClient.invalidateQueries({
          queryKey: libraryKeys.root(path.slug),
        }),
      ]);
    },
  });
}

export function useWithdrawPublication(path: PublicationPath) {
  const queryClient = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: ({
      expectedPublicationVersion,
      note,
    }: {
      expectedPublicationVersion: number;
      note: string;
    }) =>
      withdrawPublication(path, {
        expected_publication_version: expectedPublicationVersion,
        note,
      }),
    onSuccess: async () => {
      queryClient.removeQueries({
        queryKey: libraryKeys.course(path.slug, path.courseSlug),
      });
      await Promise.all([
        queryClient.invalidateQueries({
          queryKey: publicationKeys.status(path.slug, path.courseSlug),
        }),
        queryClient.invalidateQueries({
          queryKey: libraryKeys.root(path.slug),
        }),
      ]);
    },
  });
}

export function useCreateDraftFromRelease(
  path: PublicationPath & { releaseNumber: number },
) {
  const queryClient = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: (expectedPublicationVersion: number) =>
      createDraftFromRelease(path, {
        expected_publication_version: expectedPublicationVersion,
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({
        queryKey: courseKeys.course(path.slug, path.courseSlug),
      }),
  });
}
