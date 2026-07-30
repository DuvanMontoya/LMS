const STATUS_LABELS: Readonly<Record<string, string>> = {
  active: 'Activo',
  approved: 'Aprobada',
  archived: 'Archivado',
  changes_requested: 'Cambios solicitados',
  draft: 'Borrador',
  in_review: 'En revisión',
};

export function courseStatusLabel(value: string) {
  return STATUS_LABELS[value] ?? value;
}
