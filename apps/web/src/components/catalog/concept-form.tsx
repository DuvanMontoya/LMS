'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { useState, type ReactNode } from 'react';
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
import { Textarea } from '@/components/ui/textarea';
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
  const [open, setOpen] = useState(false);
  const createConcept = useCreateConcept(slug);
  const form = useForm<ConceptValues>({
    resolver: zodResolver(conceptSchema),
    defaultValues: { name: '', slug: '', definition: '' },
  });

  async function onSubmit(values: ConceptValues) {
    await createConcept.mutateAsync(values);
    form.reset();
    setOpen(false);
    router.refresh();
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>Nuevo concepto</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-lg">
        <form noValidate onSubmit={form.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Crear concepto</DialogTitle>
            <DialogDescription>
              Registra una definición reutilizable dentro del currículo.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-5 grid gap-4">
            <Field label="Nombre" error={form.formState.errors.name?.message}>
              <Input autoFocus {...form.register('name')} />
            </Field>
            <Field label="Slug" error={form.formState.errors.slug?.message}>
              <Input
                placeholder="limite-de-una-funcion"
                {...form.register('slug')}
              />
            </Field>
            <Field
              label="Definición"
              error={form.formState.errors.definition?.message}
            >
              <Textarea className="min-h-28" {...form.register('definition')} />
            </Field>
          </div>
          <p aria-live="polite" className="mt-3 text-sm text-destructive">
            {createConcept.error instanceof Error
              ? createConcept.error.message
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
            <Button disabled={createConcept.isPending} type="submit">
              {createConcept.isPending ? 'Guardando…' : 'Crear concepto'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
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
    <label className="grid gap-1.5 text-sm font-medium text-foreground">
      {label}
      {children}
      {error ? (
        <span className="text-sm font-normal text-destructive">{error}</span>
      ) : null}
    </label>
  );
}
