import type { components } from '@/lib/api/generated/platform';

type AssetKind = components['schemas']['AssetKind'];

const KIND_LABELS: Record<AssetKind, string> = {
  audio: 'Audio',
  caption: 'Subtítulos',
  dataset: 'Dataset',
  document: 'Documento',
  image: 'Imagen',
  video: 'Video',
};

const STATUS_LABELS: Record<string, string> = {
  active: 'Activo',
  archived: 'Archivado',
  failed: 'Error',
  pending_upload: 'Pendiente de carga',
  processing: 'Procesando',
  ready: 'Listo',
  rejected: 'Rechazado',
  scanning: 'Escaneando',
  uploaded: 'Verificando',
};

export function assetKindLabel(kind: AssetKind): string {
  return KIND_LABELS[kind];
}

export function assetStatusLabel(status?: string): string {
  if (!status) return 'Sin estado';
  return STATUS_LABELS[status] ?? status;
}

export function formatBytes(value?: number | null): string {
  if (!value) return '—';
  const units = ['B', 'KiB', 'MiB', 'GiB'];
  let amount = value;
  let unit = 0;
  while (amount >= 1024 && unit < units.length - 1) {
    amount /= 1024;
    unit += 1;
  }
  return `${amount.toFixed(unit === 0 ? 0 : 1)} ${units[unit]}`;
}
