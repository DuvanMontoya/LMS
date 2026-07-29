export function requireInternalOrigin(value: string | undefined): string {
  if (!value) {
    throw new Error(
      'DJANGO_INTERNAL_ORIGIN es obligatorio para iniciar la aplicación web.',
    );
  }

  let origin: URL;
  try {
    origin = new URL(value);
  } catch {
    throw new Error(
      'DJANGO_INTERNAL_ORIGIN debe ser un origen HTTP(S) válido.',
    );
  }

  if (
    !['http:', 'https:'].includes(origin.protocol) ||
    origin.username ||
    origin.password ||
    origin.pathname !== '/' ||
    origin.search ||
    origin.hash
  ) {
    throw new Error(
      'DJANGO_INTERNAL_ORIGIN debe contener solo un origen HTTP(S), sin credenciales ni ruta.',
    );
  }

  return origin.origin;
}
