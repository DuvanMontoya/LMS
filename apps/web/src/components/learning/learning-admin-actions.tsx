'use client';

import {
  Archive,
  CircleArrowUp,
  CirclePause,
  CirclePlay,
  LoaderCircle,
  ShieldX,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  useArchiveCohort,
  useEnrollmentLifecycle,
  useUpgradeEnrollment,
} from '@/lib/learning/hooks';
import type { LearningCourseOption } from '@/lib/learning/server';

export function CohortActions({
  cohortId,
  slug,
  status,
}: Readonly<{ cohortId: string; slug: string; status: string }>) {
  const router = useRouter();
  const mutation = useArchiveCohort(slug, cohortId);
  if (status === 'archived') return null;
  return (
    <ConfirmAction
      description="La cohorte dejará de aceptar matrículas nuevas. Su historial, matrículas y progreso permanecerán disponibles."
      label="Archivar"
      onConfirm={async () => {
        await mutation.mutateAsync(undefined);
        router.refresh();
      }}
      pending={mutation.isPending}
      title="Archivar cohorte"
      variant="outline"
    >
      <Archive />
    </ConfirmAction>
  );
}

export function EnrollmentActions({
  cohortId,
  enrollmentId,
  releaseOptions,
  slug,
  status,
  version,
}: Readonly<{
  cohortId?: string | null;
  enrollmentId: string;
  releaseOptions: LearningCourseOption['releases'];
  slug: string;
  status: string;
  version: number;
}>) {
  const router = useRouter();
  const lifecycle = useEnrollmentLifecycle(slug, enrollmentId);
  const upgrade = useUpgradeEnrollment(slug, enrollmentId);
  const [release, setRelease] = useState('');

  async function change(action: 'reactivate' | 'revoke' | 'suspend') {
    await lifecycle.mutateAsync({ action, version });
    router.refresh();
  }

  return (
    <section
      aria-labelledby="enrollment-actions-title"
      className="academic-panel grid gap-5 p-5 sm:p-6"
    >
      <div>
        <h2 className="font-semibold" id="enrollment-actions-title">
          Administración de acceso
        </h2>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          Los cambios de estado son explícitos y conservan el historial de la
          matrícula.
        </p>
      </div>
      <div className="flex flex-wrap gap-3">
        {status === 'active' ? (
          <ConfirmAction
            description="El estudiante perderá temporalmente el acceso, pero su progreso y release asignado se conservarán."
            label="Suspender"
            onConfirm={() => change('suspend')}
            pending={lifecycle.isPending}
            title="Suspender matrícula"
            variant="outline"
          >
            <CirclePause />
          </ConfirmAction>
        ) : null}
        {status === 'suspended' ? (
          <ConfirmAction
            description="El estudiante recuperará el acceso si su membresía, ventana y publicación continúan vigentes."
            label="Reactivar"
            onConfirm={() => change('reactivate')}
            pending={lifecycle.isPending}
            title="Reactivar matrícula"
            variant="outline"
          >
            <CirclePlay />
          </ConfirmAction>
        ) : null}
        {status !== 'revoked' ? (
          <ConfirmAction
            description="La revocación es terminal. Para reincorporar al estudiante será necesario crear una matrícula nueva."
            label="Revocar"
            onConfirm={() => change('revoke')}
            pending={lifecycle.isPending}
            title="Revocar matrícula"
            variant="destructive"
          >
            <ShieldX />
          </ConfirmAction>
        ) : null}
      </div>
      {!cohortId && status !== 'revoked' ? (
        <div className="grid max-w-lg gap-2 border-t pt-5">
          <Label htmlFor="upgrade-release">Actualizar release asignado</Label>
          {releaseOptions.length ? (
            <>
              <p className="text-sm leading-6 text-muted-foreground">
                El progreso anterior se conserva como historial; el nuevo
                release comienza con progreso independiente.
              </p>
              <div className="flex flex-col gap-2 sm:flex-row">
                <select
                  className="academic-control"
                  id="upgrade-release"
                  onChange={(event) => setRelease(event.target.value)}
                  value={release}
                >
                  <option value="">Selecciona un release posterior</option>
                  {releaseOptions.map((option) => (
                    <option key={option.number} value={option.number}>
                      Release {option.number}
                      {option.current ? ' · actual' : ''} · {option.unitCount}{' '}
                      unidades
                    </option>
                  ))}
                </select>
                <ConfirmAction
                  description={`Se cerrará la asignación actual y la matrícula quedará fijada al release ${release || 'seleccionado'}, sin copiar el progreso anterior.`}
                  disabled={!release}
                  label="Actualizar"
                  onConfirm={async () => {
                    await upgrade.mutateAsync({
                      release: Number(release),
                      version,
                    });
                    router.refresh();
                  }}
                  pending={upgrade.isPending}
                  title="Confirmar upgrade de release"
                >
                  <CircleArrowUp />
                </ConfirmAction>
              </div>
            </>
          ) : (
            <p className="text-sm text-muted-foreground">
              No hay un release posterior disponible para esta matrícula.
            </p>
          )}
        </div>
      ) : null}
    </section>
  );
}

function ConfirmAction({
  children,
  description,
  disabled = false,
  label,
  onConfirm,
  pending,
  title,
  variant = 'default',
}: Readonly<{
  children: React.ReactNode;
  description: string;
  disabled?: boolean;
  label: string;
  onConfirm: () => Promise<void>;
  pending: boolean;
  title: string;
  variant?: 'default' | 'destructive' | 'outline';
}>) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');

  async function confirm() {
    setError('');
    try {
      await onConfirm();
      setOpen(false);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : 'No fue posible completar la acción.',
      );
    }
  }

  return (
    <AlertDialog
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) setError('');
      }}
      open={open}
    >
      <AlertDialogTrigger asChild>
        <Button disabled={disabled || pending} variant={variant}>
          {children}
          {label}
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>{title}</AlertDialogTitle>
          <AlertDialogDescription>{description}</AlertDialogDescription>
        </AlertDialogHeader>
        {error ? (
          <p aria-live="polite" className="text-sm text-destructive">
            {error}
          </p>
        ) : null}
        <AlertDialogFooter>
          <AlertDialogCancel disabled={pending}>Cancelar</AlertDialogCancel>
          <Button
            disabled={pending}
            onClick={() => void confirm()}
            variant={variant}
          >
            {pending ? <LoaderCircle className="animate-spin" /> : null}
            {label}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
