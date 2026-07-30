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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  useSetNamedEntityArchived,
  useUpdateNamedEntity,
} from '@/lib/catalog/hooks';

type NamedEntityKind = 'area' | 'discipline' | 'subject';

export function NamedEntityActions({
  entity,
  kind,
  slug,
}: Readonly<{
  entity: { id: string; name: string; status: string };
  kind: NamedEntityKind;
  slug: string;
}>) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(entity.name);
  const update = useUpdateNamedEntity(slug);
  const archive = useSetNamedEntityArchived(slug);
  const noun =
    kind === 'area'
      ? 'área'
      : kind === 'discipline'
        ? 'disciplina'
        : 'asignatura';
  const isArchived = entity.status === 'archived';

  async function save() {
    try {
      await update.mutateAsync({ entityId: entity.id, kind, name });
      setEditing(false);
      router.refresh();
    } catch {
      // The API message below is safer than exposing transport details.
    }
  }

  async function setStatus() {
    try {
      await archive.mutateAsync({
        entityId: entity.id,
        kind,
        restore: isArchived,
      });
      router.refresh();
    } catch {
      // The API message below is safer than exposing transport details.
    }
  }

  return (
    <section
      aria-label={`Acciones de ${entity.name}`}
      className="flex flex-wrap items-center gap-2"
    >
      <Dialog
        open={editing}
        onOpenChange={(open) => {
          setEditing(open);
          if (!open) setName(entity.name);
        }}
      >
        <DialogTrigger asChild>
          <Button size="sm" type="button" variant="outline">
            <Pencil data-icon="inline-start" />
            Editar {noun}
          </Button>
        </DialogTrigger>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Editar {noun}</DialogTitle>
            <DialogDescription>
              Actualiza el nombre visible de {entity.name}. Su identidad y slug
              permanecen intactos.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-2">
            <Label htmlFor={`entity-name-${entity.id}`}>Nombre</Label>
            <Input
              autoFocus
              id={`entity-name-${entity.id}`}
              onChange={(event) => setName(event.target.value)}
              value={name}
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
              disabled={update.isPending || !name.trim()}
              onClick={save}
              type="button"
            >
              Guardar nombre
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {isArchived ? (
        <Button
          disabled={archive.isPending}
          onClick={setStatus}
          size="sm"
          type="button"
          variant="outline"
        >
          <RotateCcw data-icon="inline-start" />
          Restaurar {noun}
        </Button>
      ) : (
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button
              disabled={archive.isPending}
              size="sm"
              type="button"
              variant="ghost"
            >
              <Archive data-icon="inline-start" />
              Archivar {noun}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Archivar {entity.name}</AlertDialogTitle>
              <AlertDialogDescription>
                Se ocultará de los flujos activos, pero conservará su identidad
                y sus relaciones históricas.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction onClick={setStatus}>
                Archivar {noun}
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
      <p aria-live="polite" className="basis-full text-sm text-destructive">
        {update.error instanceof Error ? update.error.message : ''}
        {archive.error instanceof Error ? archive.error.message : ''}
      </p>
    </section>
  );
}
