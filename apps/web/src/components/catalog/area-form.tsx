'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useCreateArea } from '@/lib/catalog/hooks';

const areaSchema = z.object({
  description: z.string().trim().max(2000),
  name: z.string().trim().min(1, 'Escribe el nombre del área.').max(160),
  slug: z
    .string()
    .trim()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Usa minúsculas, números y guiones.')
    .max(80),
});

type AreaValues = z.infer<typeof areaSchema>;

export function AreaForm({ slug }: Readonly<{ slug: string }>) {
  const router = useRouter();
  const createArea = useCreateArea(slug);
  const form = useForm<AreaValues>({
    resolver: zodResolver(areaSchema),
    defaultValues: { name: '', slug: '', description: '' },
  });

  async function onSubmit(values: AreaValues) {
    await createArea.mutateAsync(values);
    form.reset();
    router.refresh();
  }

  return (
    <form
      className="mt-6 max-w-2xl space-y-4 rounded-xl border border-slate-200 bg-white p-5"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <h2 className="text-lg font-semibold text-slate-950">Nueva área</h2>
      <label className="block text-sm font-medium text-slate-900">
        Nombre
        <input
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('name')}
        />
        <span className="mt-1 block min-h-5 text-sm font-normal text-red-700">
          {form.formState.errors.name?.message}
        </span>
      </label>
      <label className="block text-sm font-medium text-slate-900">
        Slug
        <input
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('slug')}
        />
        <span className="mt-1 block min-h-5 text-sm font-normal text-red-700">
          {form.formState.errors.slug?.message}
        </span>
      </label>
      <label className="block text-sm font-medium text-slate-900">
        Descripción (opcional)
        <textarea
          className="mt-1 block min-h-20 w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('description')}
        />
      </label>
      <button
        className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={createArea.isPending}
        type="submit"
      >
        {createArea.isPending ? 'Guardando…' : 'Crear área'}
      </button>
      <p aria-live="polite" className="min-h-5 text-sm text-slate-700">
        {createArea.isSuccess ? 'Área creada.' : ''}
        {createArea.error instanceof Error ? createArea.error.message : ''}
      </p>
    </form>
  );
}
