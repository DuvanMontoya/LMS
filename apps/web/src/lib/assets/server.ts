import 'server-only';

import { notFound } from 'next/navigation';

import type { operations } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';
import { getOrganizationForPage } from '@/lib/organizations/server';

export type AssetSummary =
  operations['organizations_assets_list']['responses'][200]['content']['application/json'][number];
export type AssetDetail =
  operations['organizations_assets_retrieve']['responses'][200]['content']['application/json'];
export type AssetUsage =
  operations['organizations_assets_usage_retrieve']['responses'][200]['content']['application/json'];

async function required<T>(
  request: Promise<{ response: Response; data?: T }>,
  message: string,
): Promise<T> {
  const { data, response } = await request;
  if (response.status === 403 || response.status === 404) notFound();
  if (!response.ok || data === undefined) throw new Error(message);
  return data;
}

export async function getAssetsForPage(
  slug: string,
  query: { kind?: string; search?: string; status?: string },
) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('asset.library.view'))
    notFound();
  const client = await createPlatformServerClient();
  const assets = await required(
    client.GET('/api/v1/organizations/{organization_slug}/assets/', {
      params: { path: { organization_slug: slug }, query },
    }),
    'No fue posible consultar los recursos.',
  );
  return { ...organization, assets };
}

export async function getAssetForPage(slug: string, assetId: string) {
  const organization = await getOrganizationForPage(slug);
  if (!organization.access.capabilities.includes('asset.library.view'))
    notFound();
  const client = await createPlatformServerClient();
  const asset = (await required(
    client.GET('/api/v1/organizations/{organization_slug}/assets/{asset_id}/', {
      params: {
        path: { asset_id: assetId, organization_slug: slug },
      },
    }),
    'No fue posible consultar el recurso.',
  )) as AssetDetail;
  let usage: AssetUsage | undefined;
  if (organization.access.capabilities.includes('asset.library.manage')) {
    usage = (await required(
      client.GET(
        '/api/v1/organizations/{organization_slug}/assets/{asset_id}/usage/',
        {
          params: {
            path: { asset_id: assetId, organization_slug: slug },
          },
        },
      ),
      'No fue posible consultar los usos.',
    )) as AssetUsage;
  }
  return { ...organization, asset, usage };
}
