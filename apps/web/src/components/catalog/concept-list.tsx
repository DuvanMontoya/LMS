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
import { Textarea } from '@/components/ui/textarea';
import { useSetConceptArchived, useUpdateConcept } from '@/lib/catalog/hooks';
import type { components } from '@/lib/api/generated/platform';

type Concept = components['schemas']['Concept'];

export function ConceptList({
  canManage,
  concepts,
  slug,
}: Readonly<{
  canManage: boolean;
  concepts: readonly Concept[];
  slug: string;
}>) {
  const router = useRouter();
  const setArchived = useSetConceptArchived(slug);
  const updateConcept = useUpdateConcept(slug);

  async function setStatus(concept: Concept) {
    try {
      await setArchived.mutateAsync({
        conceptId: concept.id,
        restore: concept.status === 'archived',
      });
      router.refresh();
    } catch {
      // The mutation state renders the safe API message in the list live region.
    }
  }

  return (
    <>
      <ul className="mt-6 divide-y border-y">
        {concepts.length ? (
          concepts.map((concept) => (
            <ConceptRow
              canManage={canManage}
              concept={concept}
              key={concept.id}
              onSetStatus={setStatus}
              onUpdate={async (values) => {
                await updateConcept.mutateAsync(values);
                router.refresh();
              }}
              pending={setArchived.isPending || updateConcept.isPending}
            />
          ))
        ) : (
          <li className="px-4 py-10 text-center text-sm text-muted-foreground">
            No hay conceptos registrados.
          </li>
        )}
      </ul>
      <p aria-live="polite" className="mt-2 min-h-5 text-sm text-destructive">
        {setArchived.error instanceof Error ? setArchived.error.message : ''}
        {updateConcept.error instanceof Error
          ? updateConcept.error.message
          : ''}
      </p>
    </>
  );
}

function ConceptRow({
  canManage,
  concept,
  onSetStatus,
  onUpdate,
  pending,
}: Readonly<{
  canManage: boolean;
  concept: Concept;
  onSetStatus: (concept: Concept) => Promise<void>;
  onUpdate: (values: {
    conceptId: string;
    definition: string;
    name: string;
  }) => Promise<void>;
  pending: boolean;
}>) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(concept.name);
  const [definition, setDefinition] = useState(concept.definition);
  return (
    <li className="flex flex-wrap items-start justify-between gap-4 px-1 py-5 sm:px-3">
      <div className="min-w-0 flex-1">
        <h2 className="font-semibold">{concept.name}</h2>
        <p className="mt-1 text-foreground/80">{concept.definition}</p>
        <p className="mt-2 text-sm text-muted-foreground">
          {concept.status === 'archived' ? 'Archivado' : 'Activo'}
        </p>
      </div>
      {canManage ? (
        <div className="flex flex-wrap gap-2">
          <Dialog
            onOpenChange={(open) => {
              setEditing(open);
              if (!open) {
                setName(concept.name);
                setDefinition(concept.definition);
              }
            }}
            open={editing}
          >
            <DialogTrigger asChild>
              <Button size="sm" type="button" variant="outline">
                <Pencil />
                Editar
              </Button>
            </DialogTrigger>
            <DialogContent className="sm:max-w-xl">
              <DialogHeader>
                <DialogTitle>Editar {concept.name}</DialogTitle>
                <DialogDescription>
                  Actualiza el nombre y la definición canónica del concepto.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor={`concept-name-${concept.id}`}>Nombre</Label>
                  <Input
                    id={`concept-name-${concept.id}`}
                    onChange={(event) => setName(event.target.value)}
                    value={name}
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor={`concept-definition-${concept.id}`}>
                    Definición
                  </Label>
                  <Textarea
                    className="min-h-28"
                    id={`concept-definition-${concept.id}`}
                    onChange={(event) => setDefinition(event.target.value)}
                    value={definition}
                  />
                </div>
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
                  disabled={pending || !name.trim() || !definition.trim()}
                  onClick={async () => {
                    try {
                      await onUpdate({
                        conceptId: concept.id,
                        definition,
                        name,
                      });
                      setEditing(false);
                    } catch {
                      // The parent mutation exposes the safe API message.
                    }
                  }}
                  type="button"
                >
                  Guardar cambios
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          {concept.status === 'archived' ? (
            <Button
              disabled={pending}
              onClick={() => void onSetStatus(concept)}
              size="sm"
              type="button"
              variant="outline"
            >
              <RotateCcw />
              Restaurar
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
                  <AlertDialogTitle>Archivar {concept.name}</AlertDialogTitle>
                  <AlertDialogDescription>
                    El concepto dejará de estar disponible en asociaciones
                    activas, pero conservará su historial.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Cancelar</AlertDialogCancel>
                  <AlertDialogAction
                    disabled={pending}
                    onClick={() => void onSetStatus(concept)}
                    variant="destructive"
                  >
                    Archivar concepto
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>
      ) : null}
    </li>
  );
}
