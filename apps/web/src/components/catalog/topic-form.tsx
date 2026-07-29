'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

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
    router.refresh();
  }
  return (
    <form
      className="mt-5 space-y-3"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <h3 className="text-lg font-semibold">Nuevo tema</h3>
      <label className="block text-sm font-medium">
        Tema padre
        <select
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
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
      <label className="block text-sm font-medium">
        Título
        <input
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('title')}
        />
      </label>
      <label className="block text-sm font-medium">
        Slug
        <input
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('slug')}
        />
      </label>
      <button
        className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={createTopic.isPending}
        type="submit"
      >
        {createTopic.isPending ? 'Guardando…' : 'Crear tema'}
      </button>
    </form>
  );
}
