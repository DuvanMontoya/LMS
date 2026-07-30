'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { useState } from 'react';
import { z } from 'zod';

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
import { useCreateTopic } from '@/lib/catalog/hooks';

const topicSchema = z.object({
  parent_id: z.string().uuid().optional().or(z.literal('')),
  slug: z
    .string()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/)
    .max(80),
  title: z.string().trim().min(1).max(160),
});
type TopicValues = z.infer<typeof topicSchema>;

export function TopicForm({
  topics,
  slug,
  subjectId,
}: Readonly<{
  slug: string;
  subjectId: string;
  topics: ReadonlyArray<{ id: string; title: string }>;
}>) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const createTopic = useCreateTopic(slug, subjectId);
  const form = useForm<TopicValues>({
    resolver: zodResolver(topicSchema),
    defaultValues: { title: '', slug: '', parent_id: '' },
  });
  async function onSubmit(values: TopicValues) {
    const input = values.parent_id
      ? { parent_id: values.parent_id, slug: values.slug, title: values.title }
      : { slug: values.slug, title: values.title };
    await createTopic.mutateAsync(input);
    form.reset();
    setOpen(false);
    router.refresh();
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Nuevo tema</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <form noValidate onSubmit={form.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Crear tema</DialogTitle>
            <DialogDescription>
              Añádelo a la raíz o ubícalo bajo un tema existente.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-5 grid gap-4">
            <label className="academic-field">
              Tema padre
              <select
                className="academic-control"
                {...form.register('parent_id')}
              >
                <option value="">Sin padre (tema raíz)</option>
                {topics.map((topic) => (
                  <option key={topic.id} value={topic.id}>
                    {topic.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="academic-field">
              Título
              <Input autoFocus {...form.register('title')} />
            </label>
            <label className="academic-field">
              Slug
              <Input
                placeholder="limites-y-continuidad"
                {...form.register('slug')}
              />
            </label>
          </div>
          <p aria-live="polite" className="mt-3 text-sm text-destructive">
            {createTopic.error instanceof Error
              ? createTopic.error.message
              : ''}
          </p>
          <DialogFooter className="mt-5">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
            >
              Cancelar
            </Button>
            <Button disabled={createTopic.isPending} type="submit">
              {createTopic.isPending ? 'Guardando…' : 'Crear tema'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
