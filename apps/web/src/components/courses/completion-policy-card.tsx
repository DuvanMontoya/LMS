'use client';

import { useState } from 'react';
import { CheckCircle2, GraduationCap, ShieldCheck } from 'lucide-react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { components } from '@/lib/api/generated/platform';
import { useConfirmCompletionPolicy } from '@/lib/courses/hooks';

type Policy = components['schemas']['CourseCompletionPolicy'];

export function CompletionPolicyCard({
  courseSlug,
  onConfirmed,
  policy,
  revisionId,
  revisionVersion,
  slug,
}: Readonly<{
  courseSlug: string;
  onConfirmed: () => void;
  policy: Policy;
  revisionId: string;
  revisionVersion: number;
  slug: string;
}>) {
  const [gradeEnabled, setGradeEnabled] = useState(
    policy.minimum_grade_basis_points !== null,
  );
  const [attendanceEnabled, setAttendanceEnabled] = useState(
    policy.minimum_attendance_basis_points !== null,
  );
  const [error, setError] = useState('');
  const mutation = useConfirmCompletionPolicy({ courseSlug, revisionId, slug });

  async function submit(formData: FormData) {
    setError('');
    try {
      await mutation.mutateAsync({
        expected_version: revisionVersion,
        minimum_attendance_basis_points: attendanceEnabled
          ? Number(formData.get('policy-attendance')) * 100
          : null,
        minimum_grade_basis_points: gradeEnabled
          ? Number(formData.get('policy-grade')) * 100
          : null,
        require_required_activities: formData.get('policy-required') === 'on',
      });
      onConfirmed();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No fue posible confirmar la política.',
      );
    }
  }

  const confirmed = Boolean(policy.confirmed_at);
  return (
    <section
      className="mt-5 rounded-xl border bg-card p-4 shadow-xs"
      aria-labelledby="completion-policy-title"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex items-start gap-3">
          <span className="rounded-lg bg-primary/10 p-2 text-primary">
            <GraduationCap className="size-5" />
          </span>
          <div>
            <h3 className="font-semibold" id="completion-policy-title">
              Cómo se completa el curso
            </h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Una decisión guiada, independiente de cómo finaliza cada
              actividad.
            </p>
          </div>
        </div>
        <Badge
          className={confirmed ? 'bg-emerald-600 text-white' : ''}
          variant={confirmed ? 'default' : 'outline'}
        >
          {confirmed ? (
            <>
              <CheckCircle2 />
              Confirmada
            </>
          ) : (
            'Falta confirmar'
          )}
        </Badge>
      </div>
      {error ? (
        <Alert className="mt-3" variant="destructive">
          <AlertTitle>No se pudo guardar</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      <form action={submit} className="mt-4 grid gap-3 lg:grid-cols-3">
        <label className="flex items-start gap-3 rounded-xl border p-3">
          <input
            className="mt-1"
            defaultChecked={policy.require_required_activities}
            name="policy-required"
            type="checkbox"
          />
          <span>
            <strong className="text-sm">
              Completar actividades obligatorias
            </strong>
            <span className="mt-1 block text-xs text-muted-foreground">
              Recomendado: respeta el recorrido diseñado.
            </span>
          </span>
        </label>
        <div className="rounded-xl border p-3">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input
              checked={gradeEnabled}
              onChange={(event) => setGradeEnabled(event.target.checked)}
              type="checkbox"
            />
            Exigir nota global mínima
          </label>
          <label className="academic-field mt-2">
            Porcentaje
            <input
              className="academic-control"
              defaultValue={(policy.minimum_grade_basis_points ?? 7000) / 100}
              disabled={!gradeEnabled}
              max={100}
              min={0}
              name="policy-grade"
              type="number"
            />
          </label>
        </div>
        <div className="rounded-xl border p-3">
          <label className="flex items-center gap-2 text-sm font-medium">
            <input
              checked={attendanceEnabled}
              onChange={(event) => setAttendanceEnabled(event.target.checked)}
              type="checkbox"
            />
            Exigir asistencia global
          </label>
          <label className="academic-field mt-2">
            Porcentaje
            <input
              className="academic-control"
              defaultValue={
                (policy.minimum_attendance_basis_points ?? 7500) / 100
              }
              disabled={!attendanceEnabled}
              max={100}
              min={0}
              name="policy-attendance"
              type="number"
            />
          </label>
        </div>
        <div className="flex flex-wrap items-center justify-between gap-3 lg:col-span-3">
          <p className="flex items-center gap-2 text-xs text-muted-foreground">
            <ShieldCheck className="size-4" />
            Puedes confirmar la opción recomendada sin configurar porcentajes
            globales.
          </p>
          <Button
            disabled={mutation.isPending}
            type="submit"
            variant={confirmed ? 'outline' : 'default'}
          >
            {mutation.isPending
              ? 'Guardando…'
              : confirmed
                ? 'Actualizar política'
                : 'Confirmar política'}
          </Button>
        </div>
      </form>
    </section>
  );
}
