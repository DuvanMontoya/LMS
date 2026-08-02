'use client';

import { LoaderCircle, RefreshCw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  useCohortRosterSync,
  useConfirmCohortRosterSync,
} from '@/lib/learning/hooks';

export function CohortRosterSync({
  academicGroupName,
  academicGroupVersion,
  cohortId,
  cohortVersion,
  slug,
}: Readonly<{
  academicGroupName: string;
  academicGroupVersion: number;
  cohortId: string;
  cohortVersion: number;
  slug: string;
}>) {
  const router = useRouter();
  const preview = useCohortRosterSync(slug, cohortId);
  const confirm = useConfirmCohortRosterSync(slug, cohortId);
  const [reason, setReason] = useState('Sincronización confirmada');
  const plan = preview.data;
  const request = {
    expected_academic_group_version: academicGroupVersion,
    expected_cohort_version: cohortVersion,
    reason: reason.trim() || 'Sincronización confirmada',
  };

  async function confirmPlan() {
    await confirm.mutateAsync(request);
    router.refresh();
  }

  return (
    <section
      aria-labelledby="sync-roster-title"
      className="academic-panel mt-6 grid gap-4 p-5 sm:p-6"
    >
      <div>
        <p className="academic-kicker">Padrón sincronizado</p>
        <h2 className="text-lg font-semibold" id="sync-roster-title">
          Sincronizar desde {academicGroupName}
        </h2>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          Primero revisa el cambio. Confirmar conserva el historial: las
          matrículas manuales no se revocan por una baja de este padrón.
        </p>
      </div>
      <label className="grid gap-1.5 text-sm font-medium">
        Motivo para el historial
        <Input
          maxLength={500}
          onChange={(event) => setReason(event.target.value)}
          value={reason}
        />
      </label>
      <div className="flex flex-wrap gap-3">
        <Button
          disabled={preview.isPending || confirm.isPending}
          onClick={() => void preview.mutateAsync(request)}
          type="button"
          variant="outline"
        >
          {preview.isPending ? (
            <LoaderCircle className="animate-spin" />
          ) : (
            <RefreshCw />
          )}
          Vista previa
        </Button>
        {plan && !plan.conflicts.length ? (
          <Button
            disabled={confirm.isPending}
            onClick={() => void confirmPlan()}
            type="button"
          >
            {confirm.isPending ? (
              <LoaderCircle className="animate-spin" />
            ) : null}
            Confirmar sincronización
          </Button>
        ) : null}
      </div>
      {preview.error || confirm.error ? (
        <Alert variant="destructive">
          <AlertTitle>No se aplicó la sincronización</AlertTitle>
          <AlertDescription>
            {(preview.error ?? confirm.error)?.message}
          </AlertDescription>
        </Alert>
      ) : null}
      {plan ? (
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <SyncMetric label="Nuevas" value={plan.creates.length} />
          <SyncMetric label="Asignadas" value={plan.assigns.length} />
          <SyncMetric label="Traslados" value={plan.transfers.length} />
          <SyncMetric label="Suspensiones" value={plan.suspensions.length} />
          <SyncMetric
            label="Reactivaciones"
            value={plan.reactivations.length}
          />
          <SyncMetric
            label="Desasignaciones"
            value={plan.unassignments.length}
          />
          <SyncMetric label="Conflictos" value={plan.conflicts.length} />
        </div>
      ) : null}
      {plan?.conflicts.length ? (
        <Alert variant="destructive">
          <AlertTitle>Hay conflictos que requieren decisión manual</AlertTitle>
          <AlertDescription>
            La confirmación queda bloqueada hasta resolver las matrículas
            listadas en conflicto.
          </AlertDescription>
        </Alert>
      ) : null}
    </section>
  );
}

function SyncMetric({
  label,
  value,
}: Readonly<{ label: string; value: number }>) {
  return (
    <div className="rounded-md border bg-muted/20 px-4 py-3">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-xl font-semibold">{value}</p>
    </div>
  );
}
