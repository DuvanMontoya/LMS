import { apiErrorCode, apiErrorMessage } from '@/lib/api/api-error';

const messages: Record<string, string> = {
  publication_conflict:
    'La publicación cambió desde que abriste esta pantalla. Actualiza antes de reintentar.',
  publication_permission_denied:
    'No tienes capacidad para realizar esta operación.',
  publication_transition_invalid:
    'La publicación ya no admite esta transición.',
  release_chain_invalid:
    'La cadena de releases no supera la verificación de integridad.',
  release_integrity_failed:
    'El release no supera la verificación de integridad.',
  release_snapshot_invalid:
    'La revisión aprobada no puede producir un snapshot válido.',
  release_snapshot_too_large:
    'La revisión excede los límites permitidos para un release.',
  release_source_not_approved:
    'La revisión debe estar aprobada antes de publicarse.',
  release_source_not_newer:
    'La revisión aprobada no es posterior al release vigente.',
  draft_already_open: 'El curso ya tiene una revisión abierta.',
  draft_creation_invalid: 'No fue posible clonar este release.',
  withdrawal_note_required: 'Escribe una justificación para retirar el curso.',
};

export function publicationErrorMessage(
  error: unknown,
  fallback = 'No fue posible completar la operación.',
): string {
  const code = apiErrorCode(error);
  return (code && messages[code]) || apiErrorMessage(error, fallback);
}
