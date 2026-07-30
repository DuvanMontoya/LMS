'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import type { components } from '@/lib/api/generated/platform';
import { useReplaceCourseAlignment } from '@/lib/courses/hooks';

type Outline = components['schemas']['Outline'];
type Subject = components['schemas']['Subject'];
type Objective = components['schemas']['Objective'];

export function AlignmentEditor({
  canManage,
  courseSlug,
  objectives,
  outline,
  slug,
  subjects,
}: Readonly<{
  canManage: boolean;
  courseSlug: string;
  objectives: Objective[];
  outline: Outline;
  slug: string;
  subjects: Subject[];
}>) {
  const router = useRouter();
  const editable =
    canManage &&
    ['draft', 'changes_requested'].includes(outline.revision.authoring_status);
  const initialPrimary =
    outline.subjects.find((item) => item.alignment_type === 'primary')?.subject
      .id ?? '';
  const [primary, setPrimary] = useState(initialPrimary);
  const [supporting, setSupporting] = useState(
    outline.subjects
      .filter((item) => item.alignment_type === 'supporting')
      .map((item) => item.subject.id),
  );
  const [selectedObjectives, setSelectedObjectives] = useState(
    outline.learning_objectives.map((item) => item.learning_objective.id),
  );
  const [version, setVersion] = useState(outline.revision.lock_version);
  const [status, setStatus] = useState('');
  const mutation = useReplaceCourseAlignment({
    courseSlug,
    revisionId: outline.revision.id,
    slug,
  });
  const alignedSubjectIds = new Set([primary, ...supporting]);
  const visibleObjectives = objectives.filter((objective) =>
    alignedSubjectIds.has(objective.subject_id),
  );

  async function saveSubjects() {
    if (!primary) {
      setStatus('Selecciona una asignatura principal.');
      return;
    }
    try {
      const result = await mutation.mutateAsync({
        body: {
          expected_version: version,
          primary_subject_id: primary,
          supporting_subject_ids: supporting,
        },
        kind: 'subjects',
      });
      setVersion(result.lock_version);
      setStatus('Asignaturas actualizadas.');
      router.refresh();
    } catch (cause) {
      setStatus(
        cause instanceof Error ? cause.message : 'No fue posible guardar.',
      );
    }
  }

  async function saveObjectives() {
    try {
      const result = await mutation.mutateAsync({
        body: {
          expected_version: version,
          learning_objective_ids: selectedObjectives.filter((id) =>
            visibleObjectives.some((objective) => objective.id === id),
          ),
        },
        kind: 'objectives',
      });
      setVersion(result.lock_version);
      setStatus('Objetivos actualizados.');
      router.refresh();
    } catch (cause) {
      setStatus(
        cause instanceof Error ? cause.message : 'No fue posible guardar.',
      );
    }
  }

  return (
    <section aria-labelledby="alignment-title" className="border-t pt-5">
      <h2 className="text-base font-semibold" id="alignment-title">
        Alineación curricular
      </h2>
      <p aria-live="polite" className="mt-3 text-sm text-foreground/80">
        {status}
      </p>
      <fieldset className="mt-5" disabled={!editable}>
        <legend className="font-semibold">
          Asignatura principal y complementarias
        </legend>
        <div className="mt-3 divide-y border-y">
          {subjects.map((subject) => (
            <div
              className="flex flex-col gap-3 px-3 py-3 sm:flex-row sm:items-center sm:justify-between"
              key={subject.id}
            >
              <span className="font-medium">{subject.name}</span>
              <div className="flex gap-5">
                <label className="flex gap-2">
                  <input
                    checked={primary === subject.id}
                    name="workspace-primary"
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
                <label className="mt-2 flex gap-2 text-sm">
                  <input
                    checked={supporting.includes(subject.id)}
                    disabled={!editable || primary === subject.id}
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
        {editable ? (
          <Button
            className="mt-4"
            onClick={() => void saveSubjects()}
            type="button"
            variant="outline"
          >
            Guardar asignaturas
          </Button>
        ) : null}
      </fieldset>
      <fieldset className="mt-7" disabled={!editable}>
        <legend className="font-semibold">Objetivos de la revisión</legend>
        {visibleObjectives.length ? (
          <ul className="mt-3 divide-y border-y">
            {visibleObjectives.map((objective) => (
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
          <p className="mt-3 text-muted-foreground">
            No hay objetivos para las asignaturas alineadas.
          </p>
        )}
        {editable ? (
          <Button
            className="mt-4"
            onClick={() => void saveObjectives()}
            type="button"
            variant="outline"
          >
            Guardar objetivos
          </Button>
        ) : null}
      </fieldset>
    </section>
  );
}
