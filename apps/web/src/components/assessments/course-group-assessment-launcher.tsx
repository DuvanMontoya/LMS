'use client';

import { CheckCircle2, ClipboardCheck, LoaderCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

export function CourseGroupAssessmentLauncher({
  cohortId,
  slug,
}: Readonly<{ cohortId: string; slug: string }>) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function materialize() {
    setError(null);
    setMessage(null);
    setIsPending(true);
    try {
      const {
        data,
        error: responseError,
        response,
      } = await platformBrowserClient.POST(
        '/api/v1/organizations/{slug}/assessments/course-groups/{course_group_id}/deliveries/materialize/',
        { params: { path: { course_group_id: cohortId, slug } } },
      );
      if (!response.ok || !data) {
        const payload =
          responseError && typeof responseError === 'object'
            ? (responseError as Record<string, unknown>)
            : {};
        throw new Error(
          typeof payload.detail === 'string'
            ? payload.detail
            : 'No fue posible activar las evaluaciones del grupo.',
        );
      }
      const deliveryMessage = data.created_delivery_count
        ? `${data.created_delivery_count} evaluaciones activadas`
        : `${data.already_materialized_count} evaluaciones ya estaban activas`;
      const assignmentMessage = data.created_assignment_count
        ? `${data.created_assignment_count} asignaciones nuevas`
        : 'sin asignaciones pendientes';
      setMessage(`${deliveryMessage}; ${assignmentMessage}.`);
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No fue posible activar las evaluaciones del grupo.',
      );
    } finally {
      setIsPending(false);
    }
  }

  return (
    <section
      aria-labelledby="activar-evaluaciones"
      className="academic-panel mt-6 p-5"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="academic-kicker">Operación de la sección</p>
          <h2 className="text-xl font-semibold" id="activar-evaluaciones">
            Activar evaluaciones
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Convierte cada evaluación aprobada del release en una entrega real y
            la asigna a las matrículas activas. Puedes repetir la operación
            después de incorporar estudiantes; no duplica entregas ni intentos.
          </p>
        </div>
        <ClipboardCheck className="size-6 text-primary" />
      </div>
      {error ? (
        <Alert className="mt-4" variant="destructive">
          <AlertTitle>No se activaron las evaluaciones</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      {message ? (
        <Alert className="mt-4">
          <CheckCircle2 />
          <AlertTitle>Evaluaciones disponibles</AlertTitle>
          <AlertDescription>{message}</AlertDescription>
        </Alert>
      ) : null}
      <Button
        className="mt-5"
        disabled={isPending}
        onClick={() => void materialize()}
        type="button"
      >
        {isPending ? (
          <LoaderCircle className="animate-spin" />
        ) : (
          <ClipboardCheck />
        )}
        Activar evaluaciones pendientes
      </Button>
    </section>
  );
}
