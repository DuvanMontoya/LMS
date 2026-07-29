'use client';

import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';

import type { components } from '@/lib/api/generated/platform';
import { useCreateCourse } from '@/lib/courses/hooks';

type Subject = components['schemas']['Subject'];
type Objective = components['schemas']['Objective'];

export function CourseCreateForm({
  objectives,
  slug,
  subjects,
}: Readonly<{
  objectives: Objective[];
  slug: string;
  subjects: Subject[];
}>) {
  const router = useRouter();
  const mutation = useCreateCourse(slug);
  const [primary, setPrimary] = useState(subjects[0]?.id ?? '');
  const [supporting, setSupporting] = useState<string[]>([]);
  const [selectedObjectives, setSelectedObjectives] = useState<string[]>([]);
  const [error, setError] = useState('');
  const firstField = useRef<HTMLInputElement>(null);
  const alignedSubjects = new Set([primary, ...supporting]);
  const availableObjectives = objectives.filter((objective) =>
    alignedSubjects.has(objective.subject_id),
  );

  async function submit(formData: FormData) {
    setError('');
    if (!primary) {
      setError('Selecciona una asignatura principal.');
      firstField.current?.focus();
      return;
    }
    try {
      const revision = await mutation.mutateAsync({
        description: String(formData.get('description') ?? ''),
        estimated_duration_minutes: formData.get('duration')
          ? Number(formData.get('duration'))
          : null,
        learning_objective_ids: selectedObjectives.filter((id) =>
          availableObjectives.some((objective) => objective.id === id),
        ),
        primary_subject_id: primary,
        slug: String(formData.get('slug') ?? ''),
        subtitle: String(formData.get('subtitle') ?? ''),
        summary: String(formData.get('summary') ?? ''),
        supporting_subject_ids: supporting,
        title: String(formData.get('title') ?? ''),
      });
      router.push(`/organizaciones/${slug}/cursos/${revision.course_slug}`);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No fue posible crear el curso.',
      );
      firstField.current?.focus();
    }
  }

  return (
    <form action={submit} className="mt-8 space-y-7">
      <div aria-live="polite">
        {error ? (
          <p className="rounded-lg border border-red-300 bg-red-50 p-3 text-red-900">
            {error}
          </p>
        ) : null}
      </div>
      <fieldset className="rounded-xl border border-slate-200 bg-white p-6">
        <legend className="px-2 text-lg font-semibold">
          Información básica
        </legend>
        <div className="grid gap-5 md:grid-cols-2">
          <label className="font-medium">
            Slug
            <input
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
              name="slug"
              pattern="[a-z0-9-]+"
              ref={firstField}
              required
            />
          </label>
          <label className="font-medium">
            Título
            <input
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
              maxLength={200}
              name="title"
              required
            />
          </label>
          <label className="font-medium md:col-span-2">
            Subtítulo opcional
            <input
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
              maxLength={240}
              name="subtitle"
            />
          </label>
          <label className="font-medium md:col-span-2">
            Resumen
            <textarea
              className="mt-2 min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2"
              maxLength={1200}
              name="summary"
              required
            />
          </label>
          <label className="font-medium md:col-span-2">
            Descripción opcional
            <textarea
              className="mt-2 min-h-28 w-full rounded-lg border border-slate-300 px-3 py-2"
              maxLength={5000}
              name="description"
            />
          </label>
          <label className="font-medium">
            Duración estimada en minutos
            <input
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
              min={1}
              name="duration"
              type="number"
            />
          </label>
        </div>
      </fieldset>
      <fieldset className="rounded-xl border border-slate-200 bg-white p-6">
        <legend className="px-2 text-lg font-semibold">
          Alineación de asignaturas
        </legend>
        <p className="mb-4 text-sm text-slate-600">
          Elige exactamente una principal y las complementarias necesarias.
        </p>
        <div className="grid gap-3 md:grid-cols-2">
          {subjects.map((subject) => (
            <div
              className="rounded-lg border border-slate-200 p-3"
              key={subject.id}
            >
              <label className="flex gap-2 font-medium">
                <input
                  checked={primary === subject.id}
                  name="primary-subject"
                  onChange={() => {
                    setPrimary(subject.id);
                    setSupporting((ids) =>
                      ids.filter((id) => id !== subject.id),
                    );
                  }}
                  type="radio"
                />
                Principal: {subject.name}
              </label>
              <label className="mt-2 flex gap-2 text-sm">
                <input
                  checked={supporting.includes(subject.id)}
                  disabled={primary === subject.id}
                  onChange={(event) =>
                    setSupporting((ids) =>
                      event.target.checked
                        ? [...ids, subject.id]
                        : ids.filter((id) => id !== subject.id),
                    )
                  }
                  type="checkbox"
                />
                Complementaria
              </label>
            </div>
          ))}
        </div>
      </fieldset>
      <fieldset className="rounded-xl border border-slate-200 bg-white p-6">
        <legend className="px-2 text-lg font-semibold">
          Objetivos de aprendizaje
        </legend>
        {availableObjectives.length ? (
          <ul className="space-y-3">
            {availableObjectives.map((objective) => (
              <li key={objective.id}>
                <label className="flex gap-3 rounded-lg border border-slate-200 p-3">
                  <input
                    checked={selectedObjectives.includes(objective.id)}
                    onChange={(event) =>
                      setSelectedObjectives((ids) =>
                        event.target.checked
                          ? [...ids, objective.id]
                          : ids.filter((id) => id !== objective.id),
                      )
                    }
                    type="checkbox"
                  />
                  <span>
                    <strong>{objective.code}</strong> — {objective.statement}
                  </span>
                </label>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-slate-600">
            No hay objetivos activos para las asignaturas seleccionadas.
          </p>
        )}
      </fieldset>
      <button
        className="rounded-lg bg-slate-950 px-5 py-3 font-semibold text-white disabled:opacity-60"
        disabled={mutation.isPending}
        type="submit"
      >
        {mutation.isPending ? 'Creando…' : 'Crear curso'}
      </button>
    </form>
  );
}
