'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import type { ReactNode } from 'react';
import { z } from 'zod';

import { useCreateConcept } from '@/lib/catalog/hooks';

const conceptSchema = z.object({
  definition: z.string().trim().min(1, 'Escribe una definición.').max(3000),
  name: z.string().trim().min(1, 'Escribe el nombre.').max(160),
  slug: z
    .string()
    .trim()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Usa minúsculas, números y guiones.')
    .max(80),
});

type ConceptValues = z.infer<typeof conceptSchema>;

export function ConceptForm({ slug }: Readonly<{ slug: string }>) {
  const router = useRouter();
  const createConcept = useCreateConcept(slug);
  const form = useForm<ConceptValues>({
    resolver: zodResolver(conceptSchema),
    defaultValues: { name: '', slug: '', definition: '' },
  });

  async function onSubmit(values: ConceptValues) {
    await createConcept.mutateAsync(values);
    form.reset();
    router.refresh();
  }

  return (
    <form
      className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-5"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <h2 className="text-lg font-semibold text-slate-950">Nuevo concepto</h2>
      <Field label="Nombre" error={form.formState.errors.name?.message}>
        <input
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('name')}
        />
      </Field>
      <Field label="Slug" error={form.formState.errors.slug?.message}>
        <input
          className="w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('slug')}
        />
      </Field>
      <Field
        label="Definición"
        error={form.formState.errors.definition?.message}
      >
        <textarea
          className="min-h-24 w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('definition')}
        />
      </Field>
      <button
        className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={createConcept.isPending}
        type="submit"
      >
        {createConcept.isPending ? 'Guardando…' : 'Crear concepto'}
      </button>
      <p aria-live="polite" className="min-h-5 text-sm text-slate-700">
        {createConcept.isSuccess ? 'Concepto creado.' : ''}
        {createConcept.error instanceof Error
          ? createConcept.error.message
          : ''}
      </p>
    </form>
  );
}

function Field({
  children,
  error,
  label,
}: Readonly<{
  children: ReactNode;
  error: string | undefined;
  label: string;
}>) {
  return (
    <label className="block text-sm font-medium text-slate-900">
      {label}
      <span className="mt-1 block">{children}</span>
      <span className="mt-1 block min-h-5 text-sm font-normal text-red-700">
        {error}
      </span>
    </label>
  );
}
