'use client';

import { apiErrorMessage } from '@/lib/api/api-error';
import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

export type AssetAccessDescriptor =
  components['schemas']['AssetAccessDescriptor'];
export type AssetProcessingJob = components['schemas']['ProcessingJob'];

async function required<T>(
  request: Promise<{ error?: unknown; response: Response; data?: T }>,
  fallback: string,
): Promise<T> {
  const { data, error, response } = await request;
  if (response.ok && data !== undefined) return data;
  throw new Error(apiErrorMessage(error, fallback));
}

export async function getAssetAccess(
  slug: string,
  assetId: string,
  versionId: string,
  original = false,
): Promise<AssetAccessDescriptor> {
  const suffix = original ? 'original-download' : 'access';
  return required(
    platformBrowserClient.POST(
      `/api/v1/organizations/{organization_slug}/assets/{asset_id}/versions/{version_id}/${suffix}/` as
        | '/api/v1/organizations/{organization_slug}/assets/{asset_id}/versions/{version_id}/access/'
        | '/api/v1/organizations/{organization_slug}/assets/{asset_id}/versions/{version_id}/original-download/',
      {
        params: {
          path: {
            asset_id: assetId,
            organization_slug: slug,
            version_id: versionId,
          },
        },
      },
    ),
    'No fue posible autorizar el acceso temporal.',
  );
}

export async function mutateAssetState(
  slug: string,
  assetId: string,
  action: 'archive' | 'restore',
  expectedLockVersion: number,
) {
  const path =
    action === 'archive'
      ? '/api/v1/organizations/{organization_slug}/assets/{asset_id}/archive/'
      : '/api/v1/organizations/{organization_slug}/assets/{asset_id}/restore/';
  return required(
    platformBrowserClient.POST(path, {
      body: { expected_lock_version: expectedLockVersion },
      params: { path: { asset_id: assetId, organization_slug: slug } },
    }),
    'No fue posible cambiar el estado del recurso.',
  );
}

export async function promoteAssetVersion(
  slug: string,
  assetId: string,
  versionId: string,
  expectedLockVersion: number,
) {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{organization_slug}/assets/{asset_id}/versions/{version_id}/promote/',
      {
        body: { expected_lock_version: expectedLockVersion },
        params: {
          path: {
            asset_id: assetId,
            organization_slug: slug,
            version_id: versionId,
          },
        },
      },
    ),
    'No fue posible promover la versión.',
  );
}

export async function reprocessAssetVersion(
  slug: string,
  assetId: string,
  versionId: string,
): Promise<AssetProcessingJob> {
  return required(
    platformBrowserClient.POST(
      '/api/v1/organizations/{organization_slug}/assets/{asset_id}/versions/{version_id}/reprocess/',
      {
        params: {
          path: {
            asset_id: assetId,
            organization_slug: slug,
            version_id: versionId,
          },
        },
      },
    ),
    'No fue posible solicitar el reprocesamiento.',
  );
}
