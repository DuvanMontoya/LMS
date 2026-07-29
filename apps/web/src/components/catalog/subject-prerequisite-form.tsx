'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import type { components } from '@/lib/api/generated/platform';
import { useReplaceSubjectPrerequisites } from '@/lib/catalog/hooks';

type Subject = components['schemas']['Subject'];
const schema = z.object({
  prerequisiteId: z.string().uuid(),
  subjectId: z.string().uuid(),
});
type Values = z.infer<typeof schema>;

export function SubjectPrerequisiteForm({
  slug,
  subjects,
}: Readonly<{ slug: string; subjects: readonly Subject[] }>) {
  const mutation = useReplaceSubjectPrerequisites(slug);
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { prerequisiteId: '', subjectId: '' },
  });
  const selectedSubject = useWatch({
    control: form.control,
    name: 'subjectId',
  });
  async function onSubmit(values: Values) {
    await mutation.mutateAsync({
      prerequisites: [
        { kind: 'required', prerequisite_id: values.prerequisiteId },
      ],
      subjectId: values.subjectId,
    });
  }
  return (
    <form
      className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-5"
      noValidate
      onSubmit={form.handleSubmit(onSubmit)}
    >
      <h2 className="text-lg font-semibold">
        Asignar prerrequisito de asignatura
      </h2>
      <label className="block text-sm font-medium">
        Asignatura dependiente
        <select
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('subjectId')}
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
        Debe cursarse antes
        <select
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          {...form.register('prerequisiteId')}
        >
          <option value="">Selecciona un prerrequisito</option>
          {subjects
            .filter((subject) => subject.id !== selectedSubject)
            .map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
        </select>
      </label>
      <button
        className="rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={mutation.isPending || subjects.length < 2}
        type="submit"
      >
        Guardar prerrequisito
      </button>
      <p aria-live="polite" className="min-h-5 text-sm text-slate-700">
        {mutation.isSuccess ? 'Prerrequisito guardado.' : ''}
        {mutation.error instanceof Error ? mutation.error.message : ''}
      </p>
    </form>
  );
}
