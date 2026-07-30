'use client';

import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import type { components } from '@/lib/api/generated/platform';
import { courseStatusLabel } from '@/lib/courses/labels';
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
    <section aria-labelledby="review-title" className="border-t pt-5">
      <h2 className="text-base font-semibold" id="review-title">
        Flujo de revisión
      </h2>
      <p className="mt-1 text-sm text-muted-foreground">
        Estado actual: {courseStatusLabel(revision.authoring_status)}
      </p>
      <div aria-live="polite" className="mt-3">
        {message ? <p className="rounded bg-primary/5 p-3">{message}</p> : null}
        {error ? (
          <p className="rounded bg-red-50 p-3 text-red-950">{error}</p>
        ) : null}
      </div>
      <div
        className="mt-4 border-y bg-muted/25 px-4 py-4"
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
          <p className="mt-2 text-sm text-muted-foreground">
            No hay bloqueos estructurales.
          </p>
        )}
      </div>
      <div className="mt-5 flex flex-wrap gap-3">
        {canSubmit &&
        ['draft', 'changes_requested'].includes(revision.authoring_status) ? (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button>Enviar a revisión</Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Enviar para evaluación</AlertDialogTitle>
                <AlertDialogDescription>
                  La estructura quedará en modo de solo lectura mientras se
                  revisa.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancelar</AlertDialogCancel>
                <AlertDialogAction onClick={() => void act('submit-review')}>
                  Enviar revisión
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : null}
        {canApprove && revision.authoring_status === 'in_review' ? (
          <Button
            onClick={() => void act('approve')}
            type="button"
            variant="outline"
          >
            Aprobar estructura
          </Button>
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
              className="mt-2 min-h-24 w-full rounded-lg border border-border p-3"
              maxLength={2000}
              name="review-note"
              ref={note}
              required
            />
          </label>
          <Button className="mt-3" type="submit" variant="outline">
            Solicitar cambios
          </Button>
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
