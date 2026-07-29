'use client';

import { useMemo, useState } from 'react';

import {
  useReplaceConceptPrerequisites,
  useReplaceSubjectPrerequisites,
} from '@/lib/catalog/hooks';
import type { components } from '@/lib/api/generated/platform';

type EntityKind = 'concept' | 'subject';
type Item = Pick<components['schemas']['Concept'], 'id' | 'name'>;
type Link = components['schemas']['SubjectPrerequisite'];

export function PrerequisiteEditor({
  entity,
  initial,
  items,
  slug,
}: Readonly<{
  entity: EntityKind;
  initial: Record<string, Link[]>;
  items: readonly Item[];
  slug: string;
}>) {
  const conceptMutation = useReplaceConceptPrerequisites(slug);
  const subjectMutation = useReplaceSubjectPrerequisites(slug);
  const [targetId, setTargetId] = useState(items[0]?.id ?? '');
  const [linksByTarget, setLinksByTarget] = useState(initial);
  const links = linksByTarget[targetId] ?? [];
  const target = items.find((item) => item.id === targetId);
  const dependentItems = useMemo(
    () =>
      items.filter(
        (item) =>
          item.id !== targetId &&
          (linksByTarget[item.id] ?? []).some(
            (link) => link.prerequisite_id === targetId,
          ),
      ),
    [linksByTarget, items, targetId],
  );

  function updateLinks(next: Link[]) {
    setLinksByTarget((current) => ({ ...current, [targetId]: next }));
  }

  function toggle(prerequisiteId: string, enabled: boolean) {
    updateLinks(
      enabled
        ? [...links, { kind: 'required', prerequisite_id: prerequisiteId }]
        : links.filter((link) => link.prerequisite_id !== prerequisiteId),
    );
  }

  async function save() {
    if (!targetId) return;
    try {
      if (entity === 'concept') {
        await conceptMutation.mutateAsync({
          entityId: targetId,
          prerequisites: links,
        });
        return;
      }
      await subjectMutation.mutateAsync({
        prerequisites: links,
        subjectId: targetId,
      });
    } catch {
      // The mutation state renders the safe server error in the live region.
    }
  }

  return (
    <section className="mt-6 rounded-xl border border-slate-200 bg-white p-5">
      <h2 className="text-lg font-semibold">
        Prerrequisitos de {entity === 'concept' ? 'conceptos' : 'asignaturas'}
      </h2>
      <label className="mt-4 block text-sm font-medium">
        {entity === 'concept' ? 'Concepto' : 'Asignatura'}
        <select
          className="mt-1 block w-full rounded-lg border border-slate-300 px-3 py-2"
          onChange={(event) => setTargetId(event.target.value)}
          value={targetId}
        >
          {items.map((item) => (
            <option key={item.id} value={item.id}>
              {item.name}
            </option>
          ))}
        </select>
      </label>
      <fieldset className="mt-4 space-y-3">
        <legend className="font-medium">Requiere</legend>
        {items
          .filter((item) => item.id !== targetId)
          .map((item) => {
            const link = links.find(
              (candidate) => candidate.prerequisite_id === item.id,
            );
            return (
              <div
                className="rounded-lg border border-slate-200 p-3"
                key={item.id}
              >
                <label className="flex gap-2 text-sm font-medium">
                  <input
                    checked={Boolean(link)}
                    onChange={(event) => toggle(item.id, event.target.checked)}
                    type="checkbox"
                  />
                  {item.name}
                </label>
                {link ? (
                  <div className="mt-2 grid gap-2 sm:grid-cols-2">
                    <label className="text-sm">
                      Tipo
                      <select
                        className="mt-1 block w-full rounded border border-slate-300 p-2"
                        onChange={(event) =>
                          updateLinks(
                            links.map((candidate) =>
                              candidate.prerequisite_id === item.id
                                ? {
                                    ...candidate,
                                    kind: event.target.value as Link['kind'],
                                  }
                                : candidate,
                            ),
                          )
                        }
                        value={link.kind}
                      >
                        <option value="required">Obligatorio</option>
                        <option value="recommended">Recomendado</option>
                      </select>
                    </label>
                    <label className="text-sm">
                      Justificación
                      <input
                        className="mt-1 block w-full rounded border border-slate-300 p-2"
                        onChange={(event) =>
                          updateLinks(
                            links.map((candidate) =>
                              candidate.prerequisite_id === item.id
                                ? {
                                    ...candidate,
                                    rationale: event.target.value,
                                  }
                                : candidate,
                            ),
                          )
                        }
                        value={link.rationale ?? ''}
                      />
                    </label>
                  </div>
                ) : null}
              </div>
            );
          })}
      </fieldset>
      <section className="mt-4" aria-labelledby="dependent-heading">
        <h3 id="dependent-heading" className="font-medium">
          Es requisito de
        </h3>
        <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
          {dependentItems.length ? (
            dependentItems.map((item) => <li key={item.id}>{item.name}</li>)
          ) : (
            <li>Ninguna entidad activa.</li>
          )}
        </ul>
      </section>
      <button
        className="mt-4 rounded-lg bg-slate-900 px-4 py-2 font-medium text-white disabled:opacity-60"
        disabled={
          conceptMutation.isPending || subjectMutation.isPending || !target
        }
        onClick={save}
        type="button"
      >
        Guardar prerrequisitos
      </button>
      <p aria-live="polite" className="min-h-5 pt-2 text-sm text-slate-700">
        {conceptMutation.isSuccess ? 'Prerrequisitos guardados.' : ''}
        {subjectMutation.isSuccess ? 'Prerrequisitos guardados.' : ''}
        {conceptMutation.error instanceof Error
          ? conceptMutation.error.message
          : ''}
        {subjectMutation.error instanceof Error
          ? subjectMutation.error.message
          : ''}
      </p>
    </section>
  );
}
