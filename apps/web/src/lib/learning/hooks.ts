'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';

import {
  archiveLearningCohort,
  changeLearningEnrollmentStatus,
  completeLearningUnit,
  createLearningCohort,
  createLearningEnrollment,
  enrollLearningCohort,
  openLearningUnit,
  reopenLearningUnit,
  updateLearningPosition,
  upgradeLearningEnrollment,
} from './api';
import { learningKeys } from './keys';

type UnitPath = { slug: string; enrollmentId: string; unitId: string };

function invalidations(path: UnitPath) {
  return [
    learningKeys.mine(path.slug),
    learningKeys.enrollment(path.slug, path.enrollmentId),
    learningKeys.outline(path.slug, path.enrollmentId),
    learningKeys.unit(path.slug, path.enrollmentId, path.unitId),
    learningKeys.progress(path.slug, path.enrollmentId),
  ];
}

export function useOpenUnit(path: UnitPath) {
  const queryClient = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: () => openLearningUnit(path),
    onSuccess: async () => {
      await Promise.all(
        invalidations(path).map((queryKey) =>
          queryClient.invalidateQueries({ queryKey }),
        ),
      );
    },
  });
}

export function useCompleteUnit(path: UnitPath) {
  const queryClient = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: (expectedProgressVersion: number) =>
      completeLearningUnit(path, {
        expected_progress_version: expectedProgressVersion,
      }),
    onSuccess: async () => {
      await Promise.all(
        invalidations(path).map((queryKey) =>
          queryClient.invalidateQueries({ queryKey }),
        ),
      );
    },
  });
}

export function useReopenUnit(path: UnitPath) {
  const queryClient = useQueryClient();
  return useMutation({
    retry: false,
    mutationFn: (expectedProgressVersion: number) =>
      reopenLearningUnit(path, {
        expected_progress_version: expectedProgressVersion,
      }),
    onSuccess: async () => {
      await Promise.all(
        invalidations(path).map((queryKey) =>
          queryClient.invalidateQueries({ queryKey }),
        ),
      );
    },
  });
}

export function useUpdatePosition(path: Omit<UnitPath, 'unitId'>) {
  return useMutation({
    retry: false,
    mutationFn: ({ nodeId, unitId }: { nodeId: string; unitId: string }) =>
      updateLearningPosition(path, { node_id: nodeId, unit_id: unitId }),
  });
}

function useAdminLearningMutation<T>(
  slug: string,
  mutationFn: (value: T) => Promise<unknown>,
) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn,
    retry: false,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: learningKeys.all(slug) });
    },
  });
}

export function useCreateCohort(slug: string) {
  return useAdminLearningMutation(
    slug,
    (body: Parameters<typeof createLearningCohort>[1]) =>
      createLearningCohort(slug, body),
  );
}

export function useCreateEnrollment(slug: string) {
  return useAdminLearningMutation(
    slug,
    (body: Parameters<typeof createLearningEnrollment>[1]) =>
      createLearningEnrollment(slug, body),
  );
}

export function useArchiveCohort(slug: string, cohortId: string) {
  return useAdminLearningMutation(slug, () =>
    archiveLearningCohort(slug, cohortId),
  );
}

export function useEnrollCohort(slug: string, cohortId: string) {
  return useAdminLearningMutation(slug, (membershipIds: string[]) =>
    enrollLearningCohort(slug, cohortId, membershipIds),
  );
}

export function useEnrollmentLifecycle(slug: string, enrollmentId: string) {
  return useAdminLearningMutation(
    slug,
    ({
      action,
      version,
    }: {
      action: 'reactivate' | 'revoke' | 'suspend';
      version: number;
    }) => changeLearningEnrollmentStatus(slug, enrollmentId, action, version),
  );
}

export function useUpgradeEnrollment(slug: string, enrollmentId: string) {
  return useAdminLearningMutation(
    slug,
    ({ release, version }: { release: number; version: number }) =>
      upgradeLearningEnrollment(slug, enrollmentId, version, release),
  );
}
