'use client';

import {
  Archive,
  ArchiveRestore,
  ArrowDown,
  ArrowUp,
  Check,
  CornerDownRight,
  LoaderCircle,
  Outdent,
  Pencil,
  X,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useId, useState } from 'react';

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
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  useMoveTopic,
  useSetTopicArchived,
  useUpdateTopic,
} from '@/lib/catalog/hooks';

export function TopicActions({
  slug,
  topic,
  topics,
}: Readonly<{
  slug: string;
  topic: {
    id: string;
    parentId?: string | undefined;
    status?: string;
    title: string;
  };
  topics: ReadonlyArray<{
    ancestorIds: readonly string[];
    id: string;
    parentId?: string | undefined;
    title: string;
  }>;
}>) {
  const router = useRouter();
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(topic.title);
  const [targetId, setTargetId] = useState('');
  const targetInputId = useId();
  const move = useMoveTopic(slug);
  const archive = useSetTopicArchived(slug);
  const update = useUpdateTopic(slug);
  const isArchived = topic.status === 'archived';
  const siblings = topics.filter(
    (candidate) => candidate.parentId === topic.parentId,
  );
  const siblingIndex = siblings.findIndex(
    (candidate) => candidate.id === topic.id,
  );
  const previousSibling = siblings[siblingIndex - 1];
  const nextSibling = siblings[siblingIndex + 1];
  const canTarget = (candidate: (typeof topics)[number]) =>
    candidate.id !== topic.id && !candidate.ancestorIds.includes(topic.id);

  async function moveTopic(
    targetId: string,
    position: 'left' | 'right' | 'last-child',
  ) {
    try {
      await move.mutateAsync({ position, targetId, topicId: topic.id });
      router.refresh();
    } catch {
      // The mutation state renders the safe server message in the live region.
    }
  }
  async function moveUnderTarget() {
    if (!targetId) return;
    await moveTopic(targetId, 'last-child');
  }
  async function changeArchive() {
    try {
      await archive.mutateAsync({ restore: isArchived, topicId: topic.id });
      router.refresh();
    } catch {
      // The mutation state renders the safe server message in the live region.
    }
  }
  async function saveTitle() {
    try {
      await update.mutateAsync({ title, topicId: topic.id });
      setEditing(false);
      router.refresh();
    } catch {
      // The mutation state renders the safe server message in the live region.
    }
  }
  return (
    <div
      aria-label={`Acciones de ${topic.title}`}
      className="flex flex-wrap items-center justify-end gap-1.5"
      role="group"
    >
      {editing ? (
        <>
          <Label className="sr-only" htmlFor={`${targetInputId}-title`}>
            Editar título de {topic.title}
          </Label>
          <Input
            className="h-8 w-48"
            id={`${targetInputId}-title`}
            onChange={(event) => setTitle(event.target.value)}
            value={title}
          />
          <Button
            aria-label={`Guardar ${topic.title}`}
            disabled={update.isPending || !title.trim()}
            onClick={() => void saveTitle()}
            size="icon-sm"
            type="button"
          >
            {update.isPending ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <Check />
            )}
          </Button>
          <Button
            aria-label="Cancelar edición"
            onClick={() => {
              setTitle(topic.title);
              setEditing(false);
            }}
            size="icon-sm"
            type="button"
            variant="ghost"
          >
            <X />
          </Button>
        </>
      ) : (
        <Button
          onClick={() => setEditing(true)}
          size="sm"
          type="button"
          variant="outline"
        >
          <Pencil />
          Editar tema
        </Button>
      )}
      {!editing ? (
        <>
          <Label className="sr-only" htmlFor={targetInputId}>
            Mover {topic.title} bajo otro tema
          </Label>
          <select
            aria-label={`Mover ${topic.title} bajo otro tema`}
            className="h-8 max-w-44 rounded-md border border-input bg-background px-2 text-xs outline-none focus-visible:border-ring focus-visible:ring-2 focus-visible:ring-ring/40"
            id={targetInputId}
            onChange={(event) => setTargetId(event.target.value)}
            value={targetId}
          >
            <option value="">Tema superior…</option>
            {topics.filter(canTarget).map((candidate) => (
              <option key={candidate.id} value={candidate.id}>
                {candidate.title}
              </option>
            ))}
          </select>
          <Button
            disabled={!targetId || move.isPending}
            onClick={() => void moveUnderTarget()}
            size="sm"
            type="button"
            variant="outline"
          >
            <CornerDownRight />
            Anidar
          </Button>
          <Button
            aria-label={`Subir ${topic.title}`}
            disabled={!previousSibling || move.isPending}
            onClick={() =>
              previousSibling && void moveTopic(previousSibling.id, 'left')
            }
            size="icon-sm"
            title="Subir"
            type="button"
            variant="ghost"
          >
            <ArrowUp />
          </Button>
          <Button
            aria-label={`Bajar ${topic.title}`}
            disabled={!nextSibling || move.isPending}
            onClick={() =>
              nextSibling && void moveTopic(nextSibling.id, 'right')
            }
            size="icon-sm"
            title="Bajar"
            type="button"
            variant="ghost"
          >
            <ArrowDown />
          </Button>
          <Button
            aria-label={`Reducir nivel de ${topic.title}`}
            disabled={!topic.parentId || move.isPending}
            onClick={() =>
              topic.parentId && void moveTopic(topic.parentId, 'right')
            }
            size="icon-sm"
            title="Reducir nivel"
            type="button"
            variant="ghost"
          >
            <Outdent />
          </Button>
        </>
      ) : null}
      {isArchived ? (
        <Button
          disabled={archive.isPending}
          onClick={() => void changeArchive()}
          size="sm"
          type="button"
          variant="outline"
        >
          <ArchiveRestore />
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
              <AlertDialogTitle>Archivar {topic.title}</AlertDialogTitle>
              <AlertDialogDescription>
                El tema y sus descendientes dejarán de estar activos. Podrás
                restaurarlos desde la vista de archivados.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancelar</AlertDialogCancel>
              <AlertDialogAction
                disabled={archive.isPending}
                onClick={() => void changeArchive()}
                variant="destructive"
              >
                {archive.isPending ? (
                  <LoaderCircle className="animate-spin" />
                ) : (
                  <Archive />
                )}
                Archivar tema
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      )}
      <span
        aria-live="polite"
        className="basis-full text-right text-xs text-destructive"
      >
        {move.error instanceof Error ? move.error.message : ''}
        {archive.error instanceof Error ? archive.error.message : ''}
        {update.error instanceof Error ? update.error.message : ''}
      </span>
    </div>
  );
}
