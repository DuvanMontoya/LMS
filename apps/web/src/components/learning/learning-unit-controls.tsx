'use client';

import type { components } from '@/lib/api/generated/platform';
import {
  AlertCircle,
  CheckCircle2,
  LoaderCircle,
  RotateCcw,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { LearningApiError } from '@/lib/learning/api';
import {
  useCompleteUnit,
  useOpenUnit,
  useReopenUnit,
} from '@/lib/learning/hooks';

export function LearningUnitControls({
  enrollmentId,
  progress,
  slug,
  unitId,
  unitStatus,
}: Readonly<{
  enrollmentId: string;
  progress: components['schemas']['Progress'];
  slug: string;
  unitId: string;
  unitStatus: string;
}>) {
  const router = useRouter();
  const path = { enrollmentId, slug, unitId };
  const openMutation = useOpenUnit(path);
  const completeMutation = useCompleteUnit(path);
  const reopenMutation = useReopenUnit(path);
  const [notice, setNotice] = useState<string>();

  useEffect(() => {
    openMutation.mutate(undefined, {
      onSuccess: () => router.refresh(),
    });
    // La apertura se registra una vez después del primer render correcto.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enrollmentId, slug, unitId]);

  const mutation =
    unitStatus === 'completed' ? reopenMutation : completeMutation;
  const effectiveProgressVersion =
    openMutation.data?.progress_version ?? progress.progress_version;

  async function toggleCompletion() {
    setNotice(undefined);
    try {
      await mutation.mutateAsync(effectiveProgressVersion);
      setNotice(
        unitStatus === 'completed'
          ? 'La unidad volvió a quedar pendiente.'
          : 'La unidad quedó completada.',
      );
      router.refresh();
    } catch (error) {
      if (
        error instanceof LearningApiError &&
        error.code === 'learning_progress_conflict'
      ) {
        setNotice(
          'El progreso cambió en otra pestaña o dispositivo. Se actualizó la información antes de continuar.',
        );
        router.refresh();
        return;
      }
      setNotice(
        error instanceof Error
          ? error.message
          : 'No fue posible actualizar la unidad.',
      );
    }
  }

  return (
    <div className="grid gap-3">
      <Button
        disabled={mutation.isPending || openMutation.isPending}
        onClick={toggleCompletion}
        type="button"
        variant={unitStatus === 'completed' ? 'outline' : 'default'}
      >
        {mutation.isPending ? (
          <LoaderCircle className="animate-spin motion-reduce:animate-none" />
        ) : unitStatus === 'completed' ? (
          <RotateCcw />
        ) : (
          <CheckCircle2 />
        )}
        {unitStatus === 'completed'
          ? 'Marcar unidad como pendiente'
          : 'Marcar unidad como completada'}
      </Button>
      {notice ? (
        <Alert aria-live="polite">
          <AlertCircle />
          <AlertTitle>Estado del progreso</AlertTitle>
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      ) : null}
    </div>
  );
}
