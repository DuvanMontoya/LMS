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
import { Textarea } from '@/components/ui/textarea';
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
  selectedSubjectId,
  slug,
  subjects,
}: Readonly<{
  selectedSubjectId?: string | undefined;
  slug: string;
  subjects: readonly Subject[];
}>) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const createObjective = useCreateObjective(slug);
  const form = useForm<ObjectiveValues>({
    resolver: zodResolver(objectiveSchema),
    defaultValues: {
      code: '',
      cognitive_level: '',
      description: '',
      statement: '',
      subject_id: selectedSubjectId ?? subjects[0]?.id ?? '',
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
    setOpen(false);
    router.refresh();
  }
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button disabled={subjects.length === 0}>Nuevo objetivo</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-xl">
        <form noValidate onSubmit={form.handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Crear objetivo de aprendizaje</DialogTitle>
            <DialogDescription>
              Formula un resultado observable y vincúlalo con una asignatura.
            </DialogDescription>
          </DialogHeader>
          <div className="mt-5 grid gap-4 sm:grid-cols-2">
            <label className="academic-field sm:col-span-2">
              Asignatura
              <select
                className="academic-control"
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
            <label className="academic-field">
              Código
              <Input placeholder="MAT.CAL.01" {...form.register('code')} />
            </label>
            <label className="academic-field">
              Nivel cognitivo
              <select
                className="academic-control"
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
            <label className="academic-field sm:col-span-2">
              Enunciado
              <Textarea className="min-h-24" {...form.register('statement')} />
            </label>
            <label className="academic-field sm:col-span-2">
              Descripción (opcional)
              <Textarea
                className="min-h-20"
                {...form.register('description')}
              />
            </label>
          </div>
          <p aria-live="polite" className="mt-3 text-sm text-destructive">
            {createObjective.error instanceof Error
              ? createObjective.error.message
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
            <Button disabled={createObjective.isPending} type="submit">
              {createObjective.isPending ? 'Guardando…' : 'Crear objetivo'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
