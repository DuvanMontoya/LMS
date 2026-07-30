'use client';

import { LoaderCircle, Save } from 'lucide-react';
import { useMemo, useState } from 'react';

import { Button } from '@/components/ui/button';
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
  const candidates = items.filter((item) => item.id !== targetId);
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
    <section className="academic-panel p-5">
      <h2 className="text-base font-semibold">
        Prerrequisitos de {entity === 'concept' ? 'conceptos' : 'asignaturas'}
      </h2>
      <label className="academic-field mt-4">
        {entity === 'concept' ? 'Concepto' : 'Asignatura'}
        <select
          className="academic-control"
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
      <fieldset className="mt-5">
        <legend className="mb-2 text-sm font-semibold">Requiere</legend>
        {candidates.length ? (
          <div className="divide-y border-y">
            {candidates.map((item) => {
              const link = links.find(
                (candidate) => candidate.prerequisite_id === item.id,
              );
              return (
                <div className="px-3 py-3" key={item.id}>
                  <label className="flex gap-2 text-sm font-medium">
                    <input
                      checked={Boolean(link)}
                      onChange={(event) =>
                        toggle(item.id, event.target.checked)
                      }
                      type="checkbox"
                    />
                    {item.name}
                  </label>
                  {link ? (
                    <div className="mt-3 grid gap-3 border-l-2 border-primary/20 pl-4 sm:grid-cols-2">
                      <label className="academic-field">
                        Tipo
                        <select
                          className="academic-control"
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
                      <label className="academic-field">
                        Justificación
                        <input
                          className="academic-control"
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
          </div>
        ) : (
          <p className="border-y py-4 text-sm text-muted-foreground">
            No hay otras entidades activas para relacionar.
          </p>
        )}
      </fieldset>
      <section
        className="mt-5 border-t pt-4"
        aria-labelledby="dependent-heading"
      >
        <h3 id="dependent-heading" className="font-medium">
          Es requisito de
        </h3>
        <ul className="mt-2 text-sm text-foreground/80">
          {dependentItems.length ? (
            dependentItems.map((item) => <li key={item.id}>{item.name}</li>)
          ) : (
            <li className="text-muted-foreground">
              Sin dependencias inversas.
            </li>
          )}
        </ul>
      </section>
      <Button
        className="mt-4"
        disabled={
          conceptMutation.isPending || subjectMutation.isPending || !target
        }
        onClick={() => void save()}
        type="button"
      >
        {conceptMutation.isPending || subjectMutation.isPending ? (
          <LoaderCircle className="animate-spin" />
        ) : (
          <Save />
        )}
        Guardar prerrequisitos
      </Button>
      <p
        aria-live="polite"
        className="min-h-5 pt-2 text-xs text-muted-foreground"
      >
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
