'use client';

import {
  ArrowDown,
  ArrowUp,
  Check,
  GripVertical,
  ImagePlus,
  Plus,
  Trash2,
} from 'lucide-react';

import { AssetPickerDialog } from '@/components/assets/asset-picker-dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';

export type ChoiceMediaDraft = {
  alt_text: string;
  asset_version_id: string;
  caption?: string;
  kind: 'image';
  long_description?: string;
};

export type QuestionChoiceDraft = {
  id: string;
  label: string;
  mathLatex: string;
  media?: ChoiceMediaDraft;
};

export function choiceMediaFromAssetNode(
  node: Record<string, unknown>,
): ChoiceMediaDraft | null {
  if (
    node.type !== 'imageAsset' ||
    !node.attrs ||
    typeof node.attrs !== 'object'
  )
    return null;
  const attrs = node.attrs as Record<string, unknown>;
  const assetVersionId = String(attrs.assetVersionId ?? '');
  const altText = String(attrs.altText ?? '').trim();
  if (!assetVersionId || !altText) return null;
  const caption = String(attrs.caption ?? '').trim();
  return {
    alt_text: altText,
    asset_version_id: assetVersionId,
    ...(caption ? { caption } : {}),
    kind: 'image',
  };
}

function nextOptionId(options: readonly QuestionChoiceDraft[]) {
  let suffix = options.length + 1;
  while (options.some((option) => option.id === `o${suffix}`)) suffix += 1;
  return `o${suffix}`;
}

export function QuestionChoiceEditor({
  accepted,
  multiple,
  onAcceptedChange,
  onChange,
  onRationaleChange,
  options,
  rationales,
  responseMode = 'selection',
  slug,
}: Readonly<{
  accepted: readonly string[];
  multiple: boolean;
  onAcceptedChange: (ids: string[]) => void;
  onChange: (options: QuestionChoiceDraft[]) => void;
  onRationaleChange: (id: string, value: string) => void;
  options: readonly QuestionChoiceDraft[];
  rationales: Readonly<Record<string, string>>;
  responseMode?: 'selection' | 'sequence';
  slug: string;
}>) {
  function update(id: string, patch: Partial<QuestionChoiceDraft>) {
    onChange(
      options.map((option) =>
        option.id === id ? { ...option, ...patch } : option,
      ),
    );
  }

  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= options.length) return;
    const next = [...options];
    [next[index], next[target]] = [next[target]!, next[index]!];
    onChange(next);
  }

  function toggleCorrect(id: string) {
    if (!multiple) {
      onAcceptedChange([id]);
      return;
    }
    const selected = new Set(accepted);
    if (selected.has(id)) selected.delete(id);
    else selected.add(id);
    onAcceptedChange(
      options
        .map((option) => option.id)
        .filter((optionId) => selected.has(optionId)),
    );
  }

  return (
    <div className="assessment-choice-studio">
      <header>
        <h3>Opciones de respuesta</h3>
        <span>{options.length} opciones</span>
      </header>
      <ol className="assessment-choice-list">
        {options.map((option, index) => {
          const correct = accepted.includes(option.id);
          return (
            <li data-correct={correct} key={option.id}>
              <div className="assessment-choice-card__identity">
                <GripVertical aria-hidden="true" />
                <span>{String.fromCharCode(65 + index)}</span>
                {responseMode === 'selection' ? (
                  <button
                    aria-pressed={correct}
                    className="assessment-choice-correct"
                    data-correct={correct}
                    onClick={() => toggleCorrect(option.id)}
                    type="button"
                  >
                    <Check />{' '}
                    {correct ? 'Respuesta correcta' : 'Marcar como correcta'}
                  </button>
                ) : (
                  <strong className="assessment-choice-position">
                    Posición correcta {index + 1}
                  </strong>
                )}
                <div className="assessment-choice-card__actions">
                  <Button
                    aria-label={`Subir opción ${index + 1}`}
                    disabled={index === 0}
                    onClick={() => move(index, -1)}
                    size="icon-sm"
                    type="button"
                    variant="ghost"
                  >
                    <ArrowUp />
                  </Button>
                  <Button
                    aria-label={`Bajar opción ${index + 1}`}
                    disabled={index === options.length - 1}
                    onClick={() => move(index, 1)}
                    size="icon-sm"
                    type="button"
                    variant="ghost"
                  >
                    <ArrowDown />
                  </Button>
                  <Button
                    aria-label={`Eliminar opción ${index + 1}`}
                    disabled={options.length <= 2}
                    onClick={() => {
                      onChange(options.filter((item) => item.id !== option.id));
                      onAcceptedChange(
                        accepted.filter((id) => id !== option.id),
                      );
                    }}
                    size="icon-sm"
                    type="button"
                    variant="ghost"
                  >
                    <Trash2 />
                  </Button>
                  <AssetPickerDialog
                    allowDecorative={false}
                    allowedKinds={['image']}
                    iconOnly
                    onInsert={(node) => {
                      const media = choiceMediaFromAssetNode(node);
                      if (media) update(option.id, { media });
                    }}
                    slug={slug}
                    triggerLabel={`Añadir imagen a la opción ${index + 1}`}
                  />
                </div>
              </div>
              <div className="assessment-choice-card__body">
                <label>
                  <span>Contenido textual</span>
                  <Textarea
                    aria-label={`Texto de la opción ${index + 1}`}
                    className="min-h-20 resize-y text-base leading-6"
                    maxLength={2000}
                    onChange={(event) =>
                      update(option.id, { label: event.target.value })
                    }
                    placeholder="Redacta una alternativa plausible y homogénea con las demás."
                    value={option.label}
                  />
                </label>
                <div className="assessment-choice-card__media">
                  {option.media ? (
                    <div>
                      <ImagePlus />
                      <p>
                        <strong>Figura fijada</strong>
                        <span>{option.media.alt_text}</span>
                      </p>
                      <Button
                        onClick={() =>
                          onChange(
                            options.map((item) => {
                              if (item.id !== option.id) return item;
                              const withoutMedia = { ...item };
                              delete withoutMedia.media;
                              return withoutMedia;
                            }),
                          )
                        }
                        size="sm"
                        type="button"
                        variant="ghost"
                      >
                        Quitar
                      </Button>
                    </div>
                  ) : null}
                </div>
                {option.media ? (
                  <label>
                    <span>Descripción extensa de la figura</span>
                    <Textarea
                      maxLength={5000}
                      onChange={(event) =>
                        update(option.id, {
                          media: {
                            ...option.media!,
                            long_description: event.target.value,
                          },
                        })
                      }
                      placeholder="Describe relaciones, tendencias o geometría que no caben en el texto alternativo."
                      value={option.media.long_description ?? ''}
                    />
                  </label>
                ) : null}
                <details className="assessment-choice-card__rationale">
                  <summary>Diagnóstico del distractor</summary>
                  <Textarea
                    maxLength={3000}
                    onChange={(event) =>
                      onRationaleChange(option.id, event.target.value)
                    }
                    placeholder={
                      correct
                        ? 'Explica por qué esta respuesta es válida y qué evidencia exige.'
                        : 'Describe el error conceptual o procedimiento que hace plausible este distractor.'
                    }
                    value={rationales[option.id] ?? ''}
                  />
                </details>
              </div>
            </li>
          );
        })}
      </ol>
      <Button
        className="assessment-choice-add"
        disabled={options.length >= 26}
        onClick={() =>
          onChange([
            ...options,
            { id: nextOptionId(options), label: '', mathLatex: '' },
          ])
        }
        type="button"
        variant="outline"
      >
        <Plus /> Añadir alternativa
      </Button>
    </div>
  );
}
