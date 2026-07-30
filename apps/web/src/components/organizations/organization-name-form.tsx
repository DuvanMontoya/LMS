'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
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
      className="max-w-2xl"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <label
        className="block text-sm font-medium text-foreground"
        htmlFor="organization-name"
      >
        Nombre institucional
      </label>
      <div className="mt-1.5 flex items-start gap-2">
        <Input
          aria-describedby={
            form.formState.errors.name ? 'organization-name-error' : undefined
          }
          id="organization-name"
          {...form.register('name')}
        />
        <Button
          aria-label="Guardar nombre"
          disabled={updateOrganization.isPending}
          type="submit"
        >
          {updateOrganization.isPending ? 'Guardando…' : 'Guardar'}
        </Button>
      </div>
      {form.formState.errors.name?.message ? (
        <p
          className="mt-1.5 text-sm text-destructive"
          id="organization-name-error"
        >
          {form.formState.errors.name.message}
        </p>
      ) : null}
      {updateOrganization.isSuccess ||
      updateOrganization.error instanceof Error ? (
        <p aria-live="polite" className="mt-1.5 text-sm text-muted-foreground">
          {updateOrganization.isSuccess
            ? 'Nombre institucional actualizado.'
            : ''}
          {updateOrganization.error instanceof Error
            ? updateOrganization.error.message
            : ''}
        </p>
      ) : null}
    </form>
  );
}
