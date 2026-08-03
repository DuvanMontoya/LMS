'use client';

import Link from 'next/link';
import { useMemo, useState } from 'react';
import { CheckCircle2, ClipboardCheck, ShieldAlert } from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';

export type AssessmentVersionOption = {
  attemptLimit: number | null;
  description: string;
  durationMinutes: number | null;
  id: string;
  label: string;
  objectiveIds: string[];
  passBasisPoints: number;
  title: string;
};

export function AssessmentActivityDialog({
  courseObjectiveIds,
  isSaving,
  onSubmit,
  options,
  slug,
}: Readonly<{
  courseObjectiveIds: string[];
  isSaving: boolean;
  onSubmit: (formData: FormData) => Promise<boolean>;
  options: AssessmentVersionOption[];
  slug: string;
}>) {
  const [open, setOpen] = useState(false);
  const [selectedId, setSelectedId] = useState('');
  const courseIds = useMemo(
    () => new Set(courseObjectiveIds),
    [courseObjectiveIds],
  );
  const compatible = options.filter(
    (option) =>
      option.objectiveIds.length > 0 &&
      option.objectiveIds.every((id) => courseIds.has(id)),
  );
  const incompatible = options.filter((option) => !compatible.includes(option));
  const selected = compatible.find((option) => option.id === selectedId);

  async function submit(formData: FormData) {
    if (await onSubmit(formData)) setOpen(false);
  }

  return (
    <Dialog onOpenChange={setOpen} open={open}>
      <DialogTrigger asChild>
        <Button
          className="h-auto justify-start gap-3 px-3 py-3"
          variant="outline"
        >
          <span className="rounded-md bg-primary/10 p-1.5 text-primary">
            <ClipboardCheck className="size-4" />
          </span>
          <span className="text-left">
            <span className="block text-sm font-semibold">Evaluación</span>
            <span className="block text-xs font-normal text-muted-foreground">
              Sólo versiones compatibles
            </span>
          </span>
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="text-xl">
            Añadir evaluación aprobada
          </DialogTitle>
          <DialogDescription>
            La plataforma copia automáticamente sus objetivos, duración,
            intentos y nota mínima. No tendrás que alinearla dos veces.
          </DialogDescription>
        </DialogHeader>
        <form action={submit} className="space-y-4">
          {compatible.length ? (
            <>
              <label className="academic-field">
                Versión compatible
                <select
                  className="academic-control"
                  name="assessment-version"
                  onChange={(event) => setSelectedId(event.target.value)}
                  required
                  value={selectedId}
                >
                  <option value="">Selecciona una evaluación</option>
                  {compatible.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              {selected ? (
                <div className="rounded-xl border bg-muted/20 p-4">
                  <div className="flex items-center justify-between gap-3">
                    <strong>{selected.title}</strong>
                    <Badge className="bg-emerald-600 text-white">
                      <CheckCircle2 />
                      Compatible
                    </Badge>
                  </div>
                  {selected.description ? (
                    <p className="mt-2 text-sm text-muted-foreground">
                      {selected.description}
                    </p>
                  ) : null}
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <Badge variant="outline">
                      {selected.durationMinutes
                        ? `${selected.durationMinutes} min`
                        : 'Sin límite'}
                    </Badge>
                    <Badge variant="outline">
                      Aprobación {selected.passBasisPoints / 100} %
                    </Badge>
                    <Badge variant="outline">
                      {selected.attemptLimit
                        ? `${selected.attemptLimit} intento${selected.attemptLimit === 1 ? '' : 's'}`
                        : 'Intentos sin límite'}
                    </Badge>
                    <Badge variant="outline">
                      {selected.objectiveIds.length} objetivos alineados
                    </Badge>
                  </div>
                </div>
              ) : null}
              <label className="flex items-center gap-2 text-sm font-medium">
                <input
                  defaultChecked
                  name="assessment-required"
                  type="checkbox"
                />
                Evaluación obligatoria
              </label>
            </>
          ) : (
            <div className="rounded-xl border border-dashed p-4">
              <p className="font-medium">No hay evaluaciones compatibles</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Alinea los objetivos del curso o aprueba una evaluación que los
                mida.
              </p>
              <Button asChild className="mt-3" size="sm" variant="outline">
                <Link href={`/organizaciones/${slug}/evaluaciones`}>
                  Gestionar evaluaciones
                </Link>
              </Button>
            </div>
          )}
          {incompatible.length ? (
            <details className="rounded-lg border px-3 py-2">
              <summary className="cursor-pointer text-sm font-medium">
                <span className="inline-flex items-center gap-2">
                  <ShieldAlert className="size-4 text-amber-700" />
                  {incompatible.length}{' '}
                  {incompatible.length === 1
                    ? 'versión no compatible'
                    : 'versiones no compatibles'}
                </span>
              </summary>
              <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                {incompatible.map((option) => (
                  <li key={option.id}>
                    • {option.label}: mide objetivos que este curso no tiene
                    alineados.
                  </li>
                ))}
              </ul>
            </details>
          ) : null}
          <DialogFooter className="mx-0 mb-0">
            <Button disabled={isSaving || !selected} type="submit">
              <ClipboardCheck />
              {isSaving ? 'Añadiendo…' : 'Añadir evaluación'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
