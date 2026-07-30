'use client';

import { FilePlus2, Send, Undo2 } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
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
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  useCreateDraftFromRelease,
  usePublishRevision,
  useWithdrawPublication,
} from '@/lib/publishing/hooks';

type PublicationPath = { slug: string; courseSlug: string };

function MutationMessage({
  error,
  success,
}: Readonly<{ error: Error | null; success?: string | undefined }>) {
  if (!error && !success) return null;
  return (
    <Alert variant={error ? 'destructive' : 'default'}>
      <AlertDescription role={error ? 'alert' : 'status'}>
        {error?.message ?? success}
      </AlertDescription>
    </Alert>
  );
}

export function PublicationActions({
  approvedRevisionId,
  canPublish,
  canWithdraw,
  courseSlug,
  lockVersion,
  slug,
  status,
}: Readonly<
  PublicationPath & {
    approvedRevisionId: string | null;
    canPublish: boolean;
    canWithdraw: boolean;
    lockVersion: number;
    status: string | null;
  }
>) {
  const router = useRouter();
  const publish = usePublishRevision({
    slug,
    courseSlug,
    revisionId: approvedRevisionId ?? '',
  });
  const withdraw = useWithdrawPublication({ slug, courseSlug });
  const [note, setNote] = useState('');
  const [withdrawOpen, setWithdrawOpen] = useState(false);
  const refresh = () => router.refresh();

  return (
    <div className="grid gap-3">
      <div className="flex flex-wrap gap-2">
        {canPublish && approvedRevisionId ? (
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button disabled={publish.isPending} size="sm">
                <Send data-icon="inline-start" />
                Publicar revisión aprobada
              </Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>Crear release inmutable</AlertDialogTitle>
                <AlertDialogDescription>
                  Se creará una versión inmutable del curso. Los cambios futuros
                  requerirán una revisión nueva y otro release.
                </AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>Cancelar</AlertDialogCancel>
                <AlertDialogAction
                  disabled={publish.isPending}
                  onClick={() =>
                    publish.mutate(lockVersion, { onSuccess: refresh })
                  }
                >
                  Confirmar publicación
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        ) : null}
        {canWithdraw && status === 'active' ? (
          <Dialog open={withdrawOpen} onOpenChange={setWithdrawOpen}>
            <DialogTrigger asChild>
              <Button disabled={withdraw.isPending} size="sm" variant="outline">
                <Undo2 data-icon="inline-start" />
                Retirar de la biblioteca
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Retirar publicación</DialogTitle>
                <DialogDescription>
                  El curso dejará de estar disponible para estudiantes. Los
                  releases históricos no se eliminarán.
                </DialogDescription>
              </DialogHeader>
              <div className="grid gap-2">
                <Label htmlFor="withdrawal-note">
                  Justificación obligatoria
                </Label>
                <Textarea
                  id="withdrawal-note"
                  maxLength={2000}
                  onChange={(event) => setNote(event.target.value)}
                  placeholder="Explica por qué se retira esta publicación."
                  value={note}
                />
              </div>
              <MutationMessage error={withdraw.error} />
              <DialogFooter>
                <DialogClose asChild>
                  <Button variant="outline">Cancelar</Button>
                </DialogClose>
                <Button
                  disabled={!note.trim() || withdraw.isPending}
                  onClick={() =>
                    withdraw.mutate(
                      {
                        expectedPublicationVersion: lockVersion,
                        note: note.trim(),
                      },
                      {
                        onSuccess: () => {
                          setWithdrawOpen(false);
                          setNote('');
                          refresh();
                        },
                      },
                    )
                  }
                  variant="destructive"
                >
                  Confirmar retiro
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        ) : null}
      </div>
      <MutationMessage
        error={publish.error}
        success={
          publish.isSuccess
            ? publish.data.already_released
              ? 'El release ya existía; no se creó un duplicado.'
              : `Release ${publish.data.release_number} creado.`
            : undefined
        }
      />
    </div>
  );
}

export function CreateDraftAction({
  canCreate,
  courseSlug,
  lockVersion,
  releaseNumber,
  slug,
}: Readonly<
  PublicationPath & {
    canCreate: boolean;
    lockVersion: number;
    releaseNumber: number;
  }
>) {
  const router = useRouter();
  const mutation = useCreateDraftFromRelease({
    slug,
    courseSlug,
    releaseNumber,
  });
  if (!canCreate) return null;
  return (
    <div className="grid gap-3">
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button disabled={mutation.isPending} size="sm" variant="outline">
            <FilePlus2 data-icon="inline-start" />
            Crear revisión desde este release
          </Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Clonar estructura y contenido</AlertDialogTitle>
            <AlertDialogDescription>
              Se creará una revisión editable nueva con la estructura y el
              contenido de este release. El release histórico no cambiará.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction
              disabled={mutation.isPending}
              onClick={() =>
                mutation.mutate(lockVersion, {
                  onSuccess: () =>
                    router.push(`/organizaciones/${slug}/cursos/${courseSlug}`),
                })
              }
            >
              Crear revisión
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <MutationMessage error={mutation.error} />
    </div>
  );
}
