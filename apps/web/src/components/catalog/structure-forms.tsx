'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { z } from 'zod';

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
  slug,
}: Readonly<{
  areas: readonly Area[];
  disciplines: readonly Discipline[];
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
  }
  async function submitSubject(values: SubjectValues) {
    await createSubject.mutateAsync(values);
    subjectForm.reset({ ...values, name: '', slug: '' });
    router.refresh();
  }

  return (
    <div className="mt-6 grid gap-6 lg:grid-cols-2">
      <EntityForm
        form={disciplineForm}
        label="Área"
        onSubmit={submitDiscipline}
        options={areas.map((area) => ({ label: area.name, value: area.id }))}
        pending={createDiscipline.isPending}
        selectName="area_id"
        title="Nueva disciplina"
      />
      <EntityForm
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
    </div>
  );
}

function EntityForm<T extends DisciplineValues | SubjectValues>({
  form,
  label,
  onSubmit,
  options,
  pending,
  selectName,
  title,
}: Readonly<{
  form: ReturnType<typeof useForm<T>>;
  label: string;
  onSubmit: (values: T) => Promise<void>;
  options: Array<{ label: string; value: string }>;
  pending: boolean;
  selectName: T extends DisciplineValues ? 'area_id' : 'discipline_id';
  title: string;
}>) {
  return (
    <form
      className="space-y-3 rounded-xl border border-slate-200 bg-white p-5"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <h2 className="text-lg font-semibold text-slate-950">{title}</h2>
      <label className="block text-sm font-medium">
        {label}
        <select
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register(selectName as never)}
        >
          <option value="">Selecciona una opción</option>
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm font-medium">
        Nombre
        <input
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('name' as never)}
        />
      </label>
      <label className="block text-sm font-medium">
        Slug
        <input
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('slug' as never)}
        />
      </label>
      <button
        className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={pending || options.length === 0}
        type="submit"
      >
        Crear
      </button>
    </form>
  );
}
