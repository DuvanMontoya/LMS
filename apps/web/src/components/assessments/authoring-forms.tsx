'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import {
  ArrowRight,
  BookOpenCheck,
  Database,
  GitPullRequest,
  Search,
  SlidersHorizontal,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { QuestionPreviewDialog } from '@/components/assessments/question-preview-dialog';
import type { QuestionChoiceDraft } from '@/components/assessments/question-choice-editor';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  createAssessment,
  createQuestionBank,
  createQuestionRevisionFromVersion,
  transitionQuestionRevision,
  updateQuestionBank,
  useAssessmentMutation,
} from '@/lib/assessments/hooks';
import type { QuestionBankPage, QuestionPage } from '@/lib/assessments/server';
import type { LMSUnitAcademicDocumentVersion2 } from '@/lib/content/generated/unit-document-v2';

const assessmentSchema = z.object({
  attempt_limit: z.number().int().positive().max(20),
  description: z.string().trim().max(5000),
  feedback_mode: z.enum(['none', 'score_only', 'full_after_grading']),
  instructions: z.string().trim().max(5000),
  pass_percent: z.number().min(0).max(100),
  shuffle_items: z.boolean(),
  shuffle_sections: z.boolean(),
  slug: z
    .string()
    .trim()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Usa minúsculas y guiones.'),
  time_limit_minutes: z.number().int().positive().max(10080),
  title: z.string().trim().min(1, 'Escribe el título.').max(200),
});
type AssessmentValues = z.infer<typeof assessmentSchema>;

function stableSlug(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

export function AssessmentCreateForm({ slug }: Readonly<{ slug: string }>) {
  const router = useRouter();
  const mutation = useAssessmentMutation((values: AssessmentValues) =>
    createAssessment(slug, {
      attempt_limit: values.attempt_limit,
      description: values.description,
      feedback_mode: values.feedback_mode,
      instructions: values.instructions,
      pass_basis_points: Math.round(values.pass_percent * 100),
      shuffle_items: values.shuffle_items,
      shuffle_sections: values.shuffle_sections,
      slug: values.slug,
      time_limit_minutes: values.time_limit_minutes,
      title: values.title,
    }),
  );
  const form = useForm<AssessmentValues>({
    defaultValues: {
      attempt_limit: 2,
      description: '',
      feedback_mode: 'full_after_grading',
      instructions: '',
      pass_percent: 60,
      shuffle_items: false,
      shuffle_sections: false,
      slug: '',
      time_limit_minutes: 45,
      title: '',
    },
    resolver: zodResolver(assessmentSchema),
  });
  const [slugEdited, setSlugEdited] = useState(false);
  const watchedTitle = useWatch({ control: form.control, name: 'title' });
  useEffect(() => {
    if (!slugEdited) {
      form.setValue('slug', stableSlug(watchedTitle), {
        shouldValidate: form.formState.isSubmitted,
      });
    }
  }, [form, slugEdited, watchedTitle]);
  async function submit(values: AssessmentValues) {
    try {
      const parsed = assessmentSchema.parse(values);
      await mutation.mutateAsync(parsed);
      router.push(`/organizaciones/${slug}/evaluaciones/${parsed.slug}`);
      router.refresh();
    } catch {
      // React Query conserva y presenta el error en el formulario.
    }
  }
  return (
    <form
      className="assessment-create-form"
      noValidate
      onSubmit={form.handleSubmit(submit)}
    >
      <div className="assessment-create-form__identity">
        <Field
          error={form.formState.errors.title?.message}
          label="Título"
          name="assessment-title"
        >
          <Input
            autoFocus
            id="assessment-title"
            placeholder="Ej. Parcial de análisis funcional"
            {...form.register('title')}
          />
        </Field>
        <Field label="Propósito" name="assessment-description">
          <Textarea
            className="min-h-24"
            id="assessment-description"
            placeholder="Qué evidencia recoge, para quién y en qué momento del curso."
            {...form.register('description')}
          />
        </Field>
        <Field
          label="Instrucciones para el estudiante"
          name="assessment-instructions"
        >
          <Textarea
            className="min-h-20"
            id="assessment-instructions"
            placeholder="Condiciones de presentación, materiales permitidos y criterios generales."
            {...form.register('instructions')}
          />
        </Field>
      </div>
      <fieldset className="assessment-create-form__policy">
        <legend>Aplicación y retroalimentación</legend>
        <div className="assessment-create-form__numbers">
          <Field label="Duración" name="assessment-time">
            <Input
              id="assessment-time"
              min={1}
              type="number"
              {...form.register('time_limit_minutes', { valueAsNumber: true })}
            />
            <p className="assessment-control-suffix">min</p>
          </Field>
          <Field label="Intentos" name="assessment-attempts">
            <Input
              id="assessment-attempts"
              min={1}
              type="number"
              {...form.register('attempt_limit', { valueAsNumber: true })}
            />
          </Field>
          <Field label="Aprobación" name="assessment-pass">
            <Input
              id="assessment-pass"
              max={100}
              min={0}
              step="0.01"
              type="number"
              {...form.register('pass_percent', { valueAsNumber: true })}
            />
            <p className="assessment-control-suffix">%</p>
          </Field>
        </div>
        <Field label="Resultados visibles" name="assessment-feedback">
          <select
            className="academic-control"
            id="assessment-feedback"
            {...form.register('feedback_mode')}
          >
            <option value="full_after_grading">
              Puntaje y retroalimentación al calificar
            </option>
            <option value="score_only">Solo puntaje</option>
            <option value="none">Sin resultados visibles</option>
          </select>
        </Field>
        <div className="assessment-create-form__checks">
          <label>
            <input type="checkbox" {...form.register('shuffle_sections')} />
            Mezclar secciones en cada intento
          </label>
          <label>
            <input type="checkbox" {...form.register('shuffle_items')} />
            Mezclar preguntas dentro de cada sección
          </label>
        </div>
        <details className="assessment-create-form__advanced">
          <summary>Identificador avanzado</summary>
          <Field
            error={form.formState.errors.slug?.message}
            hint="Se genera automáticamente; edítalo solo si necesitas una referencia específica."
            label="Identificador estable"
            name="assessment-slug"
          >
            <Input
              id="assessment-slug"
              placeholder="parcial-analisis-funcional"
              {...form.register('slug', {
                onChange: () => setSlugEdited(true),
              })}
            />
          </Field>
        </details>
      </fieldset>
      <div className="assessment-workbench-footer">
        <div>
          <p className="font-medium">Borrador listo para componer</p>
          <p className="text-xs text-muted-foreground">
            Al crearla entrarás directamente a objetivos, secciones y preguntas.
          </p>
        </div>
        <SubmitState
          error={mutation.error}
          label="Crear evaluación"
          pending={mutation.isPending}
        />
      </div>
    </form>
  );
}

const bankSchema = z.object({
  description: z.string().trim().max(5000),
  name: z.string().trim().min(1, 'Escribe el nombre.').max(200),
  slug: z
    .string()
    .trim()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Usa minúsculas y guiones.'),
});
type BankValues = z.infer<typeof bankSchema>;

export function QuestionBankCreateForm({
  onCreated,
  slug,
}: Readonly<{ onCreated?: (bankId: string) => void; slug: string }>) {
  const router = useRouter();
  const mutation = useAssessmentMutation((values: BankValues) =>
    createQuestionBank(slug, values),
  );
  const form = useForm<BankValues>({
    defaultValues: { description: '', name: '', slug: '' },
    resolver: zodResolver(bankSchema),
  });
  const [slugEdited, setSlugEdited] = useState(false);
  const watchedName = useWatch({ control: form.control, name: 'name' });
  useEffect(() => {
    if (!slugEdited) {
      form.setValue('slug', stableSlug(watchedName), {
        shouldValidate: form.formState.isSubmitted,
      });
    }
  }, [form, slugEdited, watchedName]);
  async function submit(values: BankValues) {
    try {
      const bank = await mutation.mutateAsync(bankSchema.parse(values));
      if (onCreated) {
        form.reset();
        onCreated(bank.id);
      } else {
        router.push(`/organizaciones/${slug}/evaluaciones/bancos/${bank.id}`);
        router.refresh();
      }
    } catch {
      // React Query conserva y presenta el error en el formulario.
    }
  }
  return (
    <form
      className="assessment-bank-create-form"
      noValidate
      onSubmit={form.handleSubmit(submit)}
    >
      <Field
        error={form.formState.errors.name?.message}
        label="Nombre del banco"
        name="bank-name"
      >
        <Input
          autoFocus
          id="bank-name"
          placeholder="Ej. Problemas de análisis real"
          {...form.register('name')}
        />
      </Field>
      <Field
        hint="Indica disciplina, nivel, audiencia y criterio de reutilización."
        label="Propósito y alcance"
        name="bank-description"
      >
        <Textarea
          className="min-h-32 text-base leading-7"
          id="bank-description"
          placeholder="Ej. Preguntas de análisis real para cursos de maestría y doctorado, revisadas por el equipo de matemáticas puras."
          {...form.register('description')}
        />
      </Field>
      <details className="assessment-create-form__advanced">
        <summary>Identificador avanzado</summary>
        <Field
          error={form.formState.errors.slug?.message}
          hint="Se genera automáticamente y permanece estable."
          label="Identificador"
          name="bank-slug"
        >
          <Input
            className="font-mono"
            id="bank-slug"
            placeholder="problemas-analisis-real"
            {...form.register('slug', { onChange: () => setSlugEdited(true) })}
          />
        </Field>
      </details>
      <div className="assessment-workbench-footer">
        <div>
          <p className="font-medium">Colección privada y reutilizable</p>
          <p className="text-xs text-muted-foreground">
            Al crearla entrarás a su inventario; ninguna pregunta se publica
            automáticamente.
          </p>
        </div>
        <SubmitState
          error={mutation.error}
          label="Crear banco"
          pending={mutation.isPending}
        />
      </div>
    </form>
  );
}

export function QuestionBankSettingsForm({
  bank,
  slug,
}: Readonly<{
  bank: QuestionBankPage['results'][number];
  slug: string;
}>) {
  const router = useRouter();
  const [name, setName] = useState(bank.name);
  const [description, setDescription] = useState(bank.description);
  const mutation = useAssessmentMutation(() =>
    updateQuestionBank(slug, bank.id, {
      description,
      expected_version: bank.lock_version,
      name,
    }),
  );
  return (
    <details className="assessment-bank-settings">
      <summary>Información y gobierno del banco</summary>
      <div className="assessment-bank-settings__body">
        <div>
          <Field label="Nombre institucional" name="bank-settings-name">
            <Input
              id="bank-settings-name"
              onChange={(event) => setName(event.target.value)}
              value={name}
            />
          </Field>
          <Field label="Descripción editorial" name="bank-settings-description">
            <Textarea
              id="bank-settings-description"
              onChange={(event) => setDescription(event.target.value)}
              value={description}
            />
          </Field>
        </div>
        <aside>
          <p className="assessment-rail-kicker">Identidad inmutable</p>
          <code>/{bank.slug}</code>
          <dl>
            <div>
              <dt>Estado</dt>
              <dd>{bank.status === 'active' ? 'Activo' : 'Archivado'}</dd>
            </div>
            <div>
              <dt>Control de concurrencia</dt>
              <dd>v{bank.lock_version}</dd>
            </div>
          </dl>
          <Button
            disabled={!name.trim() || mutation.isPending}
            onClick={async () => {
              try {
                await mutation.mutateAsync(undefined);
                router.refresh();
              } catch {
                // React Query presenta el error en este panel.
              }
            }}
            type="button"
          >
            Guardar información
          </Button>
          <MutationError error={mutation.error} />
        </aside>
      </div>
    </details>
  );
}

export const QUESTION_TYPES = [
  ['single_choice', 'Selección única'],
  ['multiple_choice', 'Selección múltiple'],
  ['true_false', 'Verdadero o falso'],
  ['numeric', 'Numérica'],
  ['short_text', 'Texto corto'],
  ['long_text', 'Texto largo'],
  ['ordering', 'Ordenamiento'],
  ['matching', 'Emparejamiento'],
  ['mathematical_expression', 'Expresión matemática'],
] as const;
export const questionSchema = z
  .object({
    accepted: z.string(),
    code: z
      .string()
      .trim()
      .min(1, 'Asigna un código estable.')
      .max(64)
      .regex(/^[A-Za-z0-9_-]+$/, 'Usa letras, números, guion o guion bajo.'),
    feedbackCorrect: z.string().trim().max(5000),
    feedbackGeneral: z.string().trim().max(5000),
    feedbackIncorrect: z.string().trim().max(5000),
    allowedFunctions: z.string(),
    allowedSymbols: z.string(),
    mathAssumptions: z.string(),
    mathLatex: z.string().max(4096),
    promptMath: z.string().max(12000),
    mathStrategy: z.enum(['structural', 'symbolic_common_domain']),
    options: z.string(),
    prompt: z.string().trim().min(1, 'Escribe el enunciado.').max(5000),
    responseGuidance: z.string().max(1000).optional(),
    responsePlaceholder: z.string().max(240).optional(),
    caseSensitive: z.boolean().optional(),
    tolerance: z.string(),
    unit: z.string().max(80).optional(),
    type: z.enum([
      'single_choice',
      'multiple_choice',
      'true_false',
      'numeric',
      'short_text',
      'long_text',
      'ordering',
      'matching',
      'mathematical_expression',
    ]),
  })
  .superRefine((values, context) => {
    const optionIds = lines(values.options).map((_, index) => `o${index + 1}`);
    const keys = values.accepted
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    if (
      ['single_choice', 'multiple_choice', 'ordering', 'matching'].includes(
        values.type,
      ) &&
      optionIds.length < 2
    ) {
      context.addIssue({
        code: 'custom',
        message: 'Agrega al menos dos opciones.',
        path: ['options'],
      });
    }
    if (
      values.type === 'single_choice' &&
      (keys.length !== 1 || !optionIds.includes(keys[0]!))
    ) {
      context.addIssue({
        code: 'custom',
        message: 'Selecciona exactamente una opción existente.',
        path: ['accepted'],
      });
    }
    if (
      values.type === 'multiple_choice' &&
      (!keys.length || keys.some((key) => !optionIds.includes(key)))
    ) {
      context.addIssue({
        code: 'custom',
        message: 'Todas las claves deben corresponder a opciones existentes.',
        path: ['accepted'],
      });
    }
    if (
      values.type === 'ordering' &&
      (keys.length !== optionIds.length ||
        new Set(keys).size !== optionIds.length ||
        keys.some((key) => !optionIds.includes(key)))
    ) {
      context.addIssue({
        code: 'custom',
        message:
          'Incluye cada opción exactamente una vez en el orden correcto.',
        path: ['accepted'],
      });
    }
    if (
      values.type === 'numeric' &&
      !/^-?(0|[1-9][0-9]{0,99})(\.[0-9]{1,20})?$/.test(values.accepted.trim())
    ) {
      context.addIssue({
        code: 'custom',
        message: 'Escribe un decimal válido, sin exponente.',
        path: ['accepted'],
      });
    }
    if (
      values.type === 'numeric' &&
      !/^(0|[1-9][0-9]{0,99})(\.[0-9]{1,20})?$/.test(
        values.tolerance.trim() || '0',
      )
    ) {
      context.addIssue({
        code: 'custom',
        message: 'La tolerancia debe ser un decimal no negativo.',
        path: ['tolerance'],
      });
    }
    if (values.type === 'short_text' && lines(values.accepted).length === 0) {
      context.addIssue({
        code: 'custom',
        message: 'Agrega al menos una respuesta aceptada.',
        path: ['accepted'],
      });
    }
    if (values.type === 'true_false' && !['true', 'false'].includes(keys[0]!)) {
      context.addIssue({
        code: 'custom',
        message: 'Selecciona verdadero o falso.',
        path: ['accepted'],
      });
    }
    if (values.type === 'matching') {
      const optionCount = optionIds.length;
      const midpoint = Math.max(1, Math.floor(optionCount / 2));
      const expectedLeft = Array.from(
        { length: midpoint },
        (_, index) => `l${index + 1}`,
      );
      const expectedRight = Array.from(
        { length: midpoint },
        (_, index) => `r${index + 1}`,
      );
      const pairs = keys.map((pair) => pair.split(':'));
      if (
        optionCount % 2 !== 0 ||
        pairs.length !== expectedLeft.length ||
        pairs.some(
          ([left, right]) =>
            !expectedLeft.includes(left ?? '') ||
            !expectedRight.includes(right ?? ''),
        )
      ) {
        context.addIssue({
          code: 'custom',
          message:
            'Usa un número par de opciones y cubre cada elemento izquierdo, por ejemplo l1:r1,l2:r2.',
          path: ['accepted'],
        });
      }
    }
    if (values.type === 'mathematical_expression') {
      const symbols = commaValues(values.allowedSymbols);
      const functions = commaValues(values.allowedFunctions);
      const allowedFunctionNames = new Set([
        'Sin',
        'Cos',
        'Tan',
        'Exp',
        'Ln',
        'Log',
        'Abs',
      ]);
      if (
        symbols.length === 0 ||
        symbols.length > 10 ||
        new Set(symbols).size !== symbols.length ||
        symbols.some((symbol) => !/^[A-Za-z][A-Za-z0-9_]{0,63}$/.test(symbol))
      ) {
        context.addIssue({
          code: 'custom',
          message:
            'Define entre 1 y 10 símbolos únicos, separados por comas, con nombres seguros.',
          path: ['allowedSymbols'],
        });
      }
      if (
        functions.length > 7 ||
        new Set(functions).size !== functions.length ||
        functions.some((name) => !allowedFunctionNames.has(name))
      ) {
        context.addIssue({
          code: 'custom',
          message:
            'Usa sólo funciones permitidas y sin repetir: Sin, Cos, Tan, Exp, Ln, Log o Abs.',
          path: ['allowedFunctions'],
        });
      }
      try {
        JSON.parse(values.accepted);
      } catch {
        context.addIssue({
          code: 'custom',
          message: 'Construye una expresión matemática válida.',
          path: ['accepted'],
        });
      }
      if (!values.mathLatex.trim()) {
        context.addIssue({
          code: 'custom',
          message: 'Escribe la expresión esperada.',
          path: ['mathLatex'],
        });
      }
      const assumptions = commaValues(values.mathAssumptions);
      if (
        assumptions.some((entry) => {
          const [symbol, assumption, extra] = entry
            .split(':')
            .map((item) => item.trim());
          return (
            Boolean(extra) ||
            !symbol ||
            !symbols.includes(symbol) ||
            !assumption ||
            !['real', 'positive', 'nonnegative', 'integer'].includes(assumption)
          );
        })
      ) {
        context.addIssue({
          code: 'custom',
          message:
            'Usa símbolo:supuesto con símbolos permitidos y supuestos real, positive, nonnegative o integer.',
          path: ['mathAssumptions'],
        });
      }
    }
  });
export type QuestionValues = z.infer<typeof questionSchema>;

type ChoiceMedia = {
  alt_text: string;
  asset_version_id: string;
  caption?: string;
  kind: 'image';
  long_description?: string;
};

type QuestionMediaSelection = {
  authoring?: {
    choice_rationales?: Readonly<Record<string, string>>;
    cognitive_process: string;
    difficulty: string;
    estimated_minutes: number;
    framework: string;
    source_note?: string;
    tags?: readonly string[];
  };
  choices?: readonly QuestionChoiceDraft[];
  optionMath?: Readonly<Record<string, string>>;
  optionMedia?: Readonly<Record<string, ChoiceMedia>>;
  promptDocument?: LMSUnitAcademicDocumentVersion2;
  promptNodes?: readonly Record<string, unknown>[];
  workedSolution?: LMSUnitAcademicDocumentVersion2;
};

function promptDocument(
  text: string,
  nodes: readonly Record<string, unknown>[] = [],
  mathLatex = '',
) {
  return {
    content: [
      {
        attrs: { nodeId: crypto.randomUUID() },
        content: [{ text, type: 'text' }],
        type: 'paragraph',
      },
      ...(mathLatex.trim()
        ? [
            {
              attrs: { nodeId: crypto.randomUUID(), latex: mathLatex.trim() },
              type: 'displayMath',
            },
          ]
        : []),
      ...nodes,
    ],
    type: 'doc',
  };
}

function lines(value: string) {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function commaValues(value: string) {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

export function buildQuestionDefinition(
  values: QuestionValues,
  media: QuestionMediaSelection = {},
) {
  const type = values.type;
  const publicPayload: Record<string, unknown> = {
    prompt:
      media.promptDocument ??
      promptDocument(values.prompt, media.promptNodes, values.promptMath),
    schema_version: 1,
    type,
  };
  let grading: Record<string, unknown>;
  const optionLabels = lines(values.options);
  const sourceOptions =
    media.choices ??
    optionLabels.map((label, index) => ({
      id: `o${index + 1}`,
      label,
      mathLatex: media.optionMath?.[`o${index + 1}`] ?? '',
      media: media.optionMedia?.[`o${index + 1}`],
    }));
  const options = sourceOptions.map((source, index) => {
    const id = source.id || `o${index + 1}`;
    const optionMedia = source.media;
    const optionMath = source.mathLatex.trim();
    return {
      id,
      label: source.label.trim(),
      ...(optionMath ? { math_latex: optionMath } : {}),
      ...(optionMedia ? { media: optionMedia } : {}),
    };
  });
  if (['single_choice', 'multiple_choice', 'ordering'].includes(type)) {
    publicPayload.options = options;
  }
  if (type === 'single_choice') {
    grading = { correct_option_ids: [values.accepted.trim()] };
  } else if (type === 'multiple_choice') {
    grading = {
      correct_option_ids: values.accepted
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    };
  } else if (type === 'true_false') {
    publicPayload.true_label = 'Verdadero';
    publicPayload.false_label = 'Falso';
    grading = { correct_boolean: values.accepted.trim() === 'true' };
  } else if (type === 'numeric') {
    if (values.unit?.trim()) publicPayload.unit = values.unit.trim();
    if (values.responsePlaceholder?.trim())
      publicPayload.response_placeholder = values.responsePlaceholder.trim();
    grading = {
      correct_value: values.accepted.trim(),
      tolerance: values.tolerance.trim() || '0',
    };
  } else if (type === 'short_text') {
    if (values.responsePlaceholder?.trim())
      publicPayload.response_placeholder = values.responsePlaceholder.trim();
    grading = {
      accepted_answers: lines(values.accepted),
      case_sensitive: values.caseSensitive ?? false,
    };
  } else if (type === 'long_text') {
    if (values.responsePlaceholder?.trim())
      publicPayload.response_placeholder = values.responsePlaceholder.trim();
    grading = {
      manual_required: true,
      rubric: values.accepted.trim(),
    };
  } else if (type === 'ordering') {
    grading = {
      correct_order: values.accepted
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    };
  } else if (type === 'matching') {
    const midpoint = Math.max(1, Math.floor(options.length / 2));
    publicPayload.left = options
      .slice(0, midpoint)
      .map((item, index) => ({ ...item, id: `l${index + 1}` }));
    publicPayload.right = options
      .slice(midpoint)
      .map((item, index) => ({ ...item, id: `r${index + 1}` }));
    grading = {
      correct_pairs: Object.fromEntries(
        values.accepted
          .split(',')
          .map((pair) => pair.trim().split(':'))
          .filter(
            (pair): pair is [string, string] =>
              pair.length === 2 && Boolean(pair[0]) && Boolean(pair[1]),
          ),
      ),
    };
  } else {
    const allowedSymbols = commaValues(values.allowedSymbols);
    const allowedFunctions = commaValues(values.allowedFunctions);
    const symbolAssumptions = Object.fromEntries(
      commaValues(values.mathAssumptions)
        .flatMap((entry) => {
          const parts = entry.split(':').map((item) => item.trim());
          return parts.length === 2 && parts[0] && parts[1]
            ? ([[parts[0], parts[1]]] as const)
            : [];
        })
        .filter(
          ([symbol, assumption]) =>
            allowedSymbols.includes(symbol) &&
            ['real', 'positive', 'nonnegative', 'integer'].includes(assumption),
        )
        .map(([symbol, assumption]) => [symbol, [assumption]]),
    );
    publicPayload.allowed_symbols = allowedSymbols;
    publicPayload.allowed_functions = allowedFunctions;
    publicPayload.response_guidance =
      values.responseGuidance?.trim() ||
      'Escribe una expresión equivalente usando únicamente los símbolos y funciones indicados.';
    publicPayload.maximum_latex_length = 4096;
    grading = {
      allowed_functions: allowedFunctions,
      allowed_symbols: allowedSymbols,
      equivalence_strategy: values.mathStrategy,
      expected_mathjson: JSON.parse(values.accepted),
      symbol_assumptions: symbolAssumptions,
    };
  }
  return {
    ...(media.authoring ? { authoring: media.authoring } : {}),
    feedback: {
      correct: values.feedbackCorrect,
      general: values.feedbackGeneral,
      incorrect: values.feedbackIncorrect,
    },
    grading,
    public: publicPayload,
    schema_version: 1,
    type,
    ...(media.workedSolution ? { worked_solution: media.workedSolution } : {}),
  };
}

export function QuestionRevisionWorkflow({
  bankId,
  canApprove,
  canReview,
  canSubmit,
  questionId,
  revision,
  slug,
}: Readonly<{
  bankId: string;
  canApprove: boolean;
  canReview: boolean;
  canSubmit: boolean;
  questionId: string;
  revision: { id: string; lock_version: number; status: string };
  slug: string;
}>) {
  const router = useRouter();
  const [message, setMessage] = useState('');
  const transition = useAssessmentMutation(
    (action: 'approve' | 'request-changes' | 'submit-review') =>
      transitionQuestionRevision(
        { bankId, questionId, revisionId: revision.id, slug },
        action,
        {
          expected_version: revision.lock_version,
          note: message,
        },
      ),
  );
  async function submitTransition(
    action: 'approve' | 'request-changes' | 'submit-review',
  ) {
    try {
      await transition.mutateAsync(action);
      router.refresh();
    } catch {
      // React Query conserva el error visible en este panel.
    }
  }
  return (
    <section className="assessment-revision-workflow assessment-revision-workflow--wide">
      <header>
        <GitPullRequest />
        <div>
          <p>Estado editorial</p>
          <h2>{statusLabel(revision.status)}</h2>
        </div>
      </header>
      <div className="assessment-revision-workflow__wide-body">
        <div>
          <Label htmlFor="question-transition-note-wide">
            Nota para el equipo
          </Label>
          <Textarea
            id="question-transition-note-wide"
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Documenta evidencia, cambios solicitados o criterio de aprobación."
            value={message}
          />
        </div>
        <div className="assessment-revision-workflow__actions">
          {canSubmit &&
          ['draft', 'changes_requested'].includes(revision.status) ? (
            <Button
              disabled={transition.isPending}
              onClick={() => void submitTransition('submit-review')}
              type="button"
            >
              Enviar a revisión
            </Button>
          ) : null}
          {canReview && revision.status === 'in_review' ? (
            <Button
              disabled={transition.isPending}
              onClick={() => void submitTransition('request-changes')}
              type="button"
              variant="outline"
            >
              Solicitar cambios
            </Button>
          ) : null}
          {canApprove && revision.status === 'in_review' ? (
            <Button
              disabled={transition.isPending}
              onClick={() => void submitTransition('approve')}
              type="button"
            >
              Aprobar y crear versión
            </Button>
          ) : null}
        </div>
      </div>
      <MutationError error={transition.error} />
    </section>
  );
}

export function BankList({
  banks,
  slug,
}: Readonly<{ banks: QuestionBankPage; slug: string }>) {
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'active' | 'all' | 'archived'>('active');
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const visibleBanks = banks.results.filter(
    (bank) =>
      (status === 'all' || bank.status === status) &&
      (!normalizedQuery ||
        `${bank.name} ${bank.slug} ${bank.description}`
          .toLocaleLowerCase()
          .includes(normalizedQuery)),
  );
  return (
    <section className="assessment-bank-library">
      <div className="assessment-bank-library__toolbar">
        <label>
          <Search />
          <span className="sr-only">Buscar banco</span>
          <Input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar bancos…"
            value={query}
          />
        </label>
        <div aria-label="Filtrar bancos" role="group">
          <SlidersHorizontal aria-hidden="true" />
          {(
            [
              ['active', 'Activos'],
              ['archived', 'Archivados'],
              ['all', 'Todos'],
            ] as const
          ).map(([value, label]) => (
            <button
              aria-pressed={status === value}
              data-active={status === value}
              key={value}
              onClick={() => setStatus(value)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <span className="assessment-library-count">
          {visibleBanks.length} de {banks.count}
        </span>
      </div>
      {visibleBanks.length ? (
        <ul className="assessment-resource-list">
          {visibleBanks.map((bank) => (
            <li key={bank.id}>
              <span className="assessment-resource-list__icon">
                <Database />
              </span>
              <div className="assessment-resource-list__body">
                <h3>{bank.name}</h3>
                <p>{bank.description || 'Sin descripción.'}</p>
              </div>
              <div className="assessment-resource-list__meta">
                <span className="assessment-status" data-status={bank.status}>
                  {bank.status === 'active' ? 'Activo' : 'Archivado'}
                </span>
                <small>
                  {new Intl.DateTimeFormat('es-CO', {
                    dateStyle: 'medium',
                  }).format(new Date(bank.updated_at))}
                </small>
              </div>
              <Button
                asChild
                aria-label={`Abrir ${bank.name}`}
                size="icon-sm"
                variant="ghost"
              >
                <a
                  href={`/organizaciones/${slug}/evaluaciones/bancos/${bank.id}`}
                >
                  <ArrowRight />
                </a>
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="assessment-empty">
          <Database />
          <h3>No hay bancos con este filtro</h3>
          <p>Ajusta la búsqueda o consulta otro estado editorial.</p>
        </div>
      )}
    </section>
  );
}

export function QuestionList({
  bankId,
  questions,
  slug,
}: Readonly<{
  bankId: string;
  questions: QuestionPage;
  slug: string;
}>) {
  const router = useRouter();
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'all' | 'approved' | 'open'>('all');
  const createRevision = useAssessmentMutation(
    (question: { id: string; version: number }) =>
      createQuestionRevisionFromVersion(
        slug,
        bankId,
        question.id,
        question.version,
      ),
  );
  const normalizedQuery = query.trim().toLocaleLowerCase();
  const visibleQuestions = questions.results.filter(
    (question) =>
      (!normalizedQuery ||
        `${question.code} ${questionPreviewText(question.preview)} ${questionTypeLabel(question.type)}`
          .toLocaleLowerCase()
          .includes(normalizedQuery)) &&
      (status === 'all' ||
        (status === 'open' && Boolean(question.open_revision_id)) ||
        (status === 'approved' &&
          Boolean(question.latest_version_number) &&
          !question.open_revision_id)),
  );
  return (
    <section className="assessment-question-library">
      <div className="assessment-question-library__toolbar">
        <label>
          <Search />
          <span className="sr-only">Buscar pregunta por código</span>
          <Input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar por contenido, tipo o código…"
            value={query}
          />
        </label>
        <div aria-label="Filtrar preguntas" role="group">
          <SlidersHorizontal aria-hidden="true" />
          {(
            [
              ['all', 'Todas'],
              ['open', 'En trabajo'],
              ['approved', 'Aprobadas'],
            ] as const
          ).map(([value, label]) => (
            <button
              aria-pressed={status === value}
              data-active={status === value}
              key={value}
              onClick={() => setStatus(value)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <span className="assessment-library-count">
          {visibleQuestions.length} de {questions.count}
        </span>
      </div>
      {visibleQuestions.length ? (
        <ul className="assessment-question-list">
          {visibleQuestions.map((question) => {
            const excerpt = questionPreviewText(question.preview);
            return (
              <li key={question.id}>
                <div className="assessment-question-list__topline">
                  <span>{questionTypeLabel(question.type)}</span>
                  <span
                    className="assessment-status"
                    data-status={question.open_revision_status ?? 'approved'}
                  >
                    {statusLabel(
                      question.open_revision_status ??
                        (question.latest_version_number
                          ? 'approved'
                          : 'without_revision'),
                    )}
                  </span>
                </div>
                <p className="assessment-question-list__code">
                  {question.code}
                </p>
                <h3>{excerpt || 'Pregunta sin enunciado disponible'}</h3>
                <div className="assessment-question-list__version">
                  <span>
                    {question.latest_version_number
                      ? `Versión ${question.latest_version_number}`
                      : 'Sin versión aprobada'}
                  </span>
                  {question.open_revision_id ? (
                    <span>Revisión abierta</span>
                  ) : null}
                </div>
                <div className="assessment-question-list__actions">
                  <QuestionPreviewDialog
                    bankId={bankId}
                    code={question.code}
                    questionId={question.id}
                    slug={slug}
                  />
                  {question.open_revision_id ? (
                    <Button asChild size="sm" variant="outline">
                      <a
                        href={`/organizaciones/${slug}/evaluaciones/bancos/${bankId}/preguntas/${question.id}/revisiones/${question.open_revision_id}`}
                      >
                        Editar <ArrowRight data-icon="inline-end" />
                      </a>
                    </Button>
                  ) : question.latest_version_number ? (
                    <Button
                      disabled={createRevision.isPending}
                      onClick={async () => {
                        try {
                          const revision = await createRevision.mutateAsync({
                            id: question.id,
                            version: question.latest_version_number!,
                          });
                          router.push(
                            `/organizaciones/${slug}/evaluaciones/bancos/${bankId}/preguntas/${question.id}/revisiones/${revision.id}`,
                          );
                        } catch {
                          // React Query conserva el error para el panel.
                        }
                      }}
                      size="sm"
                      type="button"
                      variant="outline"
                    >
                      Nueva revisión
                    </Button>
                  ) : (
                    <span className="assessment-question-list__locked">
                      Sin contenido editable
                    </span>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      ) : (
        <div className="assessment-empty">
          <BookOpenCheck />
          <h3>No hay preguntas con este filtro</h3>
          <p>
            Ajusta la búsqueda o inicia una nueva pregunta desde el encabezado.
          </p>
        </div>
      )}
      <MutationError error={createRevision.error} />
    </section>
  );
}

function questionPreviewText(preview: Record<string, unknown> | null) {
  if (!preview) return '';
  const fragments: string[] = [];
  const pending: unknown[] = [preview.prompt];
  while (pending.length && fragments.join(' ').length < 320) {
    const current = pending.shift();
    if (Array.isArray(current)) {
      pending.unshift(...current);
      continue;
    }
    if (!current || typeof current !== 'object') continue;
    const node = current as Record<string, unknown>;
    if (typeof node.text === 'string') fragments.push(node.text);
    const attrs = node.attrs;
    if (attrs && typeof attrs === 'object') {
      const latex = (attrs as Record<string, unknown>).latex;
      if (typeof latex === 'string') fragments.push(`$${latex}$`);
      const altText = (attrs as Record<string, unknown>).altText;
      if (typeof altText === 'string') fragments.push(altText);
    }
    if (Array.isArray(node.content)) pending.push(...node.content);
  }
  return fragments.join(' ').replace(/\s+/g, ' ').trim().slice(0, 260);
}

function questionTypeLabel(type: string | null) {
  return QUESTION_TYPES.find(([value]) => value === type)?.[1] ?? 'Pregunta';
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    approved: 'Aprobada',
    changes_requested: 'Cambios solicitados',
    draft: 'Borrador',
    in_review: 'En revisión',
    without_revision: 'Sin revisión',
  };
  return labels[status] ?? status;
}

export function Field({
  children,
  error,
  hint,
  label,
  name,
}: Readonly<{
  children: React.ReactNode;
  error?: string | undefined;
  hint?: string | undefined;
  label: string;
  name: string;
}>) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={name}>{label}</Label>
      {children}
      {hint ? <p className="text-xs text-muted-foreground">{hint}</p> : null}
      {error ? (
        <p className="text-xs text-destructive" role="alert">
          {error}
        </p>
      ) : null}
    </div>
  );
}

export function MutationError({ error }: Readonly<{ error: Error | null }>) {
  return error ? (
    <div className="assessment-error" role="alert">
      <strong>No se guardó el cambio</strong>
      <p>{error.message}</p>
    </div>
  ) : null;
}

export function SubmitState({
  error,
  label,
  pending,
}: Readonly<{ error: Error | null; label: string; pending: boolean }>) {
  return (
    <div className="flex items-end gap-3">
      <Button disabled={pending} type="submit">
        {pending ? 'Procesando…' : label}
      </Button>
      <MutationError error={error} />
    </div>
  );
}
