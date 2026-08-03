'use client';

import {
  ArrowRight,
  Binary,
  CheckCircle2,
  ImagePlus,
  Plus,
  Timer,
  Trash2,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { MathExpressionField } from '@/components/assessments/math-expression-field';
import {
  choiceMediaFromAssetNode,
  QuestionChoiceEditor,
  type ChoiceMediaDraft,
  type QuestionChoiceDraft,
} from '@/components/assessments/question-choice-editor';
import { QuestionContentEditor } from '@/components/assessments/question-content-editor';
import { AssetPickerDialog } from '@/components/assets/asset-picker-dialog';
import {
  QUESTION_TYPES,
  buildQuestionDefinition,
  questionSchema,
  type QuestionValues,
} from '@/components/assessments/authoring-forms';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import {
  createQuestion,
  updateQuestionRevision,
  useAssessmentMutation,
} from '@/lib/assessments/hooks';
import type { LMSUnitAcademicDocumentVersion2 } from '@/lib/content/generated/unit-document-v2';

type QuestionType = (typeof QUESTION_TYPES)[number][0];

const typePresentation: Record<
  QuestionType,
  { description: string; label: string }
> = {
  single_choice: {
    description: 'Una alternativa válida y distractores diagnosticables.',
    label: 'Selección única',
  },
  multiple_choice: {
    description: 'Varias afirmaciones u opciones correctas.',
    label: 'Selección múltiple',
  },
  true_false: {
    description: 'Juicio binario sobre una proposición precisa.',
    label: 'Verdadero / falso',
  },
  numeric: {
    description: 'Valor exacto o aproximado con unidad y tolerancia.',
    label: 'Respuesta numérica',
  },
  short_text: {
    description: 'Respuesta breve con normalización controlada.',
    label: 'Texto corto',
  },
  long_text: {
    description: 'Desarrollo, demostración o argumentación con rúbrica.',
    label: 'Desarrollo abierto',
  },
  ordering: {
    description: 'Secuencia lógica, algorítmica o procedimental.',
    label: 'Ordenamiento',
  },
  matching: {
    description: 'Correspondencia entre conceptos, objetos o representaciones.',
    label: 'Emparejamiento',
  },
  mathematical_expression: {
    description: 'Equivalencia matemática segura mediante MathJSON.',
    label: 'Respuesta matemática',
  },
};

const difficultyLabel: Record<string, string> = {
  advanced: 'Avanzada',
  expert: 'Experta',
  foundational: 'Fundamental',
  intermediate: 'Intermedia',
};

type MatchPair = {
  id: string;
  left: string;
  leftMathLatex: string;
  leftMedia?: ChoiceMediaDraft;
  right: string;
  rightMathLatex: string;
  rightMedia?: ChoiceMediaDraft;
};

export type QuestionStudioRevision = {
  code: string;
  definition: unknown;
  id: string;
  lockVersion: number;
  questionId: string;
  status: string;
  type: string;
};

type StudioSeed = {
  accepted: string[];
  allowedFunctions: string;
  allowedSymbols: string;
  answer: string;
  assumptions: string;
  caseSensitive: boolean;
  choices: QuestionChoiceDraft[];
  cognitiveProcess: string;
  code: string;
  difficulty: string;
  estimatedMinutes: number;
  feedbackCorrect: string;
  feedbackGeneral: string;
  feedbackIncorrect: string;
  framework: string;
  mathAnswer: { latex: string; mathjson: unknown };
  mathStrategy: 'structural' | 'symbolic_common_domain';
  pairs: MatchPair[];
  prompt: LMSUnitAcademicDocumentVersion2;
  rationales: Record<string, string>;
  solution: LMSUnitAcademicDocumentVersion2;
  sourceNote: string;
  tags: string;
  tolerance: string;
  type: QuestionType;
  unit: string;
};

function record(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function strings(value: unknown) {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === 'string')
    : [];
}

function questionType(value: unknown): QuestionType {
  return QUESTION_TYPES.some(([candidate]) => candidate === value)
    ? (value as QuestionType)
    : 'single_choice';
}

function optionDraft(value: unknown, index: number): QuestionChoiceDraft {
  const source = record(value);
  const media = record(source.media);
  const assetVersionId = String(media.asset_version_id ?? '');
  const altText = String(media.alt_text ?? '');
  return {
    id: String(source.id ?? `o${index + 1}`),
    label: String(source.label ?? ''),
    mathLatex: String(source.math_latex ?? ''),
    ...(assetVersionId && altText
      ? {
          media: {
            alt_text: altText,
            asset_version_id: assetVersionId,
            ...(typeof media.caption === 'string'
              ? { caption: media.caption }
              : {}),
            kind: 'image' as const,
            ...(typeof media.long_description === 'string'
              ? { long_description: media.long_description }
              : {}),
          },
        }
      : {}),
  };
}

function studioSeed(initial?: QuestionStudioRevision): StudioSeed {
  const definition = record(initial?.definition);
  const publicDefinition = record(definition.public);
  const grading = record(definition.grading);
  const feedback = record(definition.feedback);
  const authoring = record(definition.authoring);
  const type = questionType(initial?.type ?? definition.type);
  const publicOptions = Array.isArray(publicDefinition.options)
    ? publicDefinition.options
    : [];
  const choices = publicOptions.length
    ? publicOptions.map(optionDraft)
    : initialChoices();
  const left = Array.isArray(publicDefinition.left)
    ? publicDefinition.left
    : [];
  const right = Array.isArray(publicDefinition.right)
    ? publicDefinition.right
    : [];
  const pairs =
    left.length || right.length
      ? Array.from(
          { length: Math.max(left.length, right.length) },
          (_, index) => {
            const leftDraft = optionDraft(left[index], index);
            const rightDraft = optionDraft(right[index], left.length + index);
            return {
              id: `p${index + 1}`,
              left: leftDraft.label,
              leftMathLatex: leftDraft.mathLatex,
              ...(leftDraft.media ? { leftMedia: leftDraft.media } : {}),
              right: rightDraft.label,
              rightMathLatex: rightDraft.mathLatex,
              ...(rightDraft.media ? { rightMedia: rightDraft.media } : {}),
            };
          },
        )
      : [
          {
            id: 'p1',
            left: '',
            leftMathLatex: '',
            right: '',
            rightMathLatex: '',
          },
          {
            id: 'p2',
            left: '',
            leftMathLatex: '',
            right: '',
            rightMathLatex: '',
          },
        ];
  const correctOptionIds = strings(grading.correct_option_ids);
  const correctOrder = strings(grading.correct_order);
  const accepted =
    type === 'ordering'
      ? correctOrder
      : type === 'single_choice' || type === 'multiple_choice'
        ? correctOptionIds
        : ['o1'];
  const answer =
    type === 'true_false'
      ? String(Boolean(grading.correct_boolean))
      : type === 'numeric'
        ? String(grading.correct_value ?? '')
        : type === 'short_text'
          ? strings(grading.accepted_answers).join('\n')
          : type === 'long_text'
            ? String(grading.rubric ?? '')
            : '';
  const symbolAssumptions = record(grading.symbol_assumptions);
  const prompt = record(publicDefinition.prompt);
  const workedSolution = record(definition.worked_solution);
  return {
    accepted,
    allowedFunctions: strings(grading.allowed_functions).join(', '),
    allowedSymbols: strings(grading.allowed_symbols).join(', ') || 'x',
    answer,
    assumptions:
      Object.entries(symbolAssumptions)
        .map(([symbol, values]) => `${symbol}:${strings(values)[0] ?? 'real'}`)
        .join(', ') || 'x:real',
    caseSensitive: Boolean(grading.case_sensitive),
    choices,
    cognitiveProcess: String(authoring.cognitive_process ?? 'analyze'),
    code: initial?.code ?? '',
    difficulty: String(authoring.difficulty ?? 'advanced'),
    estimatedMinutes: Number(authoring.estimated_minutes ?? 5),
    feedbackCorrect: String(feedback.correct ?? ''),
    feedbackGeneral: String(feedback.general ?? ''),
    feedbackIncorrect: String(feedback.incorrect ?? ''),
    framework: String(authoring.framework ?? 'icfes'),
    mathAnswer: {
      latex: '',
      mathjson: grading.expected_mathjson ?? '',
    },
    mathStrategy:
      grading.equivalence_strategy === 'symbolic_common_domain'
        ? 'symbolic_common_domain'
        : 'structural',
    pairs,
    prompt:
      prompt.type === 'doc'
        ? (prompt as unknown as LMSUnitAcademicDocumentVersion2)
        : initialDocument('10000000-0000-4000-8000-000000000001'),
    rationales: Object.fromEntries(
      Object.entries(record(authoring.choice_rationales)).filter(
        (entry): entry is [string, string] => typeof entry[1] === 'string',
      ),
    ),
    solution:
      workedSolution.type === 'doc'
        ? (workedSolution as unknown as LMSUnitAcademicDocumentVersion2)
        : initialDocument('10000000-0000-4000-8000-000000000002'),
    sourceNote: String(authoring.source_note ?? ''),
    tags: strings(authoring.tags).join(', '),
    tolerance: String(grading.tolerance ?? '0'),
    type,
    unit: String(publicDefinition.unit ?? ''),
  };
}

function initialChoices(): QuestionChoiceDraft[] {
  return Array.from({ length: 4 }, (_, index) => ({
    id: `o${index + 1}`,
    label: '',
    mathLatex: '',
  }));
}

function initialDocument(nodeId: string): LMSUnitAcademicDocumentVersion2 {
  return {
    content: [{ attrs: { nodeId }, type: 'paragraph' }],
    type: 'doc',
  } as LMSUnitAcademicDocumentVersion2;
}

function documentText(document: LMSUnitAcademicDocumentVersion2) {
  const parts: string[] = [];
  const stack: unknown[] = [document];
  while (stack.length) {
    const current = stack.pop();
    if (!current || typeof current !== 'object' || Array.isArray(current))
      continue;
    const record = current as Record<string, unknown>;
    if (typeof record.text === 'string') parts.push(record.text);
    if (record.attrs && typeof record.attrs === 'object') {
      const attrs = record.attrs as Record<string, unknown>;
      if (typeof attrs.latex === 'string') parts.push(attrs.latex);
      if (typeof attrs.altText === 'string') parts.push(attrs.altText);
    }
    if (Array.isArray(record.content))
      stack.push(...record.content.toReversed());
  }
  return parts.join(' ').trim();
}

function tagsFrom(value: string) {
  return [
    ...new Set(
      value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    ),
  ];
}

function StudioField({
  children,
  hint,
  label,
}: Readonly<{
  children: React.ReactNode;
  hint?: string;
  label: string;
}>) {
  return (
    <label className="assessment-studio-field">
      <span>{label}</span>
      {children}
      {hint ? <small>{hint}</small> : null}
    </label>
  );
}

export function QuestionStudio({
  bankId,
  initialRevision,
  slug,
}: Readonly<{
  bankId: string;
  initialRevision?: QuestionStudioRevision;
  slug: string;
}>) {
  const router = useRouter();
  const seed = useMemo(() => studioSeed(initialRevision), [initialRevision]);
  const [type, setType] = useState<QuestionType>(seed.type);
  const [code, setCode] = useState(seed.code);
  const [prompt, setPrompt] = useState(seed.prompt);
  const [solution, setSolution] = useState(seed.solution);
  const [choices, setChoices] = useState<QuestionChoiceDraft[]>(seed.choices);
  const [accepted, setAccepted] = useState<string[]>(seed.accepted);
  const [rationales, setRationales] = useState<Record<string, string>>(
    seed.rationales,
  );
  const [pairs, setPairs] = useState<MatchPair[]>(seed.pairs);
  const [answer, setAnswer] = useState(seed.answer);
  const [tolerance, setTolerance] = useState(seed.tolerance);
  const [unit, setUnit] = useState(seed.unit);
  const [caseSensitive, setCaseSensitive] = useState(seed.caseSensitive);
  const [mathAnswer, setMathAnswer] = useState<{
    latex: string;
    mathjson: unknown;
  }>(seed.mathAnswer);
  const [allowedSymbols, setAllowedSymbols] = useState(seed.allowedSymbols);
  const [allowedFunctions, setAllowedFunctions] = useState(
    seed.allowedFunctions,
  );
  const [assumptions, setAssumptions] = useState(seed.assumptions);
  const [mathStrategy, setMathStrategy] = useState<
    'structural' | 'symbolic_common_domain'
  >(seed.mathStrategy);
  const [framework, setFramework] = useState(seed.framework);
  const [difficulty, setDifficulty] = useState(seed.difficulty);
  const [cognitiveProcess, setCognitiveProcess] = useState(
    seed.cognitiveProcess,
  );
  const [estimatedMinutes, setEstimatedMinutes] = useState(
    seed.estimatedMinutes,
  );
  const [tags, setTags] = useState(seed.tags);
  const [sourceNote, setSourceNote] = useState(seed.sourceNote);
  const [feedbackCorrect, setFeedbackCorrect] = useState(seed.feedbackCorrect);
  const [feedbackIncorrect, setFeedbackIncorrect] = useState(
    seed.feedbackIncorrect,
  );
  const [feedbackGeneral, setFeedbackGeneral] = useState(seed.feedbackGeneral);
  const [error, setError] = useState('');

  useEffect(() => {
    if (
      type !== 'mathematical_expression' ||
      mathAnswer.latex ||
      !mathAnswer.mathjson
    )
      return;
    let active = true;
    void import('@cortex-js/compute-engine').then(({ ComputeEngine }) => {
      if (!active) return;
      try {
        const engine = new ComputeEngine();
        const latex = engine.box(mathAnswer.mathjson as never).toLatex();
        setMathAnswer((current) => ({ ...current, latex }));
      } catch {
        // El autor puede reconstruir una respuesta heredada no representable.
      }
    });
    return () => {
      active = false;
    };
  }, [mathAnswer.latex, mathAnswer.mathjson, type]);

  const effectiveChoices = useMemo<QuestionChoiceDraft[]>(() => {
    if (type !== 'matching') return choices;
    return [
      ...pairs.map((pair, index) => ({
        id: `o${index + 1}`,
        label: pair.left,
        mathLatex: pair.leftMathLatex,
        ...(pair.leftMedia ? { media: pair.leftMedia } : {}),
      })),
      ...pairs.map((pair, index) => ({
        id: `o${pairs.length + index + 1}`,
        label: pair.right,
        mathLatex: pair.rightMathLatex,
        ...(pair.rightMedia ? { media: pair.rightMedia } : {}),
      })),
    ];
  }, [choices, pairs, type]);

  const answerKey = useMemo(() => {
    if (type === 'single_choice' || type === 'multiple_choice')
      return accepted.join(',');
    if (type === 'ordering')
      return choices.map((choice) => choice.id).join(',');
    if (type === 'matching')
      return pairs.map((_, index) => `l${index + 1}:r${index + 1}`).join(',');
    if (type === 'true_false') return answer || 'true';
    if (type === 'mathematical_expression')
      return mathAnswer.latex ? JSON.stringify(mathAnswer.mathjson) : '';
    return answer;
  }, [accepted, answer, choices, mathAnswer, pairs, type]);

  const visibleChoiceTypes = [
    'single_choice',
    'multiple_choice',
    'ordering',
  ].includes(type);
  const promptText = documentText(prompt);
  const solutionText = documentText(solution);
  const choiceReady =
    !visibleChoiceTypes ||
    (effectiveChoices.length >= 2 &&
      effectiveChoices.every((choice) => choice.label.trim()));
  const promptReady = promptText.length >= 20 && !promptText.includes('⟦');
  const solutionReady = solutionText.length > 0 && !solutionText.includes('⟦');

  const mutation = useAssessmentMutation(
    ({
      definition,
      questionCode,
    }: {
      definition: unknown;
      questionCode: string;
    }) =>
      initialRevision
        ? updateQuestionRevision(
            {
              bankId,
              questionId: initialRevision.questionId,
              revisionId: initialRevision.id,
              slug,
            },
            {
              definition,
              expected_version: initialRevision.lockVersion,
            },
          )
        : createQuestion(slug, bankId, {
            code: questionCode,
            definition,
            type,
          }),
  );

  function changeType(next: QuestionType) {
    setType(next);
    setError('');
    if (next === 'single_choice')
      setAccepted([accepted[0] ?? choices[0]?.id ?? 'o1']);
    if (next === 'multiple_choice' && !accepted.length)
      setAccepted([choices[0]?.id ?? 'o1']);
    if (next === 'true_false') setAnswer('true');
    if (next === 'numeric') setAnswer('0');
  }

  async function submit() {
    setError('');
    const values: QuestionValues = {
      accepted: answerKey,
      allowedFunctions,
      allowedSymbols,
      caseSensitive,
      code: code.trim(),
      feedbackCorrect,
      feedbackGeneral,
      feedbackIncorrect,
      mathAssumptions: assumptions,
      mathLatex: mathAnswer.latex,
      mathStrategy,
      options: effectiveChoices.map((choice) => choice.label).join('\n'),
      prompt: promptText,
      promptMath: '',
      responseGuidance: '',
      responsePlaceholder: '',
      tolerance,
      type,
      unit,
    };
    const parsed = questionSchema.safeParse(values);
    if (!parsed.success) {
      setError(
        parsed.error.issues[0]?.message ?? 'Revisa los campos del estudio.',
      );
      return;
    }
    if (!choiceReady) {
      setError('Completa todas las alternativas antes de crear la revisión.');
      return;
    }
    if (!promptReady) {
      setError(
        'Completa el enunciado y reemplaza todas las indicaciones ⟦entre corchetes⟧ de la plantilla.',
      );
      return;
    }
    try {
      const revision = await mutation.mutateAsync({
        definition: buildQuestionDefinition(parsed.data, {
          authoring: {
            choice_rationales: Object.fromEntries(
              Object.entries(rationales).filter(([, value]) => value.trim()),
            ),
            cognitive_process: cognitiveProcess,
            difficulty,
            estimated_minutes: estimatedMinutes,
            framework,
            ...(sourceNote.trim() ? { source_note: sourceNote.trim() } : {}),
            tags: tagsFrom(tags),
          },
          choices: effectiveChoices,
          promptDocument: prompt,
          ...(solutionReady ? { workedSolution: solution } : {}),
        }),
        questionCode: parsed.data.code,
      });
      if (initialRevision) {
        window.location.reload();
      } else {
        router.push(
          `/organizaciones/${slug}/evaluaciones/bancos/${bankId}/preguntas/${revision.question_id}/revisiones/${revision.id}`,
        );
        router.refresh();
      }
    } catch {
      // React Query conserva la causa y se presenta abajo.
    }
  }

  return (
    <div className="assessment-question-studio">
      <section className="assessment-question-studio__command">
        <div>
          <strong>
            {initialRevision ? 'Editar pregunta' : 'Nueva pregunta'}
          </strong>
          <small>{code.trim() || 'Sin código todavía'}</small>
        </div>
        <div>
          <Button onClick={() => router.back()} type="button" variant="ghost">
            Salir
          </Button>
          <Button
            disabled={mutation.isPending}
            onClick={() => void submit()}
            type="button"
          >
            {mutation.isPending
              ? initialRevision
                ? 'Guardando…'
                : 'Creando revisión…'
              : initialRevision
                ? 'Guardar cambios'
                : 'Crear revisión'}
          </Button>
        </div>
      </section>

      <div className="assessment-question-studio__layout">
        <main className="assessment-question-studio__main">
          <section
            className="assessment-studio-section"
            id="question-blueprint"
          >
            <header>
              <h2>Configuración</h2>
            </header>
            <div className="assessment-question-blueprint">
              <StudioField
                hint={typePresentation[type].description}
                label="Tipo de respuesta"
              >
                <select
                  className="academic-control"
                  disabled={Boolean(initialRevision)}
                  onChange={(event) =>
                    changeType(event.target.value as QuestionType)
                  }
                  value={type}
                >
                  {QUESTION_TYPES.map(([value]) => (
                    <option key={value} value={value}>
                      {typePresentation[value].label}
                    </option>
                  ))}
                </select>
              </StudioField>
              <StudioField
                label="Código estable"
                hint="Identifica el ítem a través de todas sus revisiones."
              >
                <Input
                  disabled={Boolean(initialRevision)}
                  maxLength={64}
                  onChange={(event) => setCode(event.target.value)}
                  placeholder="ICFES-RC-ALG-001"
                  value={code}
                />
              </StudioField>
              <StudioField label="Marco de uso">
                <select
                  className="academic-control"
                  onChange={(event) => setFramework(event.target.value)}
                  value={framework}
                >
                  <option value="icfes">ICFES / Saber</option>
                  <option value="higher_education">Educación superior</option>
                  <option value="research">Posgrado / investigación</option>
                  <option value="other">Otro marco</option>
                </select>
              </StudioField>
              <StudioField label="Complejidad">
                <select
                  className="academic-control"
                  onChange={(event) => setDifficulty(event.target.value)}
                  value={difficulty}
                >
                  <option value="foundational">Fundamental</option>
                  <option value="intermediate">Intermedia</option>
                  <option value="advanced">Avanzada</option>
                  <option value="expert">Experta / doctoral</option>
                </select>
              </StudioField>
              <StudioField label="Proceso cognitivo">
                <select
                  className="academic-control"
                  onChange={(event) => setCognitiveProcess(event.target.value)}
                  value={cognitiveProcess}
                >
                  <option value="understand">Comprender</option>
                  <option value="apply">Aplicar</option>
                  <option value="analyze">Analizar</option>
                  <option value="evaluate">Evaluar</option>
                  <option value="create">Crear / demostrar</option>
                </select>
              </StudioField>
              <StudioField label="Tiempo esperado">
                <div className="assessment-input-with-suffix">
                  <Input
                    max={240}
                    min={1}
                    onChange={(event) =>
                      setEstimatedMinutes(event.target.valueAsNumber)
                    }
                    type="number"
                    value={estimatedMinutes}
                  />
                  <span>min</span>
                </div>
              </StudioField>
              <StudioField
                label="Etiquetas"
                hint="Separadas por comas; no reemplazan objetivos curriculares."
              >
                <Input
                  onChange={(event) => setTags(event.target.value)}
                  placeholder="álgebra lineal, espacios vectoriales"
                  value={tags}
                />
              </StudioField>
            </div>
          </section>

          <section className="assessment-studio-section" id="question-prompt">
            <header>
              <h2>Contexto y enunciado</h2>
            </header>
            <QuestionContentEditor
              ariaLabel="Contexto y enunciado de la pregunta"
              onChange={setPrompt}
              slug={slug}
              value={prompt}
            />
          </section>

          <section className="assessment-studio-section" id="question-response">
            <header>
              <h2>Respuesta y clave</h2>
            </header>
            {visibleChoiceTypes ? (
              <QuestionChoiceEditor
                accepted={accepted}
                multiple={type === 'multiple_choice'}
                onAcceptedChange={setAccepted}
                onChange={setChoices}
                onRationaleChange={(id, value) =>
                  setRationales((current) => ({ ...current, [id]: value }))
                }
                options={choices}
                rationales={rationales}
                responseMode={type === 'ordering' ? 'sequence' : 'selection'}
                slug={slug}
              />
            ) : type === 'matching' ? (
              <MatchingStudio onChange={setPairs} pairs={pairs} slug={slug} />
            ) : type === 'true_false' ? (
              <div className="assessment-binary-key">
                <button
                  data-active={(answer || 'true') === 'true'}
                  onClick={() => setAnswer('true')}
                  type="button"
                >
                  <CheckCircle2 /> Verdadero
                </button>
                <button
                  data-active={answer === 'false'}
                  onClick={() => setAnswer('false')}
                  type="button"
                >
                  <Binary /> Falso
                </button>
              </div>
            ) : type === 'numeric' ? (
              <div className="assessment-exact-answer-grid">
                <StudioField label="Valor esperado">
                  <Input
                    inputMode="decimal"
                    onChange={(event) => setAnswer(event.target.value)}
                    value={answer}
                  />
                </StudioField>
                <StudioField
                  label="Tolerancia absoluta"
                  hint="Usa 0 cuando la respuesta deba ser exacta."
                >
                  <Input
                    inputMode="decimal"
                    onChange={(event) => setTolerance(event.target.value)}
                    value={tolerance}
                  />
                </StudioField>
                <StudioField
                  label="Unidad"
                  hint="Opcional; se muestra junto al campo."
                >
                  <Input
                    onChange={(event) => setUnit(event.target.value)}
                    placeholder="m/s²"
                    value={unit}
                  />
                </StudioField>
              </div>
            ) : type === 'short_text' ? (
              <div className="assessment-open-answer">
                <StudioField
                  label="Respuestas aceptadas"
                  hint="Una variante por línea; el servidor normaliza espacios y Unicode."
                >
                  <Textarea
                    className="min-h-32"
                    onChange={(event) => setAnswer(event.target.value)}
                    value={answer}
                  />
                </StudioField>
                <label className="assessment-check-row">
                  <input
                    checked={caseSensitive}
                    onChange={(event) => setCaseSensitive(event.target.checked)}
                    type="checkbox"
                  />{' '}
                  Distinguir mayúsculas y minúsculas
                </label>
              </div>
            ) : type === 'long_text' ? (
              <StudioField
                label="Rúbrica para calificación humana"
                hint="Define evidencias observables, errores críticos y condiciones de crédito parcial."
              >
                <Textarea
                  className="min-h-56 text-base leading-7"
                  onChange={(event) => setAnswer(event.target.value)}
                  placeholder="Criterio 1…\nCriterio 2…"
                  value={answer}
                />
              </StudioField>
            ) : (
              <div className="assessment-math-key-studio">
                <div>
                  <StudioField label="Símbolos permitidos">
                    <Input
                      onChange={(event) =>
                        setAllowedSymbols(event.target.value)
                      }
                      value={allowedSymbols}
                    />
                  </StudioField>
                  <StudioField label="Funciones permitidas">
                    <Input
                      onChange={(event) =>
                        setAllowedFunctions(event.target.value)
                      }
                      placeholder="Sin, Cos, Exp"
                      value={allowedFunctions}
                    />
                  </StudioField>
                  <StudioField label="Hipótesis sobre símbolos">
                    <Input
                      onChange={(event) => setAssumptions(event.target.value)}
                      placeholder="x:real, n:integer"
                      value={assumptions}
                    />
                  </StudioField>
                  <StudioField label="Criterio de equivalencia">
                    <select
                      className="academic-control"
                      onChange={(event) =>
                        setMathStrategy(
                          event.target.value as typeof mathStrategy,
                        )
                      }
                      value={mathStrategy}
                    >
                      <option value="structural">Estructural canónica</option>
                      <option value="symbolic_common_domain">
                        Simbólica en dominio común
                      </option>
                    </select>
                  </StudioField>
                </div>
                <MathExpressionField
                  allowedFunctions={allowedFunctions
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean)}
                  allowedSymbols={allowedSymbols
                    .split(',')
                    .map((item) => item.trim())
                    .filter(Boolean)}
                  label="Expresión matemática esperada"
                  onChange={(value) =>
                    setMathAnswer(
                      value
                        ? { latex: value.latex, mathjson: value.mathjson }
                        : { latex: '', mathjson: '' },
                    )
                  }
                  value={mathAnswer}
                />
              </div>
            )}
          </section>

          <section className="assessment-studio-section" id="question-solution">
            <header>
              <h2>Solución y retroalimentación</h2>
            </header>
            <QuestionContentEditor
              ariaLabel="Solución razonada privada"
              compact
              onChange={setSolution}
              slug={slug}
              value={solution}
            />
            <div className="assessment-feedback-grid">
              <StudioField label="Cuando acierta">
                <Textarea
                  onChange={(event) => setFeedbackCorrect(event.target.value)}
                  placeholder="Confirma el razonamiento, no sólo el resultado."
                  value={feedbackCorrect}
                />
              </StudioField>
              <StudioField label="Cuando falla">
                <Textarea
                  onChange={(event) => setFeedbackIncorrect(event.target.value)}
                  placeholder="Orienta sin revelar automáticamente toda la solución."
                  value={feedbackIncorrect}
                />
              </StudioField>
              <StudioField label="Orientación general">
                <Textarea
                  onChange={(event) => setFeedbackGeneral(event.target.value)}
                  placeholder="Referencia el concepto o estrategia que conviene revisar."
                  value={feedbackGeneral}
                />
              </StudioField>
            </div>
            <StudioField
              label="Fuente, adaptación o nota editorial"
              hint="Campo privado para trazabilidad; no se muestra al estudiante."
            >
              <Textarea
                onChange={(event) => setSourceNote(event.target.value)}
                value={sourceNote}
              />
            </StudioField>
          </section>
        </main>
      </div>
      {error ? (
        <p className="assessment-studio-submit-error" role="alert">
          {error}
        </p>
      ) : null}
      {mutation.error ? (
        <p className="assessment-studio-submit-error" role="alert">
          {mutation.error instanceof Error
            ? mutation.error.message
            : 'No fue posible crear la revisión.'}
        </p>
      ) : null}
      <div className="assessment-question-studio__mobile-save">
        <div>
          <Timer />
          <span>
            {estimatedMinutes} min · {difficultyLabel[difficulty] ?? difficulty}
          </span>
        </div>
        <Button
          disabled={mutation.isPending}
          onClick={() => void submit()}
          type="button"
        >
          {initialRevision ? 'Guardar cambios' : 'Crear revisión'}
        </Button>
      </div>
    </div>
  );
}

function MatchingStudio({
  onChange,
  pairs,
  slug,
}: Readonly<{
  onChange: (pairs: MatchPair[]) => void;
  pairs: readonly MatchPair[];
  slug: string;
}>) {
  function update(id: string, patch: Partial<MatchPair>) {
    onChange(
      pairs.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  }

  return (
    <div className="assessment-matching-studio">
      <header>
        <h3>Pares de correspondencia</h3>
        <span>{pairs.length} pares</span>
      </header>
      {pairs.map((pair, index) => (
        <div key={pair.id}>
          <span>{index + 1}</span>
          <div className="assessment-matching-studio__side">
            <Textarea
              aria-label={`Elemento izquierdo ${index + 1}`}
              onChange={(event) =>
                update(pair.id, { left: event.target.value })
              }
              placeholder="Concepto, expresión o afirmación"
              value={pair.left}
            />
            <div className="assessment-matching-studio__side-actions">
              {pair.leftMedia ? (
                <span>
                  <ImagePlus />
                  {pair.leftMedia.alt_text}
                </span>
              ) : null}
              {pair.leftMedia ? (
                <Button
                  aria-label={`Quitar imagen del elemento izquierdo ${index + 1}`}
                  onClick={() => {
                    const next = { ...pair };
                    delete next.leftMedia;
                    onChange(
                      pairs.map((item) => (item.id === pair.id ? next : item)),
                    );
                  }}
                  size="sm"
                  type="button"
                  variant="ghost"
                >
                  Quitar
                </Button>
              ) : null}
              <AssetPickerDialog
                allowDecorative={false}
                allowedKinds={['image']}
                iconOnly
                onInsert={(node) => {
                  const media = choiceMediaFromAssetNode(node);
                  if (media) update(pair.id, { leftMedia: media });
                }}
                slug={slug}
                triggerLabel={`Añadir imagen al elemento izquierdo ${index + 1}`}
              />
            </div>
          </div>
          <ArrowRight />
          <div className="assessment-matching-studio__side">
            <Textarea
              aria-label={`Correspondencia ${index + 1}`}
              onChange={(event) =>
                update(pair.id, { right: event.target.value })
              }
              placeholder="Definición, resultado o representación"
              value={pair.right}
            />
            <div className="assessment-matching-studio__side-actions">
              {pair.rightMedia ? (
                <span>
                  <ImagePlus />
                  {pair.rightMedia.alt_text}
                </span>
              ) : null}
              {pair.rightMedia ? (
                <Button
                  aria-label={`Quitar imagen de la correspondencia ${index + 1}`}
                  onClick={() => {
                    const next = { ...pair };
                    delete next.rightMedia;
                    onChange(
                      pairs.map((item) => (item.id === pair.id ? next : item)),
                    );
                  }}
                  size="sm"
                  type="button"
                  variant="ghost"
                >
                  Quitar
                </Button>
              ) : null}
              <AssetPickerDialog
                allowDecorative={false}
                allowedKinds={['image']}
                iconOnly
                onInsert={(node) => {
                  const media = choiceMediaFromAssetNode(node);
                  if (media) update(pair.id, { rightMedia: media });
                }}
                slug={slug}
                triggerLabel={`Añadir imagen a la correspondencia ${index + 1}`}
              />
            </div>
          </div>
          <Button
            aria-label={`Eliminar par ${index + 1}`}
            disabled={pairs.length <= 1}
            onClick={() =>
              onChange(pairs.filter((item) => item.id !== pair.id))
            }
            size="icon-sm"
            type="button"
            variant="ghost"
          >
            <Trash2 />
          </Button>
        </div>
      ))}
      <Button
        onClick={() =>
          onChange([
            ...pairs,
            {
              id: `p${Date.now()}`,
              left: '',
              leftMathLatex: '',
              right: '',
              rightMathLatex: '',
            },
          ])
        }
        type="button"
        variant="outline"
      >
        <Plus /> Añadir par
      </Button>
    </div>
  );
}
