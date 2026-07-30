'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
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

export function AreaForm({
  embedded = false,
  onCreated,
  slug,
}: Readonly<{
  embedded?: boolean;
  onCreated?: () => void;
  slug: string;
}>) {
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
    onCreated?.();
  }

  const formContent = (
    <form
      className="grid gap-5 sm:grid-cols-2"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <div className="space-y-2">
        <Label htmlFor="area-name">Nombre</Label>
        <Input id="area-name" {...form.register('name')} />
        <p className="min-h-5 text-sm text-destructive">
          {form.formState.errors.name?.message}
        </p>
      </div>
      <div className="space-y-2">
        <Label htmlFor="area-slug">Slug</Label>
        <Input
          className="font-mono"
          id="area-slug"
          {...form.register('slug')}
        />
        <p className="min-h-5 text-sm text-destructive">
          {form.formState.errors.slug?.message}
        </p>
      </div>
      <div className="space-y-2 sm:col-span-2">
        <Label htmlFor="area-description">Descripción (opcional)</Label>
        <Textarea
          className="min-h-24"
          id="area-description"
          {...form.register('description')}
        />
      </div>
      <div className="flex flex-wrap items-center gap-4 sm:col-span-2">
        <Button disabled={createArea.isPending} type="submit">
          {createArea.isPending ? 'Guardando…' : 'Crear área'}
        </Button>
        <p aria-live="polite" className="min-h-5 text-sm text-muted-foreground">
          {createArea.isSuccess ? 'Área creada.' : ''}
          {createArea.error instanceof Error ? createArea.error.message : ''}
        </p>
      </div>
    </form>
  );
  if (embedded) return formContent;
  return (
    <Card className="mt-6 max-w-3xl">
      <CardHeader>
        <CardTitle>Nueva área</CardTitle>
        <p className="text-sm text-muted-foreground">
          Nivel superior para agrupar disciplinas relacionadas.
        </p>
      </CardHeader>
      <CardContent>{formContent}</CardContent>
    </Card>
  );
}
