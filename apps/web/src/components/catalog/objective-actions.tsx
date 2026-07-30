'use client';

import { Archive, Pencil, RotateCcw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

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
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { components } from '@/lib/api/generated/platform';
import {
  useSetObjectiveArchived,
  useUpdateObjective,
} from '@/lib/catalog/hooks';

type Objective = components['schemas']['Objective'];

export function ObjectiveActions({
  objective,
  slug,
}: Readonly<{ objective: Objective; slug: string }>) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [statement, setStatement] = useState(objective.statement);
  const update = useUpdateObjective(slug);
  const archive = useSetObjectiveArchived(slug);
  const isArchived = objective.status === 'archived';

  async function save() {
    try {
      await update.mutateAsync({ objectiveId: objective.id, statement });
      setEditing(false);
      router.refresh();
    } catch {
      // The safe API message is rendered in the live region.
    }
  }

  async function setStatus() {
    try {
      await archive.mutateAsync({
        objectiveId: objective.id,
        restore: isArchived,
      });
      router.refresh();
    } catch {
      // The safe API message is rendered in the live region.
    }
  }

  return (
    <section
      aria-label={`Acciones de ${objective.code}`}
      className="mt-3 flex flex-wrap items-center gap-2"
    >
      <Dialog
        onOpenChange={(open) => {
          setEditing(open);
          if (!open) setStatement(objective.statement);
        }}
        open={editing}
      >
        <DialogTrigger asChild>
          <Button size="sm" type="button" variant="outline">
            <Pencil />
            Editar objetivo
          </Button>
        </DialogTrigger>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>Editar {objective.code}</DialogTitle>
            <DialogDescription>
              Ajusta el resultado observable sin cambiar su identidad.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor={`objective-statement-${objective.id}`}>
              Enunciado
            </Label>
            <Textarea
              className="min-h-28"
              id={`objective-statement-${objective.id}`}
              onChange={(event) => setStatement(event.target.value)}
              value={statement}
            />
          </div>
          <DialogFooter>
            <Button
              onClick={() => setEditing(false)}
              type="button"
              variant="outline"
            >
              Cancelar
            </Button>
            <Button
              disabled={update.isPending || !statement.trim()}
              onClick={() => void save()}
              type="button"
            >
              {update.isPending ? 'Guardando…' : 'Guardar cambios'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {isArchived ? (
        <Button
          disabled={archive.isPending}
          onClick={() => void setStatus()}
          size="sm"
          type="button"
          variant="outline"
        >
          <RotateCcw />
          Restaurar objetivo
        </Button>
      ) : (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button size="sm" type="button" variant="ghost">
              <Archive />
              Archivar
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Archivar {objective.code}</AlertDialogTitle>
              <AlertDialogDescription>
                El objetivo dejará de estar disponible en las alineaciones
                activas, pero conservará su historial.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction
                disabled={archive.isPending}
                onClick={() => void setStatus()}
                variant="destructive"
              >
                Archivar objetivo
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
      <p aria-live="polite" className="basis-full text-xs text-destructive">
        {update.error instanceof Error ? update.error.message : ''}
        {archive.error instanceof Error ? archive.error.message : ''}
      </p>
    </section>
  );
}
