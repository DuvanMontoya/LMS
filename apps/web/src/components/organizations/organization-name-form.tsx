'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { useUpdateOrganization } from '@/lib/organizations/hooks';

const nameSchema = z.object({
  name: z.string().trim().min(1, 'Escribe el nombre institucional.').max(160),
});

type NameValues = z.infer<typeof nameSchema>;

export function OrganizationNameForm({
  slug,
  name,
}: Readonly<{ slug: string; name: string }>) {
  const updateOrganization = useUpdateOrganization(slug);
  const form = useForm<NameValues>({
    resolver: zodResolver(nameSchema),
    defaultValues: { name },
  });

  useEffect(() => form.reset({ name }), [form, name]);

  async function onSubmit(values: NameValues) {
    await updateOrganization.mutateAsync(values.name);
  }

  return (
    <form
      className="mt-8 max-w-xl space-y-4"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <div>
        <label
          className="block font-medium text-slate-900"
          htmlFor="organization-name"
        >
          Nombre institucional
        </label>
        <input
          aria-describedby="organization-name-error"
          className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2"
          id="organization-name"
          {...form.register('name')}
        />
        <p
          className="mt-1 min-h-5 text-sm text-red-700"
          id="organization-name-error"
        >
          {form.formState.errors.name?.message}
        </p>
      </div>
      <button
        className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={updateOrganization.isPending}
        type="submit"
      >
        {updateOrganization.isPending ? 'Guardando…' : 'Guardar nombre'}
      </button>
      <p aria-live="polite" className="text-sm text-slate-700">
        {updateOrganization.isSuccess
          ? 'Nombre institucional actualizado.'
          : ''}
        {updateOrganization.error instanceof Error
          ? updateOrganization.error.message
          : ''}
      </p>
    </form>
  );
}
