'use client';

import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useRef, useState } from 'react';

import type { components } from '@/lib/api/generated/platform';
import {
  RevisionConflictError,
  useCreateModule,
  useCreateUnit,
  useReorderStructure,
  useReplaceUnitAlignment,
  useSetStructureArchived,
  useUpdateStructure,
} from '@/lib/courses/hooks';

type Outline = components['schemas']['Outline'];
type Objective = components['schemas']['Objective'];
type Topic = components['schemas']['Topic'];
const contentStatusLabels: Record<string, string> = {
  empty: 'Contenido vacío',
  missing: 'Sin contenido',
  ready: 'Contenido listo',
};

export function StructureEditor({
  canManage,
  courseSlug,
  objectives,
  outline,
  slug,
  topics,
}: Readonly<{
  canManage: boolean;
  courseSlug: string;
  objectives: Objective[];
  outline: Outline;
  slug: string;
  topics: Topic[];
}>) {
  const router = useRouter();
  const editable = ['draft', 'changes_requested'].includes(
    outline.revision.authoring_status,
  );
  const [modules, setModules] = useState([...outline.modules]);
  const [version, setVersion] = useState(outline.revision.lock_version);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const moduleTitle = useRef<HTMLInputElement>(null);
  const path = { courseSlug, revisionId: outline.revision.id, slug };
  const createModule = useCreateModule(path);
  const createUnit = useCreateUnit(path);
  const updateStructure = useUpdateStructure(path);
  const reorder = useReorderStructure(path);
  const archive = useSetStructureArchived(path);
  const unitAlignment = useReplaceUnitAlignment(path);

  function failed(cause: unknown) {
    setError(
      cause instanceof Error ? cause.message : 'No fue posible guardar.',
    );
    if (cause instanceof RevisionConflictError) {
      setMessage(
        'Actualiza la página cuando estés listo para reconciliar cambios.',
      );
    }
  }

  async function addModule(formData: FormData) {
    setError('');
    try {
      await createModule.mutateAsync({
        expected_version: version,
        title: String(formData.get('module-title') ?? ''),
      });
      setVersion((current) => current + 1);
      setMessage('Módulo creado.');
      moduleTitle.current?.form?.reset();
      router.refresh();
    } catch (cause) {
      failed(cause);
      moduleTitle.current?.focus();
    }
  }

  async function addUnit(moduleId: string, formData: FormData) {
    setError('');
    try {
      await createUnit.mutateAsync({
        body: {
          expected_version: version,
          title: String(formData.get('unit-title') ?? ''),
        },
        moduleId,
      });
      setVersion((current) => current + 1);
      setMessage('Unidad creada.');
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  async function editModule(moduleId: string, formData: FormData) {
    setError('');
    try {
      await updateStructure.mutateAsync({
        body: {
          description: String(formData.get('module-description') ?? ''),
          expected_version: version,
          title: String(formData.get('module-title') ?? ''),
        },
        id: moduleId,
        kind: 'module',
      });
      setVersion((current) => current + 1);
      setMessage('Módulo actualizado.');
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  async function editUnit(unitId: string, formData: FormData) {
    setError('');
    try {
      await updateStructure.mutateAsync({
        body: {
          estimated_duration_minutes: formData.get('unit-duration')
            ? Number(formData.get('unit-duration'))
            : null,
          expected_version: version,
          summary: String(formData.get('unit-summary') ?? ''),
          title: String(formData.get('unit-title') ?? ''),
        },
        id: unitId,
        kind: 'unit',
      });
      setVersion((current) => current + 1);
      setMessage('Unidad actualizada.');
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  async function moveModule(index: number, delta: number) {
    const target = index + delta;
    if (target < 0 || target >= modules.length) return;
    const next = [...modules];
    const moving = next[index];
    const displaced = next[target];
    if (!moving || !displaced) return;
    next[index] = displaced;
    next[target] = moving;
    try {
      const result = await reorder.mutateAsync({
        body: {
          expected_version: version,
          ordered_ids: next
            .filter((item) => item.status === 'active')
            .map((item) => item.id),
        },
      });
      setModules(next);
      setVersion(result.lock_version);
      setMessage(`«${moving.title}» ahora está en la posición ${target + 1}.`);
    } catch (cause) {
      failed(cause);
    }
  }

  async function moveUnit(
    moduleIndex: number,
    unitIndex: number,
    delta: number,
  ) {
    const courseModule = modules[moduleIndex];
    if (!courseModule) return;
    const units = [...courseModule.units];
    const target = unitIndex + delta;
    if (target < 0 || target >= units.length) return;
    const moving = units[unitIndex];
    const displaced = units[target];
    if (!moving || !displaced) return;
    units[unitIndex] = displaced;
    units[target] = moving;
    try {
      const result = await reorder.mutateAsync({
        body: {
          expected_version: version,
          ordered_ids: units
            .filter((item) => item.status === 'active')
            .map((item) => item.id),
        },
        moduleId: courseModule.id,
      });
      const nextModules = [...modules];
      nextModules[moduleIndex] = { ...courseModule, units };
      setModules(nextModules);
      setVersion(result.lock_version);
      setMessage(`«${moving.title}» ahora está en la posición ${target + 1}.`);
    } catch (cause) {
      failed(cause);
    }
  }

  async function setArchived(
    id: string,
    kind: 'module' | 'unit',
    restore: boolean,
  ) {
    try {
      await archive.mutateAsync({
        expectedVersion: version,
        id,
        kind,
        restore,
      });
      setVersion((current) => current + 1);
      setMessage(
        restore ? 'Elemento restaurado al final.' : 'Elemento archivado.',
      );
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  async function saveUnitAlignment(
    unitId: string,
    kind: 'objectives' | 'topics',
    formData: FormData,
  ) {
    try {
      const ids = formData.getAll(kind).map(String);
      const result = await unitAlignment.mutateAsync(
        kind === 'topics'
          ? {
              body: { expected_version: version, topic_ids: ids },
              kind,
              unitId,
            }
          : {
              body: {
                expected_version: version,
                learning_objective_ids: ids,
              },
              kind,
              unitId,
            },
      );
      setVersion(result.lock_version);
      setMessage(
        kind === 'topics'
          ? 'Temas de la unidad actualizados.'
          : 'Objetivos de la unidad actualizados.',
      );
      router.refresh();
    } catch (cause) {
      failed(cause);
    }
  }

  return (
    <section aria-labelledby="course-structure">
      <div aria-live="polite" className="mb-4 space-y-2">
        {message ? (
          <p className="rounded-lg bg-sky-50 p-3 text-sky-950">{message}</p>
        ) : null}
        {error ? (
          <p className="rounded-lg bg-red-50 p-3 text-red-950">{error}</p>
        ) : null}
      </div>
      <h2 className="text-2xl font-semibold" id="course-structure">
        Estructura del curso
      </h2>
      {!editable ? (
        <p className="mt-3 rounded-lg bg-amber-50 p-3 text-amber-950">
          Esta revisión está en estado {outline.revision.authoring_status} y es
          de solo lectura.
        </p>
      ) : null}
      {canManage && editable ? (
        <form action={addModule} className="mt-5 flex flex-wrap gap-3">
          <label className="min-w-64 flex-1 font-medium">
            Título del nuevo módulo
            <input
              className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
              maxLength={200}
              name="module-title"
              ref={moduleTitle}
              required
            />
          </label>
          <button
            className="self-end rounded-lg bg-slate-950 px-4 py-2 font-medium text-white"
            type="submit"
          >
            Añadir módulo
          </button>
        </form>
      ) : null}
      {modules.length ? (
        <ol className="mt-6 space-y-5">
          {modules.map((module, moduleIndex) => (
            <li
              className="rounded-xl border border-slate-200 bg-white p-5"
              key={module.id}
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <p className="text-sm text-slate-500">
                    Módulo {module.position ?? 'archivado'}
                  </p>
                  <h3 className="text-xl font-semibold">{module.title}</h3>
                  <p className="text-sm text-slate-600">
                    Estado: {module.status}
                  </p>
                </div>
                {canManage && editable ? (
                  <div className="flex flex-wrap gap-2">
                    <button
                      aria-label={`Mover «${module.title}» una posición arriba`}
                      className="rounded border px-3 py-2 text-sm"
                      disabled={moduleIndex === 0 || module.status !== 'active'}
                      onClick={() => moveModule(moduleIndex, -1)}
                      type="button"
                    >
                      Mover módulo arriba
                    </button>
                    <button
                      aria-label={`Mover «${module.title}» una posición abajo`}
                      className="rounded border px-3 py-2 text-sm"
                      disabled={
                        moduleIndex === modules.length - 1 ||
                        module.status !== 'active'
                      }
                      onClick={() => moveModule(moduleIndex, 1)}
                      type="button"
                    >
                      Mover módulo abajo
                    </button>
                    <button
                      className="rounded border px-3 py-2 text-sm"
                      onClick={() =>
                        setArchived(
                          module.id,
                          'module',
                          module.status === 'archived',
                        )
                      }
                      type="button"
                    >
                      {module.status === 'archived' ? 'Restaurar' : 'Archivar'}{' '}
                      módulo
                    </button>
                  </div>
                ) : null}
              </div>
              {canManage && editable && module.status === 'active' ? (
                <details className="mt-4 rounded-lg border border-slate-200 p-3">
                  <summary className="cursor-pointer font-medium">
                    Editar módulo «{module.title}»
                  </summary>
                  <form
                    action={(formData) => editModule(module.id, formData)}
                    className="mt-3 grid gap-3"
                  >
                    <label className="font-medium">
                      Nuevo título de módulo «{module.title}»
                      <input
                        className="mt-2 w-full rounded border px-3 py-2"
                        defaultValue={module.title}
                        maxLength={200}
                        name="module-title"
                        required
                      />
                    </label>
                    <label className="font-medium">
                      Descripción del módulo «{module.title}»
                      <textarea
                        className="mt-2 min-h-20 w-full rounded border px-3 py-2"
                        defaultValue={module.description}
                        maxLength={3000}
                        name="module-description"
                      />
                    </label>
                    <button
                      className="w-fit rounded border px-3 py-2 text-sm"
                      type="submit"
                    >
                      Guardar módulo «{module.title}»
                    </button>
                  </form>
                </details>
              ) : null}
              {module.units.length ? (
                <ol className="mt-4 space-y-3">
                  {module.units.map((unit, unitIndex) => (
                    <li className="rounded-lg bg-slate-50 p-4" key={unit.id}>
                      <div className="flex flex-wrap justify-between gap-3">
                        <div>
                          <h4 className="font-semibold">
                            {unit.position ?? 'Archivada'}. {unit.title}
                          </h4>
                          <p className="mt-1 text-sm text-slate-600">
                            Contenido:{' '}
                            {contentStatusLabels[unit.content_status] ??
                              unit.content_status}
                            {unit.content_version
                              ? ` · versión ${unit.content_version}`
                              : ''}
                          </p>
                          {unit.status === 'active' ? (
                            <Link
                              className="mt-2 inline-block rounded border border-sky-700 px-3 py-2 text-sm font-medium text-sky-800"
                              href={`/organizaciones/${slug}/cursos/${courseSlug}/unidades/${unit.id}/contenido`}
                            >
                              {canManage && editable
                                ? 'Editar contenido'
                                : 'Ver contenido'}
                            </Link>
                          ) : null}
                          <p className="text-sm text-slate-600">
                            Temas: {unit.topics.length} · Objetivos:{' '}
                            {unit.learning_objectives.length}
                          </p>
                          {canManage && editable && unit.status === 'active' ? (
                            <details className="mt-3">
                              <summary className="cursor-pointer font-medium">
                                Editar unidad «{unit.title}»
                              </summary>
                              <form
                                action={(formData) =>
                                  editUnit(unit.id, formData)
                                }
                                className="mt-3 grid gap-3"
                              >
                                <label className="font-medium">
                                  Nuevo título de unidad «{unit.title}»
                                  <input
                                    className="mt-2 w-full rounded border px-3 py-2"
                                    defaultValue={unit.title}
                                    maxLength={200}
                                    name="unit-title"
                                    required
                                  />
                                </label>
                                <label className="font-medium">
                                  Resumen de unidad «{unit.title}»
                                  <textarea
                                    className="mt-2 min-h-20 w-full rounded border px-3 py-2"
                                    defaultValue={unit.summary}
                                    maxLength={1200}
                                    name="unit-summary"
                                  />
                                </label>
                                <label className="font-medium">
                                  Duración de unidad «{unit.title}»
                                  <input
                                    className="mt-2 w-full rounded border px-3 py-2"
                                    defaultValue={
                                      unit.estimated_duration_minutes ?? ''
                                    }
                                    min={1}
                                    name="unit-duration"
                                    type="number"
                                  />
                                </label>
                                <button
                                  className="w-fit rounded border px-3 py-2 text-sm"
                                  type="submit"
                                >
                                  Guardar unidad «{unit.title}»
                                </button>
                              </form>
                            </details>
                          ) : null}
                          {canManage && editable && unit.status === 'active' ? (
                            <details className="mt-3">
                              <summary className="cursor-pointer font-medium">
                                Gestionar alineación de «{unit.title}»
                              </summary>
                              <form
                                action={(formData) =>
                                  saveUnitAlignment(unit.id, 'topics', formData)
                                }
                                className="mt-3"
                              >
                                <fieldset>
                                  <legend className="font-medium">Temas</legend>
                                  <div className="mt-2 space-y-2">
                                    {topics.map((topic) => (
                                      <label
                                        className="flex gap-2"
                                        key={topic.id}
                                      >
                                        <input
                                          defaultChecked={unit.topics.some(
                                            (item) =>
                                              item.topic.id === topic.id,
                                          )}
                                          name="topics"
                                          type="checkbox"
                                          value={topic.id}
                                        />
                                        {topic.title}
                                      </label>
                                    ))}
                                  </div>
                                </fieldset>
                                <button
                                  className="mt-3 rounded border px-3 py-2 text-sm"
                                  type="submit"
                                >
                                  Guardar temas de {unit.title}
                                </button>
                              </form>
                              <form
                                action={(formData) =>
                                  saveUnitAlignment(
                                    unit.id,
                                    'objectives',
                                    formData,
                                  )
                                }
                                className="mt-4"
                              >
                                <fieldset>
                                  <legend className="font-medium">
                                    Objetivos
                                  </legend>
                                  <div className="mt-2 space-y-2">
                                    {objectives.map((objective) => (
                                      <label
                                        className="flex gap-2"
                                        key={objective.id}
                                      >
                                        <input
                                          defaultChecked={unit.learning_objectives.some(
                                            (item) =>
                                              item.learning_objective.id ===
                                              objective.id,
                                          )}
                                          name="objectives"
                                          type="checkbox"
                                          value={objective.id}
                                        />
                                        {objective.code} — {objective.statement}
                                      </label>
                                    ))}
                                  </div>
                                </fieldset>
                                <button
                                  className="mt-3 rounded border px-3 py-2 text-sm"
                                  type="submit"
                                >
                                  Guardar objetivos de {unit.title}
                                </button>
                              </form>
                            </details>
                          ) : null}
                        </div>
                        {canManage && editable ? (
                          <div className="flex flex-wrap gap-2">
                            <button
                              aria-label={`Mover «${unit.title}» una posición arriba`}
                              className="rounded border px-3 py-2 text-sm"
                              disabled={
                                unitIndex === 0 || unit.status !== 'active'
                              }
                              onClick={() =>
                                moveUnit(moduleIndex, unitIndex, -1)
                              }
                              type="button"
                            >
                              Mover unidad arriba
                            </button>
                            <button
                              aria-label={`Mover «${unit.title}» una posición abajo`}
                              className="rounded border px-3 py-2 text-sm"
                              disabled={
                                unitIndex === module.units.length - 1 ||
                                unit.status !== 'active'
                              }
                              onClick={() =>
                                moveUnit(moduleIndex, unitIndex, 1)
                              }
                              type="button"
                            >
                              Mover unidad abajo
                            </button>
                            <button
                              className="rounded border px-3 py-2 text-sm"
                              onClick={() =>
                                setArchived(
                                  unit.id,
                                  'unit',
                                  unit.status === 'archived',
                                )
                              }
                              type="button"
                            >
                              {unit.status === 'archived'
                                ? 'Restaurar'
                                : 'Archivar'}{' '}
                              unidad
                            </button>
                          </div>
                        ) : null}
                      </div>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="mt-4 text-slate-600">
                  Este módulo todavía no tiene unidades.
                </p>
              )}
              {canManage && editable && module.status === 'active' ? (
                <form
                  action={(formData) => addUnit(module.id, formData)}
                  className="mt-4 flex flex-wrap gap-3 border-t border-slate-200 pt-4"
                >
                  <label className="min-w-56 flex-1 text-sm font-medium">
                    Nueva unidad en «{module.title}»
                    <input
                      className="mt-2 w-full rounded-lg border border-slate-300 px-3 py-2"
                      maxLength={200}
                      name="unit-title"
                      required
                    />
                  </label>
                  <button
                    className="self-end rounded-lg border border-slate-900 px-4 py-2 font-medium"
                    type="submit"
                  >
                    Añadir unidad
                  </button>
                </form>
              ) : null}
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-6 rounded-xl border border-dashed border-slate-300 p-6 text-slate-600">
          Aún no hay módulos. Empieza por definir la estructura del curso.
        </p>
      )}
    </section>
  );
}
