import type { AssetAccessDescriptor } from './api';

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

function delivered(value: unknown) {
  if (!record(value)) return false;
  return (
    typeof value.role === 'string' &&
    typeof value.url === 'string' &&
    /^https?:\/\//.test(value.url) &&
    typeof value.mime_type === 'string' &&
    typeof value.size_bytes === 'number'
  );
}

export function parseAssetDescriptors(value: unknown): AssetAccessDescriptor[] {
  if (!Array.isArray(value)) return [];
  return value.filter((entry): entry is AssetAccessDescriptor => {
    if (!record(entry)) return false;
    return (
      typeof entry.asset_version_id === 'string' &&
      typeof entry.kind === 'string' &&
      typeof entry.expires_at === 'string' &&
      (entry.source === null || delivered(entry.source)) &&
      Array.isArray(entry.variants) &&
      entry.variants.every(delivered)
    );
  });
}
