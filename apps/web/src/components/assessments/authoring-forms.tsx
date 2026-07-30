'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import {
  ArrowDown,
  ArrowRight,
  ArrowUp,
  BookOpenCheck,
  CheckCircle2,
  ClipboardCheck,
  Code2,
  Database,
  Eye,
  FileCheck2,
  GitPullRequest,
  Layers3,
  LockKeyhole,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  createAssessment,
  createQuestion,
  createQuestionBank,
  transitionQuestionRevision,
  updateQuestionBank,
  updateQuestionRevision,
  useAssessmentMutation,
} from '@/lib/assessments/hooks';
import type { QuestionBankPage, QuestionPage } from '@/lib/assessments/server';

const assessmentSchema = z.object({
  attempt_limit: z.number().int().positive().max(20),
  description: z.string().trim().max(5000),
  pass_basis_points: z.number().int().min(0).max(10000),
  slug: z
    .string()
    .trim()
    .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Usa minúsculas y guiones.'),
  time_limit_minutes: z.number().int().positive().max(10080),
  title: z.string().trim().min(1, 'Escribe el título.').max(200),
});
type AssessmentValues = z.infer<typeof assessmentSchema>;

export function AssessmentCreateForm({ slug }: Readonly<{ slug: string }>) {
  const router = useRouter();
  const mutation = useAssessmentMutation((values: AssessmentValues) =>
    createAssessment(slug, {
      ...values,
      feedback_mode: 'full_after_grading',
      shuffle_items: false,
      shuffle_sections: false,
    }),
  );
  const form = useForm<AssessmentValues>({
    defaultValues: {
      attempt_limit: 2,
      description: '',
      pass_basis_points: 6000,
      slug: '',
      time_limit_minutes: 45,
      title: '',
    },
    resolver: zodResolver(assessmentSchema),
  });
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
    <div className="assessment-studio-grid mt-6">
      <form
        className="assessment-workbench"
        noValidate
        onSubmit={form.handleSubmit(submit)}
      >
        <BuilderSection
          description="Define una identidad reconocible. El slug será la referencia estable en URLs y API."
          icon={<Layers3 />}
          number="01"
          title="Identidad del instrumento"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <Field
              error={form.formState.errors.title?.message}
              label="Título de la evaluación"
              name="assessment-title"
            >
              <Input
                id="assessment-title"
                placeholder="Ej. Diagnóstico de cálculo diferencial"
                {...form.register('title')}
              />
            </Field>
            <Field
              error={form.formState.errors.slug?.message}
              hint="Identificador permanente, en minúsculas."
              label="Slug"
              name="assessment-slug"
            >
              <Input
                id="assessment-slug"
                placeholder="diagnostico-calculo"
                {...form.register('slug')}
              />
            </Field>
            <div className="sm:col-span-2">
              <Field label="Propósito y alcance" name="assessment-description">
                <Textarea
                  className="min-h-28"
                  id="assessment-description"
                  placeholder="Explica qué evidencia recoge el instrumento y para qué población está diseñado."
                  {...form.register('description')}
                />
              </Field>
            </div>
          </div>
        </BuilderSection>
        <BuilderSection
          description="Configura límites operativos. Podrás refinarlos antes de enviar la revisión."
          icon={<ShieldCheck />}
          number="02"
          title="Política de aplicación"
        >
          <div className="grid gap-5 sm:grid-cols-3">
            <Field label="Duración" name="assessment-time">
              <Input
                id="assessment-time"
                min={1}
                type="number"
                {...form.register('time_limit_minutes', {
                  valueAsNumber: true,
                })}
              />
              <p className="assessment-control-suffix">minutos</p>
            </Field>
            <Field label="Oportunidades" name="assessment-attempts">
              <Input
                id="assessment-attempts"
                min={1}
                type="number"
                {...form.register('attempt_limit', { valueAsNumber: true })}
              />
              <p className="assessment-control-suffix">intentos</p>
            </Field>
            <Field
              hint="Se almacena con precisión de puntos base."
              label="Umbral de aprobación"
              name="assessment-pass"
            >
              <Input
                id="assessment-pass"
                max={10000}
                min={0}
                type="number"
                {...form.register('pass_basis_points', {
                  valueAsNumber: true,
                })}
              />
            </Field>
          </div>
        </BuilderSection>
        <div className="assessment-workbench-footer">
          <div>
            <p className="font-medium">Se creará como borrador editable</p>
            <p className="text-xs text-muted-foreground">
              Ninguna evaluación se entrega hasta aprobar una versión y activar
              una entrega.
            </p>
          </div>
          <SubmitState
            error={mutation.error}
            label="Crear y abrir compositor"
            pending={mutation.isPending}
          />
        </div>
      </form>
      <aside className="assessment-context-rail">
        <p className="assessment-rail-kicker">Ruta de trabajo</p>
        <h2 className="assessment-rail-title">
          De la intención a una versión auditable
        </h2>
        <ol className="assessment-step-list">
          {[
            ['1', 'Crear identidad', 'Título, propósito y política inicial.'],
            [
              '2',
              'Diseñar composición',
              'Objetivos, secciones y preguntas aprobadas.',
            ],
            [
              '3',
              'Revisar y aprobar',
              'Readiness, trazabilidad y snapshot inmutable.',
            ],
            [
              '4',
              'Programar entrega',
              'Ventana, release y población asignada.',
            ],
          ].map(([step, title, description]) => (
            <li key={step}>
              <span>{step}</span>
              <div>
                <strong>{title}</strong>
                <p>{description}</p>
              </div>
            </li>
          ))}
        </ol>
        <div className="assessment-assurance">
          <ShieldCheck />
          <p>
            Guardado explícito, control de concurrencia y separación de claves
            de calificación.
          </p>
        </div>
      </aside>
    </div>
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

export function QuestionBankCreateForm({ slug }: Readonly<{ slug: string }>) {
  const router = useRouter();
  const mutation = useAssessmentMutation((values: BankValues) =>
    createQuestionBank(slug, values),
  );
  const form = useForm<BankValues>({
    defaultValues: { description: '', name: '', slug: '' },
    resolver: zodResolver(bankSchema),
  });
  async function submit(values: BankValues) {
    try {
      await mutation.mutateAsync(bankSchema.parse(values));
      form.reset();
      router.refresh();
    } catch {
      // React Query conserva y presenta el error en el formulario.
    }
  }
  return (
    <form
      className="assessment-inline-creator"
      noValidate
      onSubmit={form.handleSubmit(submit)}
    >
      <div className="assessment-inline-creator__intro">
        <span className="assessment-icon-box">
          <ClipboardCheck />
        </span>
        <div>
          <h2>Crear banco institucional</h2>
          <p>Separa preguntas por disciplina, propósito o equipo editorial.</p>
        </div>
      </div>
      <Field
        error={form.formState.errors.name?.message}
        label="Nombre del banco"
        name="bank-name"
      >
        <Input
          id="bank-name"
          placeholder="Ej. Fundamentos de estadística"
          {...form.register('name')}
        />
      </Field>
      <Field
        error={form.formState.errors.slug?.message}
        label="Slug"
        name="bank-slug"
      >
        <Input
          id="bank-slug"
          placeholder="fundamentos-estadistica"
          {...form.register('slug')}
        />
      </Field>
      <div className="assessment-inline-creator__description">
        <Field label="Descripción" name="bank-description">
          <Textarea id="bank-description" {...form.register('description')} />
        </Field>
      </div>
      <div className="assessment-inline-creator__action">
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
] as const;
type QuestionType = (typeof QUESTION_TYPES)[number][0];

const questionSchema = z
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
    options: z.string(),
    prompt: z.string().trim().min(1, 'Escribe el enunciado.').max(5000),
    tolerance: z.string(),
    type: z.enum([
      'single_choice',
      'multiple_choice',
      'true_false',
      'numeric',
      'short_text',
      'long_text',
      'ordering',
      'matching',
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
  });
type QuestionValues = z.infer<typeof questionSchema>;

function promptDocument(text: string) {
  return {
    content: [
      {
        attrs: { nodeId: crypto.randomUUID() },
        content: [{ text, type: 'text' }],
        type: 'paragraph',
      },
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

export function buildQuestionDefinition(values: QuestionValues) {
  const type = values.type;
  const publicPayload: Record<string, unknown> = {
    prompt: promptDocument(values.prompt),
    schema_version: 1,
    type,
  };
  let grading: Record<string, unknown>;
  const optionLabels = lines(values.options);
  const options = optionLabels.map((label, index) => ({
    id: `o${index + 1}`,
    label,
  }));
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
    grading = {
      correct_value: values.accepted.trim(),
      tolerance: values.tolerance.trim() || '0',
    };
  } else if (type === 'short_text') {
    grading = {
      accepted_answers: lines(values.accepted),
      case_sensitive: false,
    };
  } else if (type === 'long_text') {
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
  } else {
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
  }
  return {
    feedback: {
      correct: values.feedbackCorrect,
      general: values.feedbackGeneral,
      incorrect: values.feedbackIncorrect,
    },
    grading,
    public: publicPayload,
    schema_version: 1,
    type,
  };
}

export function QuestionCreateForm({
  bankId,
  slug,
}: Readonly<{ bankId: string; slug: string }>) {
  const router = useRouter();
  const mutation = useAssessmentMutation((values: QuestionValues) =>
    createQuestion(slug, bankId, {
      code: values.code,
      definition: buildQuestionDefinition(values),
      type: values.type,
    }),
  );
  const form = useForm<QuestionValues>({
    defaultValues: {
      accepted: 'o1',
      code: '',
      feedbackCorrect: 'Respuesta correcta.',
      feedbackGeneral: 'Revisa el objetivo asociado.',
      feedbackIncorrect: 'Revisa tu procedimiento.',
      options: 'Primera opción\nSegunda opción',
      prompt: '',
      tolerance: '0',
      type: 'single_choice',
    },
    resolver: zodResolver(questionSchema),
  });
  const selectedType = useWatch({ control: form.control, name: 'type' });
  const watchedPrompt = useWatch({ control: form.control, name: 'prompt' });
  const watchedCode = useWatch({ control: form.control, name: 'code' });
  const watchedOptions = useWatch({ control: form.control, name: 'options' });
  const watchedAccepted = useWatch({
    control: form.control,
    name: 'accepted',
  });
  const previewOptions = lines(watchedOptions);
  useEffect(() => {
    const optionIds = previewOptions.map((_, index) => `o${index + 1}`);
    const acceptedIds = watchedAccepted
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean);
    let normalized: string | undefined;
    if (
      selectedType === 'ordering' &&
      (acceptedIds.length !== optionIds.length ||
        acceptedIds.some((id) => !optionIds.includes(id)))
    ) {
      normalized = optionIds.join(',');
    } else if (selectedType === 'matching' && optionIds.length % 2 === 0) {
      const midpoint = optionIds.length / 2;
      const defaultPairs = Array.from(
        { length: midpoint },
        (_, index) => `l${index + 1}:r${index + 1}`,
      ).join(',');
      const validPairs =
        acceptedIds.length === midpoint &&
        acceptedIds.every((pair) => /^l[1-9][0-9]*:r[1-9][0-9]*$/.test(pair));
      if (!validPairs) normalized = defaultPairs;
    } else if (
      ['single_choice', 'multiple_choice'].includes(selectedType) &&
      (!acceptedIds.length || acceptedIds.some((id) => !optionIds.includes(id)))
    ) {
      normalized = optionIds[0] ?? '';
    } else if (
      selectedType === 'true_false' &&
      !['true', 'false'].includes(watchedAccepted)
    ) {
      normalized = 'true';
    }
    if (normalized !== undefined && normalized !== watchedAccepted) {
      form.setValue('accepted', normalized, { shouldDirty: true });
    }
  }, [form, previewOptions, selectedType, watchedAccepted]);
  const selectedTypeLabel =
    QUESTION_TYPES.find(([value]) => value === selectedType)?.[1] ??
    selectedType;
  async function submit(values: QuestionValues) {
    try {
      await mutation.mutateAsync(questionSchema.parse(values));
      form.reset();
      router.refresh();
    } catch {
      // React Query conserva y presenta el error en el formulario.
    }
  }
  return (
    <div className="assessment-studio-grid mt-5">
      <form
        className="assessment-workbench"
        noValidate
        onSubmit={form.handleSubmit(submit)}
      >
        <BuilderSection
          description="El código permanece estable aunque la pregunta acumule revisiones y versiones."
          icon={<Sparkles />}
          number="01"
          title="Identidad y formato"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <Field
              error={form.formState.errors.code?.message}
              label="Código estable"
              name="question-code"
            >
              <Input
                id="question-code"
                placeholder="MAT-DER-001"
                {...form.register('code')}
              />
            </Field>
            <Field label="Tipo de interacción" name="question-type">
              <select
                className="academic-control"
                id="question-type"
                {...form.register('type')}
              >
                {QUESTION_TYPES.map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <div className="assessment-type-note">
            <ClipboardCheck />
            <div>
              <strong>{selectedTypeLabel}</strong>
              <p>{typeDescription(selectedType)}</p>
            </div>
          </div>
        </BuilderSection>
        <BuilderSection
          description="Redacta una consigna autónoma. La estructura semántica se construye y valida automáticamente."
          icon={<MessageSquareText />}
          number="02"
          title="Contenido de la pregunta"
        >
          <Field
            error={form.formState.errors.prompt?.message}
            label="Enunciado"
            name="question-prompt"
          >
            <Textarea
              className="min-h-32 text-base leading-7"
              id="question-prompt"
              placeholder="Formula la situación, incluye los datos necesarios y especifica qué debe responder el estudiante."
              {...form.register('prompt')}
            />
          </Field>
          {[
            'single_choice',
            'multiple_choice',
            'ordering',
            'matching',
          ].includes(selectedType) ? (
            <Field
              error={form.formState.errors.options?.message}
              hint={
                selectedType === 'matching'
                  ? 'Usa un número par: la primera mitad será la columna izquierda y la segunda, la derecha.'
                  : 'Una opción por línea. La interfaz asigna IDs o1, o2, o3…'
              }
              label={
                selectedType === 'matching'
                  ? 'Elementos de ambas columnas'
                  : 'Opciones de respuesta'
              }
              name="question-options"
            >
              <Textarea
                className="min-h-36 font-mono text-sm"
                id="question-options"
                {...form.register('options')}
              />
            </Field>
          ) : null}
        </BuilderSection>
        <BuilderSection
          description="La clave queda en el snapshot secreto y nunca viaja al navegador del learner."
          icon={<ShieldCheck />}
          number="03"
          title="Calificación y feedback"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <div className={selectedType === 'numeric' ? '' : 'sm:col-span-2'}>
              <Field
                error={form.formState.errors.accepted?.message}
                hint={answerHint(selectedType)}
                label={
                  selectedType === 'long_text'
                    ? 'Rúbrica interna'
                    : 'Clave de respuesta'
                }
                name="question-answer"
              >
                {selectedType === 'true_false' ? (
                  <select
                    className="academic-control"
                    id="question-answer"
                    {...form.register('accepted')}
                  >
                    <option value="true">Verdadero</option>
                    <option value="false">Falso</option>
                  </select>
                ) : ['single_choice', 'multiple_choice'].includes(
                    selectedType,
                  ) ? (
                  <ChoiceAnswerKey
                    accepted={watchedAccepted}
                    multiple={selectedType === 'multiple_choice'}
                    onChange={(value) =>
                      form.setValue('accepted', value, {
                        shouldDirty: true,
                        shouldValidate: true,
                      })
                    }
                    options={previewOptions}
                  />
                ) : selectedType === 'ordering' ? (
                  <OrderingAnswerKey
                    accepted={watchedAccepted}
                    onChange={(value) =>
                      form.setValue('accepted', value, {
                        shouldDirty: true,
                        shouldValidate: true,
                      })
                    }
                    options={previewOptions}
                  />
                ) : selectedType === 'matching' ? (
                  <MatchingAnswerKey
                    accepted={watchedAccepted}
                    onChange={(value) =>
                      form.setValue('accepted', value, {
                        shouldDirty: true,
                        shouldValidate: true,
                      })
                    }
                    options={previewOptions}
                  />
                ) : (
                  <Textarea
                    className="min-h-24"
                    id="question-answer"
                    {...form.register('accepted')}
                  />
                )}
              </Field>
            </div>
            {selectedType === 'numeric' ? (
              <Field
                error={form.formState.errors.tolerance?.message}
                hint="Diferencia máxima aceptada respecto al valor exacto."
                label="Tolerancia absoluta"
                name="question-tolerance"
              >
                <Input
                  id="question-tolerance"
                  inputMode="decimal"
                  {...form.register('tolerance')}
                />
              </Field>
            ) : null}
          </div>
          <details className="assessment-feedback-panel">
            <summary>Personalizar retroalimentación</summary>
            <div className="mt-4 grid gap-4 sm:grid-cols-3">
              <Field label="Respuesta correcta" name="feedback-correct">
                <Textarea
                  id="feedback-correct"
                  {...form.register('feedbackCorrect')}
                />
              </Field>
              <Field label="Respuesta incorrecta" name="feedback-incorrect">
                <Textarea
                  id="feedback-incorrect"
                  {...form.register('feedbackIncorrect')}
                />
              </Field>
              <Field label="Orientación general" name="feedback-general">
                <Textarea
                  id="feedback-general"
                  {...form.register('feedbackGeneral')}
                />
              </Field>
            </div>
          </details>
        </BuilderSection>
        <div className="assessment-workbench-footer">
          <div>
            <p className="font-medium">Borrador sujeto a workflow editorial</p>
            <p className="text-xs text-muted-foreground">
              Crear no aprueba ni publica; conserva separación entre autoría y
              revisión.
            </p>
          </div>
          <SubmitState
            error={mutation.error}
            label="Crear borrador de pregunta"
            pending={mutation.isPending}
          />
        </div>
      </form>
      <aside className="assessment-preview-rail">
        <div className="assessment-preview-rail__header">
          <span>Vista previa del learner</span>
          <strong>{selectedTypeLabel}</strong>
        </div>
        <div className="assessment-question-preview">
          <p className="assessment-question-preview__meta">
            Pregunta sin puntaje asignado
          </p>
          <h3>
            {watchedPrompt.trim() ||
              'El enunciado aparecerá aquí mientras escribes.'}
          </h3>
          {previewOptions.length ? (
            <ol>
              {previewOptions.map((option, index) => (
                <li key={`${option}-${index}`}>
                  <span>{String.fromCharCode(65 + index)}</span>
                  {option}
                </li>
              ))}
            </ol>
          ) : (
            <div className="assessment-preview-answer">
              {selectedType === 'long_text'
                ? 'Área de respuesta extensa'
                : selectedType === 'numeric'
                  ? 'Campo de respuesta numérica'
                  : 'Campo de respuesta'}
            </div>
          )}
        </div>
        <div className="assessment-quality-list">
          <p className="assessment-rail-kicker">Control de calidad</p>
          <ul>
            <QualityItem
              label="Código estable"
              ready={!form.formState.errors.code && !!watchedCode.trim()}
            />
            <QualityItem
              label="Enunciado completo"
              ready={watchedPrompt.trim().length >= 10}
            />
            <QualityItem
              label="Clave configurada"
              ready={watchedAccepted.trim().length > 0}
            />
            <QualityItem
              label="Contrato validado antes de enviar"
              ready={form.formState.isValid}
            />
          </ul>
        </div>
      </aside>
    </div>
  );
}

function OrderingAnswerKey({
  accepted,
  onChange,
  options,
}: Readonly<{
  accepted: string;
  onChange: (value: string) => void;
  options: readonly string[];
}>) {
  const byId = new Map(
    options.map((option, index) => [`o${index + 1}`, option]),
  );
  const requested = accepted
    .split(',')
    .map((item) => item.trim())
    .filter((id) => byId.has(id));
  const order = [
    ...new Set([...requested, ...options.map((_, index) => `o${index + 1}`)]),
  ];
  function move(index: number, direction: -1 | 1) {
    const target = index + direction;
    if (target < 0 || target >= order.length) return;
    const next = [...order];
    [next[index], next[target]] = [next[target]!, next[index]!];
    onChange(next.join(','));
  }
  return (
    <ol className="assessment-order-key" id="question-answer">
      {order.map((id, index) => (
        <li key={id}>
          <span>{index + 1}</span>
          <strong>{byId.get(id)}</strong>
          <div>
            <Button
              aria-label={`Subir ${byId.get(id)}`}
              disabled={index === 0}
              onClick={() => move(index, -1)}
              size="icon-sm"
              type="button"
              variant="ghost"
            >
              <ArrowUp />
            </Button>
            <Button
              aria-label={`Bajar ${byId.get(id)}`}
              disabled={index === order.length - 1}
              onClick={() => move(index, 1)}
              size="icon-sm"
              type="button"
              variant="ghost"
            >
              <ArrowDown />
            </Button>
          </div>
        </li>
      ))}
    </ol>
  );
}

function MatchingAnswerKey({
  accepted,
  onChange,
  options,
}: Readonly<{
  accepted: string;
  onChange: (value: string) => void;
  options: readonly string[];
}>) {
  const midpoint = Math.floor(options.length / 2);
  const left = options.slice(0, midpoint);
  const right = options.slice(midpoint);
  const pairs = new Map(
    accepted
      .split(',')
      .map((pair) => pair.trim().split(':'))
      .filter(
        (pair): pair is [string, string] =>
          pair.length === 2 && Boolean(pair[0]) && Boolean(pair[1]),
      ),
  );
  function select(leftIndex: number, rightId: string) {
    const next = new Map(pairs);
    next.set(`l${leftIndex + 1}`, rightId);
    onChange(
      left
        .map(
          (_, index) =>
            `l${index + 1}:${next.get(`l${index + 1}`) ?? `r${index + 1}`}`,
        )
        .join(','),
    );
  }
  if (options.length % 2 !== 0) {
    return (
      <div className="assessment-answer-key-empty" id="question-answer">
        Agrega el mismo número de elementos para ambas columnas.
      </div>
    );
  }
  return (
    <div className="assessment-matching-key" id="question-answer">
      {left.map((label, index) => (
        <div key={`l${index + 1}`}>
          <strong>{label}</strong>
          <ArrowRight />
          <Label className="sr-only" htmlFor={`match-answer-${index}`}>
            Correspondencia para {label}
          </Label>
          <select
            className="academic-control"
            id={`match-answer-${index}`}
            onChange={(event) => select(index, event.target.value)}
            value={pairs.get(`l${index + 1}`) ?? `r${index + 1}`}
          >
            {right.map((rightLabel, rightIndex) => (
              <option key={`r${rightIndex + 1}`} value={`r${rightIndex + 1}`}>
                {rightLabel}
              </option>
            ))}
          </select>
        </div>
      ))}
    </div>
  );
}

function ChoiceAnswerKey({
  accepted,
  multiple,
  onChange,
  options,
}: Readonly<{
  accepted: string;
  multiple: boolean;
  onChange: (value: string) => void;
  options: readonly string[];
}>) {
  const selected = new Set(
    accepted
      .split(',')
      .map((item) => item.trim())
      .filter(Boolean),
  );
  if (!options.length) {
    return (
      <div className="assessment-answer-key-empty" id="question-answer">
        Agrega opciones para configurar la respuesta correcta.
      </div>
    );
  }
  return (
    <fieldset className="assessment-answer-key" id="question-answer">
      <legend className="sr-only">Clave de respuesta</legend>
      {options.map((option, index) => {
        const optionId = `o${index + 1}`;
        const checked = selected.has(optionId);
        return (
          <label
            className="assessment-answer-key__option"
            data-selected={checked}
            key={`${optionId}-${option}`}
          >
            <input
              aria-label={`Marcar ${option} como correcta`}
              checked={checked}
              name="question-correct-answer"
              onChange={() => {
                if (!multiple) {
                  onChange(optionId);
                  return;
                }
                const next = new Set(selected);
                if (checked) next.delete(optionId);
                else next.add(optionId);
                onChange(
                  options
                    .map((_, optionIndex) => `o${optionIndex + 1}`)
                    .filter((id) => next.has(id))
                    .join(','),
                );
              }}
              type={multiple ? 'checkbox' : 'radio'}
            />
            <span className="assessment-answer-key__letter">
              {String.fromCharCode(65 + index)}
            </span>
            <span>{option}</span>
            <small>{checked ? 'Correcta' : 'Marcar'}</small>
          </label>
        );
      })}
    </fieldset>
  );
}

function typeDescription(type: QuestionType) {
  const descriptions: Record<QuestionType, string> = {
    long_text:
      'Respuesta abierta con decisión humana, rúbrica y correcciones append-only.',
    matching:
      'Relación explícita entre dos conjuntos; se valida cobertura de la columna izquierda.',
    multiple_choice:
      'Una o más opciones correctas, sin puntaje parcial en esta fase.',
    numeric:
      'Comparación Decimal determinista con tolerancia absoluta controlada.',
    ordering:
      'Secuencia completa; cada opción debe aparecer exactamente una vez.',
    short_text:
      'Comparación normalizada contra una lista de respuestas aceptadas.',
    single_choice:
      'Una sola respuesta correcta entre opciones mutuamente excluyentes.',
    true_false: 'Decisión binaria con etiquetas claras para el estudiante.',
  };
  return descriptions[type];
}

function answerHint(type: QuestionType) {
  const hints: Record<QuestionType, string> = {
    long_text: 'Sólo será visible para quien califica.',
    matching: 'Selecciona una correspondencia para cada elemento.',
    multiple_choice:
      'Marca todas las opciones que deben considerarse correctas.',
    numeric: 'Decimal sin exponente; admite punto o coma no ambiguos.',
    ordering: 'Organiza las opciones en la secuencia correcta.',
    short_text: 'Una respuesta aceptada por línea.',
    single_choice: 'Marca la única opción correcta.',
    true_false: 'Selecciona el valor correcto.',
  };
  return hints[type];
}

export function QuestionRevisionEditor({
  bankId,
  canApprove,
  canManage,
  canReview,
  canSubmit,
  questionId,
  revision,
  slug,
}: Readonly<{
  bankId: string;
  canApprove: boolean;
  canManage: boolean;
  canReview: boolean;
  canSubmit: boolean;
  questionId: string;
  revision: {
    definition: unknown;
    id: string;
    lock_version: number;
    status: string;
    type: string;
  };
  slug: string;
}>) {
  const router = useRouter();
  const [source, setSource] = useState(
    JSON.stringify(revision.definition, null, 2),
  );
  const [message, setMessage] = useState('');
  const path = {
    bankId,
    questionId,
    revisionId: revision.id,
    slug,
  };
  const save = useAssessmentMutation(async () => {
    let definition: unknown;
    try {
      definition = JSON.parse(source);
    } catch {
      throw new Error('El JSON no es válido.');
    }
    return updateQuestionRevision(path, {
      definition,
      expected_version: revision.lock_version,
    });
  });
  const transition = useAssessmentMutation(
    (action: 'approve' | 'request-changes' | 'submit-review') =>
      transitionQuestionRevision(path, action, {
        expected_version: revision.lock_version,
        note: message,
      }),
  );
  async function finish(operation: Promise<unknown>) {
    try {
      await operation;
      router.refresh();
    } catch {
      // React Query conserva y presenta el error junto al editor.
    }
  }
  const editable =
    canManage &&
    (revision.status === 'draft' || revision.status === 'changes_requested');
  const preview = questionPreviewFromDefinition(source);
  return (
    <div className="assessment-revision-studio mt-6">
      <section className="assessment-revision-editor">
        <header>
          <span className="assessment-icon-box">
            <Code2 />
          </span>
          <div>
            <p className="assessment-rail-kicker">Contrato canónico</p>
            <h2>Definición semántica avanzada</h2>
            <p>
              Tipo {revision.type} · revisión {revision.status} · guardado
              explícito
            </p>
          </div>
          {editable ? (
            <Button
              disabled={save.isPending}
              onClick={() => finish(save.mutateAsync(undefined))}
              type="button"
            >
              Guardar contrato
            </Button>
          ) : (
            <span className="assessment-status" data-status={revision.status}>
              {statusLabel(revision.status)}
            </span>
          )}
        </header>
        <div className="assessment-revision-editor__body">
          <div className="assessment-revision-notice">
            <LockKeyhole />
            <p>
              Las claves y rúbricas permanecen en el payload privado. La vista
              del learner recibe únicamente el snapshot público.
            </p>
          </div>
          <details className="assessment-code-disclosure">
            <summary>Contrato técnico · editar JSON Schema v1</summary>
            <Label className="sr-only" htmlFor="question-definition">
              JSON semántico
            </Label>
            <Textarea
              aria-describedby="question-definition-help"
              className="min-h-[34rem] font-mono text-xs leading-5"
              disabled={!editable}
              id="question-definition"
              onChange={(event) => setSource(event.target.value)}
              spellCheck={false}
              value={source}
            />
          </details>
          <p
            className="text-xs leading-5 text-muted-foreground"
            id="question-definition-help"
          >
            El contrato se valida por Draft 2020-12 y después por invariantes de
            negocio. Los errores se informan con su ruta exacta.
          </p>
          <MutationError error={save.error} />
        </div>
      </section>
      <aside className="assessment-revision-rail">
        <section className="assessment-revision-preview">
          <header>
            <Eye />
            <div>
              <p>Vista pública</p>
              <h2>Experiencia del learner</h2>
            </div>
          </header>
          <article>
            <span>{preview.type}</span>
            <h3>{preview.prompt || 'Enunciado no disponible'}</h3>
            {preview.options.length ? (
              <ol>
                {preview.options.map((option, index) => (
                  <li key={`${option}-${index}`}>
                    <span>{String.fromCharCode(65 + index)}</span>
                    {option}
                  </li>
                ))}
              </ol>
            ) : (
              <div>Campo de respuesta del learner</div>
            )}
          </article>
        </section>
        <section className="assessment-revision-workflow">
          <header>
            <GitPullRequest />
            <div>
              <p>Gobierno editorial</p>
              <h2>Transición de revisión</h2>
            </div>
          </header>
          <Label htmlFor="question-transition-note">Nota para el equipo</Label>
          <Textarea
            id="question-transition-note"
            onChange={(event) => setMessage(event.target.value)}
            placeholder="Documenta evidencia, cambios solicitados o criterio de aprobación."
            value={message}
          />
          <div className="grid gap-2">
            {canSubmit &&
            ['draft', 'changes_requested'].includes(revision.status) ? (
              <Button
                disabled={transition.isPending}
                onClick={() => finish(transition.mutateAsync('submit-review'))}
                type="button"
              >
                Enviar a revisión
              </Button>
            ) : null}
            {canReview && revision.status === 'in_review' ? (
              <Button
                disabled={transition.isPending}
                onClick={() =>
                  finish(transition.mutateAsync('request-changes'))
                }
                type="button"
                variant="outline"
              >
                Solicitar cambios
              </Button>
            ) : null}
            {canApprove && revision.status === 'in_review' ? (
              <Button
                disabled={transition.isPending}
                onClick={() => finish(transition.mutateAsync('approve'))}
                type="button"
              >
                Aprobar y crear versión
              </Button>
            ) : null}
          </div>
          <MutationError error={transition.error} />
        </section>
      </aside>
    </div>
  );
}

function questionPreviewFromDefinition(source: string) {
  try {
    const definition = JSON.parse(source) as {
      public?: {
        options?: { label?: string }[];
        prompt?: {
          content?: { content?: { text?: string }[] }[];
        };
        type?: string;
      };
      type?: string;
    };
    const prompt = (definition.public?.prompt?.content ?? [])
      .flatMap((block) => block.content ?? [])
      .map((node) => node.text ?? '')
      .join(' ')
      .trim();
    return {
      options: (definition.public?.options ?? []).map(
        (option) => option.label ?? '',
      ),
      prompt,
      type: definition.public?.type ?? definition.type ?? 'Pregunta',
    };
  } catch {
    return { options: [] as string[], prompt: '', type: 'JSON inválido' };
  }
}

export function BankList({
  banks,
  slug,
}: Readonly<{ banks: QuestionBankPage; slug: string }>) {
  return (
    <section className="assessment-collection">
      <header className="assessment-collection__header">
        <div>
          <p className="assessment-rail-kicker">Inventario editorial</p>
          <h2>Bancos disponibles</h2>
        </div>
        <span>{banks.count} registros</span>
      </header>
      {banks.results.length ? (
        <ul className="assessment-card-grid">
          {banks.results.map((bank) => (
            <li className="assessment-resource-card" key={bank.id}>
              <div className="assessment-resource-card__top">
                <span className="assessment-icon-box">
                  <Database />
                </span>
                <span className="assessment-status" data-status={bank.status}>
                  {bank.status === 'active' ? 'Activo' : 'Archivado'}
                </span>
              </div>
              <div className="assessment-resource-card__body">
                <p className="assessment-resource-card__code">/{bank.slug}</p>
                <h3>{bank.name}</h3>
                <p>
                  {bank.description ||
                    'Banco institucional sin descripción editorial.'}
                </p>
              </div>
              <Button
                asChild
                className="w-full justify-between"
                variant="outline"
              >
                <a
                  href={`/organizaciones/${slug}/evaluaciones/bancos/${bank.id}`}
                >
                  Abrir espacio de autoría
                  <ArrowRight data-icon="inline-end" />
                </a>
              </Button>
            </li>
          ))}
        </ul>
      ) : (
        <div className="assessment-empty">
          <Database />
          <h3>Aún no hay bancos de preguntas</h3>
          <p>Crea el primero para iniciar el flujo editorial.</p>
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
  return (
    <section className="assessment-collection mt-6">
      <header className="assessment-collection__header">
        <div>
          <p className="assessment-rail-kicker">Contenido del banco</p>
          <h2>Preguntas y revisiones</h2>
        </div>
        <span>{questions.count} preguntas</span>
      </header>
      {questions.results.length ? (
        <ul className="assessment-question-list">
          {questions.results.map((question) => (
            <li key={question.id}>
              <span className="assessment-question-list__icon">
                {question.latest_version_number ? (
                  <FileCheck2 />
                ) : (
                  <BookOpenCheck />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3>{question.code}</h3>
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
                <p>
                  Versión aprobada{' '}
                  {question.latest_version_number
                    ? `v${question.latest_version_number}`
                    : 'pendiente'}
                </p>
              </div>
              {question.open_revision_id ? (
                <Button asChild variant="outline">
                  <a
                    href={`/organizaciones/${slug}/evaluaciones/bancos/${bankId}/preguntas/${question.id}/revisiones/${question.open_revision_id}`}
                  >
                    Continuar revisión
                    <ArrowRight data-icon="inline-end" />
                  </a>
                </Button>
              ) : (
                <span className="assessment-question-list__locked">
                  Snapshot aprobado
                </span>
              )}
            </li>
          ))}
        </ul>
      ) : (
        <div className="assessment-empty">
          <BookOpenCheck />
          <h3>Este banco aún no contiene preguntas</h3>
          <p>Usa el compositor para crear el primer borrador.</p>
        </div>
      )}
    </section>
  );
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

function BuilderSection({
  children,
  description,
  icon,
  number,
  title,
}: Readonly<{
  children: React.ReactNode;
  description: string;
  icon: React.ReactNode;
  number: string;
  title: string;
}>) {
  return (
    <section className="assessment-builder-section">
      <header className="assessment-builder-section__header">
        <span className="assessment-builder-section__number">{number}</span>
        <span className="assessment-icon-box">{icon}</span>
        <div>
          <h2>{title}</h2>
          <p>{description}</p>
        </div>
      </header>
      <div className="assessment-builder-section__body">{children}</div>
    </section>
  );
}

function QualityItem({
  label,
  ready,
}: Readonly<{ label: string; ready: boolean }>) {
  return (
    <li data-ready={ready}>
      <CheckCircle2 />
      <span>{label}</span>
    </li>
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
