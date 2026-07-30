const accessLabels: Record<string, string> = {
  available: 'Disponible',
  ended: 'Acceso finalizado',
  membership_inactive: 'Membresía inactiva',
  not_started: 'Acceso no iniciado',
  publication_withdrawn: 'Publicación retirada',
  release_invalid: 'Release no disponible',
  revoked: 'Matrícula revocada',
  suspended: 'Matrícula suspendida',
};

const progressLabels: Record<string, string> = {
  completed: 'Completado',
  in_progress: 'En progreso',
  not_started: 'No iniciado',
};

const enrollmentLabels: Record<string, string> = {
  active: 'Activa',
  revoked: 'Revocada',
  suspended: 'Suspendida',
};

const cohortLabels: Record<string, string> = {
  active: 'Activa',
  archived: 'Archivada',
};

export function accessStateLabel(value: string): string {
  return accessLabels[value] ?? value;
}

export function cohortStatusLabel(value: string): string {
  return cohortLabels[value] ?? value;
}

export function enrollmentStatusLabel(value: string): string {
  return enrollmentLabels[value] ?? value;
}

export function progressStatusLabel(value: string): string {
  return progressLabels[value] ?? value;
}

export function percentLabel(basisPoints: number): string {
  return new Intl.NumberFormat('es-CO', {
    maximumFractionDigits: 2,
    minimumFractionDigits: 0,
  }).format(basisPoints / 100);
}

export function dateTimeLabel(value?: string | null): string {
  if (!value) return 'Sin registrar';
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

export function accessWindowLabel(
  start?: string | null,
  end?: string | null,
): string {
  if (!start && !end) return 'Sin límite';
  const format = (value?: string | null) =>
    value
      ? new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium' }).format(
          new Date(value),
        )
      : 'Sin límite';
  return `${format(start)} – ${format(end)}`;
}
