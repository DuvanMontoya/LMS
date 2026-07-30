'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import type { components } from '@/lib/api/generated/platform';
import { useCreateDiscipline, useCreateSubject } from '@/lib/catalog/hooks';

type Area = components['schemas']['Area'];
type Discipline = components['schemas']['Discipline'];

const entitySchema = z.object({
  name: z.string().trim().min(1, 'Escribe un nombre.').max(160),
  slug: z
    .string()
    .trim()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Usa minúsculas, números y guiones.')
    .max(80),
});
const disciplineSchema = entitySchema.extend({ area_id: z.string().uuid() });
const subjectSchema = entitySchema.extend({ discipline_id: z.string().uuid() });

type DisciplineValues = z.infer<typeof disciplineSchema>;
type SubjectValues = z.infer<typeof subjectSchema>;

export function StructureForms({
  areas,
  disciplines,
  embedded = false,
  mode = 'all',
  onCreated,
  slug,
}: Readonly<{
  areas: readonly Area[];
  disciplines: readonly Discipline[];
  embedded?: boolean;
  mode?: 'all' | 'discipline' | 'subject';
  onCreated?: () => void;
  slug: string;
}>) {
  const router = useRouter();
  const createDiscipline = useCreateDiscipline(slug);
  const createSubject = useCreateSubject(slug);
  const disciplineForm = useForm<DisciplineValues>({
    resolver: zodResolver(disciplineSchema),
    defaultValues: { area_id: areas[0]?.id ?? '', name: '', slug: '' },
  });
  const subjectForm = useForm<SubjectValues>({
    resolver: zodResolver(subjectSchema),
    defaultValues: {
      discipline_id: disciplines[0]?.id ?? '',
      name: '',
      slug: '',
    },
  });

  async function submitDiscipline(values: DisciplineValues) {
    await createDiscipline.mutateAsync(values);
    disciplineForm.reset({ ...values, name: '', slug: '' });
    router.refresh();
    onCreated?.();
  }
  async function submitSubject(values: SubjectValues) {
    await createSubject.mutateAsync(values);
    subjectForm.reset({ ...values, name: '', slug: '' });
    router.refresh();
    onCreated?.();
  }

  return (
    <div className={embedded ? 'grid gap-6' : 'mt-6 grid gap-6 lg:grid-cols-2'}>
      {mode === 'all' || mode === 'discipline' ? (
        <EntityForm
          embedded={embedded}
          form={disciplineForm}
          label="Área"
          onSubmit={submitDiscipline}
          options={areas.map((area) => ({ label: area.name, value: area.id }))}
          pending={createDiscipline.isPending}
          selectName="area_id"
          title="Nueva disciplina"
        />
      ) : null}
      {mode === 'all' || mode === 'subject' ? (
        <EntityForm
          embedded={embedded}
          form={subjectForm}
          label="Disciplina"
          onSubmit={submitSubject}
          options={disciplines.map((discipline) => ({
            label: discipline.name,
            value: discipline.id,
          }))}
          pending={createSubject.isPending}
          selectName="discipline_id"
          title="Nueva asignatura"
        />
      ) : null}
    </div>
  );
}

function EntityForm<T extends DisciplineValues | SubjectValues>({
  embedded,
  form,
  label,
  onSubmit,
  options,
  pending,
  selectName,
  title,
}: Readonly<{
  embedded: boolean;
  form: ReturnType<typeof useForm<T>>;
  label: string;
  onSubmit: (values: T) => Promise<void>;
  options: Array<{ label: string; value: string }>;
  pending: boolean;
  selectName: T extends DisciplineValues ? 'area_id' : 'discipline_id';
  title: string;
}>) {
  const formContent = (
    <form
      className="space-y-4"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <div className="space-y-2">
        <Label htmlFor={`${selectName}-parent`}>{label}</Label>
        <select
          className="flex h-9 w-full rounded-lg border border-input bg-background px-3 text-sm outline-none focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50"
          id={`${selectName}-parent`}
          {...form.register(selectName as never)}
        >
          <option value="">Selecciona una opción</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>
      <div className="space-y-2">
        <Label htmlFor={`${selectName}-name`}>Nombre</Label>
        <Input id={`${selectName}-name`} {...form.register('name' as never)} />
      </div>
      <div className="space-y-2">
        <Label htmlFor={`${selectName}-slug`}>Slug</Label>
        <Input
          className="font-mono"
          id={`${selectName}-slug`}
          {...form.register('slug' as never)}
        />
      </div>
      <Button disabled={pending || options.length === 0} type="submit">
        Crear
      </Button>
    </form>
  );
  if (embedded) return formContent;
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>{formContent}</CardContent>
    </Card>
  );
}
