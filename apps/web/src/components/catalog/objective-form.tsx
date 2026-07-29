'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import type { components } from '@/lib/api/generated/platform';
import { useCreateObjective } from '@/lib/catalog/hooks';

type Subject = components['schemas']['Subject'];
const objectiveSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(/^[A-Z0-9_.-]+$/)
    .max(32),
  statement: z.string().trim().min(1).max(1200),
  description: z.string().trim().max(2000).optional(),
  cognitive_level: z
    .enum(['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create'])
    .or(z.literal(''))
    .optional(),
  subject_id: z.string().uuid(),
});
type ObjectiveValues = z.infer<typeof objectiveSchema>;

export function ObjectiveForm({
  slug,
  subjects,
}: Readonly<{ slug: string; subjects: readonly Subject[] }>) {
  const router = useRouter();
  const createObjective = useCreateObjective(slug);
  const form = useForm<ObjectiveValues>({
    resolver: zodResolver(objectiveSchema),
    defaultValues: {
      code: '',
      cognitive_level: '',
      description: '',
      statement: '',
      subject_id: subjects[0]?.id ?? '',
    },
  });
  async function onSubmit(values: ObjectiveValues) {
    const { cognitive_level, description, ...input } = values;
    await createObjective.mutateAsync({
      ...input,
      ...(description ? { description } : {}),
      ...(cognitive_level ? { cognitive_level } : {}),
    });
    form.reset({ ...values, code: '', statement: '' });
    router.refresh();
  }
  return (
    <form
      className="mt-6 space-y-3 rounded-xl border border-slate-200 bg-white p-5"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <h2 className="text-lg font-semibold">Nuevo objetivo</h2>
      <label className="block text-sm font-medium">
        Asignatura
        <select
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('subject_id')}
        >
          <option value="">Selecciona una asignatura</option>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm font-medium">
        Código
        <input
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('code')}
        />
      </label>
      <label className="block text-sm font-medium">
        Enunciado
        <textarea
          className="mt-1 block min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('statement')}
        />
      </label>
      <label className="block text-sm font-medium">
        Descripción (opcional)
        <textarea
          className="mt-1 block min-h-20 w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('description')}
        />
      </label>
      <label className="block text-sm font-medium">
        Nivel cognitivo (opcional)
        <select
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('cognitive_level')}
        >
          <option value="">Sin especificar</option>
          <option value="remember">Recordar</option>
          <option value="understand">Comprender</option>
          <option value="apply">Aplicar</option>
          <option value="analyze">Analizar</option>
          <option value="evaluate">Evaluar</option>
          <option value="create">Crear</option>
        </select>
      </label>
      <button
        className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={createObjective.isPending || subjects.length === 0}
        type="submit"
      >
        Crear objetivo
      </button>
    </form>
  );
}
