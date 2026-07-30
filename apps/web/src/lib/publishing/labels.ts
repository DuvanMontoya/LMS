export function publicationStatusLabel(status: string | null): string {
  if (status === 'active') return 'Activa';
  if (status === 'withdrawn') return 'Retirada';
  return 'Sin publicar';
}

export function languageLabel(code: string): string {
  try {
    return new Intl.DisplayNames(['es'], { type: 'language' }).of(code) ?? code;
  } catch {
    return code;
  }
}

export function shortDigest(digest: string): string {
  return `${digest.slice(0, 12)}…${digest.slice(-8)}`;
}

export function formatDuration(minutes: number | null): string {
  if (!minutes) return 'Duración no especificada';
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;
  if (!hours) return `${minutes} min`;
  return remainder ? `${hours} h ${remainder} min` : `${hours} h`;
}
