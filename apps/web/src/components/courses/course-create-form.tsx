'use client';

import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
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
    <form action={submit} className="mt-6 max-w-5xl pb-16">
      <div aria-live="polite">
        {error ? (
          <Alert className="mb-5" variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
      </div>
      <div className="border-y">
        <fieldset className="academic-form-section">
          <legend className="academic-form-legend">
            1. Identidad del curso
          </legend>
          <div className="grid gap-4 md:grid-cols-2">
            <label className="academic-field">
              Slug
              <input
                className="academic-control"
                name="slug"
                pattern="[a-z0-9-]+"
                placeholder="calculo-diferencial"
                ref={firstField}
                required
              />
            </label>
            <label className="academic-field">
              Título
              <input
                className="academic-control"
                maxLength={200}
                name="title"
                placeholder="Cálculo diferencial"
                required
              />
            </label>
            <label className="academic-field md:col-span-2">
              Subtítulo (opcional)
              <input
                className="academic-control"
                maxLength={240}
                name="subtitle"
              />
            </label>
            <label className="academic-field md:col-span-2">
              Resumen
              <textarea
                className="academic-control min-h-20"
                maxLength={1200}
                name="summary"
                required
              />
            </label>
            <label className="academic-field md:col-span-2">
              Descripción (opcional)
              <textarea
                className="academic-control min-h-24"
                maxLength={5000}
                name="description"
              />
            </label>
            <label className="academic-field max-w-xs">
              Duración estimada (minutos)
              <input
                className="academic-control"
                min={1}
                name="duration"
                type="number"
              />
            </label>
          </div>
        </fieldset>
        <fieldset className="academic-form-section">
          <legend className="academic-form-legend">
            2. Alineación con asignaturas
          </legend>
          <p className="-mt-2 mb-4 text-sm text-muted-foreground">
            Selecciona una principal y, si aportan al curso, asignaturas
            complementarias.
          </p>
          <div className="divide-y border-y">
            {subjects.map((subject) => (
              <div
                className="flex flex-col gap-3 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
                key={subject.id}
              >
                <span className="font-medium">{subject.name}</span>
                <div className="flex flex-wrap gap-x-5 gap-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium">
                    <input
                      aria-label={`Principal: ${subject.name}`}
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
                    Principal
                  </label>
                  <label className="flex items-center gap-2 text-sm">
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
              </div>
            ))}
          </div>
        </fieldset>
        <fieldset className="academic-form-section">
          <legend className="academic-form-legend">
            3. Objetivos de aprendizaje
          </legend>
          {availableObjectives.length ? (
            <ul className="divide-y border-y">
              {availableObjectives.map((objective) => (
                <li key={objective.id}>
                  <label className="flex gap-3 px-3 py-3">
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
            <p className="border-y bg-muted/30 px-4 py-5 text-sm text-muted-foreground">
              No hay objetivos activos para las asignaturas seleccionadas.
            </p>
          )}
        </fieldset>
      </div>
      <div className="mt-5 flex justify-end border-t px-2 py-3 sm:sticky sm:bottom-0 sm:z-10 sm:-mx-2 sm:bg-background/95 sm:backdrop-blur">
        <Button disabled={mutation.isPending} type="submit">
          {mutation.isPending ? 'Creando…' : 'Crear curso'}
        </Button>
      </div>
    </form>
  );
}
