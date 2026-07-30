'use client';

import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';

import type { components } from '@/lib/api/generated/platform';
import { useReviewAction } from '@/lib/courses/hooks';

type Revision = components['schemas']['Revision'];
type Readiness = components['schemas']['Readiness'];

function contentIssueUnitId(path: string): string | undefined {
  const match = path.match(/^modules\.[^.]+\.units\.([^.]+)\.content$/);
  return match?.[1];
}

export function ReviewPanel({
  canApprove,
  canReview,
  canSubmit,
  courseSlug,
  readiness,
  revision,
  slug,
}: Readonly<{
  canApprove: boolean;
  canReview: boolean;
  canSubmit: boolean;
  courseSlug: string;
  readiness: Readiness;
  revision: Revision;
  slug: string;
}>) {
  const router = useRouter();
  const mutation = useReviewAction({
    courseSlug,
    revisionId: revision.id,
    slug,
  });
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const note = useRef<HTMLTextAreaElement>(null);

  async function act(
    action: 'approve' | 'request-changes' | 'submit-review',
    noteValue = '',
  ) {
    setError('');
    if (action === 'submit-review' && !readiness.ready) {
      setError('Resuelve los problemas de integridad antes de enviar.');
      document.getElementById('readiness-issues')?.focus();
      return;
    }
    if (action === 'request-changes' && !noteValue.trim()) {
      setError('La nota de cambios es obligatoria.');
      note.current?.focus();
      return;
    }
    try {
      await mutation.mutateAsync({
        action,
        body: { expected_version: revision.lock_version, note: noteValue },
      });
      setMessage('El estado de la revisión se actualizó correctamente.');
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No fue posible cambiar el estado.',
      );
    }
  }

  return (
    <section
      aria-labelledby="review-title"
      className="rounded-xl border border-slate-200 bg-white p-6"
    >
      <h2 className="text-xl font-semibold" id="review-title">
        Flujo de revisión
      </h2>
      <p className="mt-2">Estado actual: {revision.authoring_status}</p>
      <div aria-live="polite" className="mt-3">
        {message ? <p className="rounded bg-sky-50 p-3">{message}</p> : null}
        {error ? (
          <p className="rounded bg-red-50 p-3 text-red-950">{error}</p>
        ) : null}
      </div>
      <div
        className="mt-4 rounded-lg bg-slate-50 p-4"
        id="readiness-issues"
        tabIndex={-1}
      >
        <h3 className="font-semibold">
          {readiness.ready ? 'Lista para revisión' : 'Problemas por resolver'}
        </h3>
        {readiness.issues.length ? (
          <ul className="mt-2 list-disc space-y-1 pl-5">
            {readiness.issues.map((issue) => (
              <li key={`${issue.code}-${issue.path}`}>
                {issue.message}{' '}
                {contentIssueUnitId(issue.path) ? (
                  <a
                    className="font-medium text-sky-800 underline"
                    href={`/organizaciones/${slug}/cursos/${courseSlug}/unidades/${contentIssueUnitId(issue.path)}/contenido`}
                  >
                    Abrir unidad
                  </a>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="mt-2 text-sm text-slate-600">
            No hay bloqueos estructurales.
          </p>
        )}
      </div>
      <div className="mt-5 flex flex-wrap gap-3">
        {canSubmit &&
        ['draft', 'changes_requested'].includes(revision.authoring_status) ? (
          <button
            className="rounded-lg bg-slate-950 px-4 py-2 font-medium text-white"
            onClick={() => {
              if (window.confirm('¿Enviar esta revisión para evaluación?'))
                void act('submit-review');
            }}
            type="button"
          >
            Enviar a revisión
          </button>
        ) : null}
        {canApprove && revision.authoring_status === 'in_review' ? (
          <button
            className="rounded-lg bg-emerald-800 px-4 py-2 font-medium text-white"
            onClick={() => void act('approve')}
            type="button"
          >
            Aprobar estructura
          </button>
        ) : null}
      </div>
      {canReview && revision.authoring_status === 'in_review' ? (
        <form
          action={(formData) =>
            act('request-changes', String(formData.get('review-note') ?? ''))
          }
          className="mt-5"
        >
          <label className="font-medium">
            Nota para solicitar cambios
            <textarea
              className="mt-2 min-h-24 w-full rounded-lg border border-slate-300 p-3"
              maxLength={2000}
              name="review-note"
              ref={note}
              required
            />
          </label>
          <button
            className="mt-3 rounded-lg border px-4 py-2 font-medium"
            type="submit"
          >
            Solicitar cambios
          </button>
        </form>
      ) : null}
      {revision.authoring_status === 'approved' ? (
        <p className="mt-5 rounded-lg bg-emerald-50 p-4 text-emerald-950">
          La estructura fue aprobada. La publicación y el contenido se mantienen
          separados: aprobar no publica el curso.
        </p>
      ) : null}
    </section>
  );
}
