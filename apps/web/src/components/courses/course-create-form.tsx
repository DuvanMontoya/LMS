'use client';

import {
  ArrowLeft,
  BookOpenCheck,
  CheckCircle2,
  Clock3,
  FileText,
  GraduationCap,
  Layers3,
  ShieldCheck,
  Target,
} from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useRef, useState } from 'react';

import { Alert, AlertDescription } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { components } from '@/lib/api/generated/platform';
import { useCreateCourse } from '@/lib/courses/hooks';
import { cn } from '@/lib/utils';

type Subject = components['schemas']['Subject'];
type Objective = components['schemas']['Objective'];

export function slugifyCourseTitle(value: string) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es-CO')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 80);
}

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
  const [title, setTitle] = useState('');
  const [courseSlug, setCourseSlug] = useState('');
  const [slugTouched, setSlugTouched] = useState(false);
  const [duration, setDuration] = useState('');
  const [primary, setPrimary] = useState(subjects[0]?.id ?? '');
  const [supporting, setSupporting] = useState<string[]>([]);
  const [selectedObjectives, setSelectedObjectives] = useState<string[]>([]);
  const [error, setError] = useState('');
  const firstField = useRef<HTMLInputElement>(null);
  const errorRef = useRef<HTMLDivElement>(null);
  const alignedSubjects = new Set([primary, ...supporting]);
  const availableObjectives = objectives.filter((objective) =>
    alignedSubjects.has(objective.subject_id),
  );
  const primarySubject = subjects.find((subject) => subject.id === primary);

  async function submit(formData: FormData) {
    setError('');
    if (!primary) {
      setError('Selecciona una asignatura principal.');
      return;
    }
    try {
      const revision = await mutation.mutateAsync({
        description: String(formData.get('description') ?? ''),
        estimated_duration_minutes: duration ? Number(duration) : null,
        learning_objective_ids: selectedObjectives.filter((id) =>
          availableObjectives.some((objective) => objective.id === id),
        ),
        primary_subject_id: primary,
        slug: courseSlug,
        subtitle: String(formData.get('subtitle') ?? ''),
        summary: String(formData.get('summary') ?? ''),
        supporting_subject_ids: supporting.filter((id) =>
          subjects.some((subject) => subject.id === id),
        ),
        title,
      });
      router.push(`/organizaciones/${slug}/cursos/${revision.course_slug}`);
    } catch (cause) {
      const message =
        cause instanceof Error
          ? cause.message
          : 'No fue posible crear el curso.';
      setError(
        message.includes('responsabilidad académica')
          ? 'Tu responsabilidad académica cambió mientras completabas el formulario. Actualiza la página para consultar las asignaturas vigentes.'
          : message,
      );
      window.requestAnimationFrame(() => errorRef.current?.focus());
    }
  }

  return (
    <form action={submit} className="mt-6 pb-12">
      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1fr)_20rem]">
        <div className="space-y-4">
          <div aria-live="polite">
            {error ? (
              <Alert
                className="px-4 py-3"
                ref={errorRef}
                tabIndex={-1}
                variant="destructive"
              >
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            ) : null}
          </div>

          <FormSection
            description="La información que identificará el curso en el catálogo y en su espacio de autoría."
            icon={FileText}
            step="01"
            title="Identidad del curso"
          >
            <div className="grid gap-4 md:grid-cols-2">
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="course-title">Título</Label>
                <Input
                  autoFocus
                  id="course-title"
                  maxLength={200}
                  name="title"
                  onChange={(event) => {
                    const value = event.target.value;
                    setTitle(value);
                    if (!slugTouched) setCourseSlug(slugifyCourseTitle(value));
                  }}
                  placeholder="Ej. Introducción al cálculo diferencial"
                  ref={firstField}
                  required
                  value={title}
                />
              </div>
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2">
                  <Label htmlFor="course-slug">Slug</Label>
                  <span className="text-xs text-muted-foreground">
                    Se genera desde el título
                  </span>
                </div>
                <Input
                  aria-describedby="course-slug-help"
                  id="course-slug"
                  name="slug"
                  onChange={(event) => {
                    setSlugTouched(true);
                    setCourseSlug(event.target.value);
                  }}
                  pattern="[a-z0-9-]+"
                  placeholder="calculo-diferencial"
                  required
                  value={courseSlug}
                />
                <p
                  className="text-xs leading-5 text-muted-foreground"
                  id="course-slug-help"
                >
                  Identificador estable para la URL; usa letras minúsculas,
                  números y guiones.
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="course-duration">
                  Duración estimada
                  <span className="font-normal text-muted-foreground">
                    Opcional
                  </span>
                </Label>
                <div className="relative">
                  <Clock3 className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    className="pr-16 pl-9"
                    id="course-duration"
                    min={1}
                    name="duration"
                    onChange={(event) => setDuration(event.target.value)}
                    placeholder="120"
                    type="number"
                    value={duration}
                  />
                  <span className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-xs text-muted-foreground">
                    minutos
                  </span>
                </div>
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="course-subtitle">
                  Subtítulo
                  <span className="font-normal text-muted-foreground">
                    Opcional
                  </span>
                </Label>
                <Input
                  id="course-subtitle"
                  maxLength={240}
                  name="subtitle"
                  placeholder="Una frase breve que amplíe el título"
                />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="course-summary">Resumen</Label>
                <Textarea
                  id="course-summary"
                  maxLength={1200}
                  name="summary"
                  placeholder="Explica con claridad qué aprenderá la persona y cuál es el alcance del curso."
                  required
                  rows={3}
                />
              </div>
              <div className="space-y-2 md:col-span-2">
                <Label htmlFor="course-description">
                  Descripción ampliada
                  <span className="font-normal text-muted-foreground">
                    Opcional
                  </span>
                </Label>
                <Textarea
                  id="course-description"
                  maxLength={5000}
                  name="description"
                  placeholder="Añade contexto pedagógico, audiencia o criterios de alcance cuando sea necesario."
                  rows={4}
                />
              </div>
            </div>
          </FormSection>

          <FormSection
            description="Elige la asignatura central y agrega complementarias solo cuando aporten al alcance del curso."
            icon={GraduationCap}
            step="02"
            title="Alineación curricular"
          >
            <div className="mb-4 flex gap-3 rounded-lg border bg-primary/[0.035] p-3 text-sm leading-5">
              <ShieldCheck className="mt-0.5 size-4 shrink-0 text-primary" />
              <p>
                Solo aparecen asignaturas cubiertas por tu responsabilidad
                académica vigente. El servidor vuelve a comprobarla al crear el
                curso.
              </p>
            </div>
            <div className="grid gap-2">
              {subjects.map((subject) => {
                const isPrimary = primary === subject.id;
                const isSupporting = supporting.includes(subject.id);
                return (
                  <div
                    className={cn(
                      'rounded-xl border bg-background p-4 transition-[border-color,box-shadow,background-color]',
                      isPrimary &&
                        'border-primary/40 bg-primary/[0.025] shadow-sm',
                    )}
                    key={subject.id}
                  >
                    <div className="flex items-start gap-3">
                      <div
                        className={cn(
                          'grid size-9 shrink-0 place-items-center rounded-lg border bg-muted/30 text-muted-foreground',
                          isPrimary && 'border-primary/20 text-primary',
                        )}
                      >
                        <BookOpenCheck className="size-4" />
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <p className="font-semibold">{subject.name}</p>
                          {isPrimary ? (
                            <Badge variant="secondary">Principal</Badge>
                          ) : null}
                        </div>
                        <div className="mt-3 flex flex-wrap gap-2">
                          <label
                            className={cn(
                              'flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium transition-colors hover:bg-muted/50',
                              isPrimary &&
                                'border-primary/30 bg-primary/5 text-primary',
                            )}
                          >
                            <input
                              aria-label={`Principal: ${subject.name}`}
                              checked={isPrimary}
                              className="size-4 accent-primary"
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
                          <label
                            className={cn(
                              'flex items-center gap-2 rounded-md border px-3 py-2 text-sm transition-colors',
                              isPrimary
                                ? 'cursor-not-allowed opacity-50'
                                : 'cursor-pointer hover:bg-muted/50',
                              isSupporting &&
                                'border-primary/30 bg-primary/5 text-primary',
                            )}
                          >
                            <input
                              aria-label={`Complementaria: ${subject.name}`}
                              checked={isSupporting}
                              className="size-4 accent-primary"
                              disabled={isPrimary}
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
                    </div>
                  </div>
                );
              })}
            </div>
          </FormSection>

          <FormSection
            description="Vincula resultados esperados que ya pertenecen a las asignaturas seleccionadas."
            icon={Target}
            step="03"
            title="Objetivos de aprendizaje"
          >
            <div className="mb-3 flex items-center justify-between gap-3 text-xs text-muted-foreground">
              <span>{availableObjectives.length} disponibles</span>
              <span>{selectedObjectives.length} seleccionados</span>
            </div>
            {availableObjectives.length ? (
              <ul className="grid gap-2">
                {availableObjectives.map((objective) => {
                  const selected = selectedObjectives.includes(objective.id);
                  return (
                    <li key={objective.id}>
                      <label
                        className={cn(
                          'flex cursor-pointer gap-3 rounded-lg border bg-background p-3.5 transition-[border-color,background-color,box-shadow] hover:border-primary/30 hover:shadow-xs',
                          selected && 'border-primary/35 bg-primary/[0.025]',
                        )}
                      >
                        <input
                          aria-label={`${objective.code} — ${objective.statement}`}
                          checked={selected}
                          className="mt-1 size-4 shrink-0 accent-primary"
                          onChange={(event) =>
                            setSelectedObjectives((ids) =>
                              event.target.checked
                                ? [...ids, objective.id]
                                : ids.filter((id) => id !== objective.id),
                            )
                          }
                          type="checkbox"
                        />
                        <span className="min-w-0">
                          <span className="block font-mono text-xs font-semibold text-primary">
                            {objective.code}
                          </span>
                          <span className="mt-1 block text-sm leading-5">
                            {objective.statement}
                          </span>
                        </span>
                      </label>
                    </li>
                  );
                })}
              </ul>
            ) : (
              <div className="rounded-lg border border-dashed bg-muted/15 px-4 py-6 text-center">
                <Target className="mx-auto size-5 text-muted-foreground" />
                <p className="mt-2 text-sm font-medium">
                  Sin objetivos disponibles
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Cambia la alineación o continúa; podrás completar la
                  estructura en el espacio de autoría.
                </p>
              </div>
            )}
          </FormSection>
        </div>

        <aside className="xl:sticky xl:top-20">
          <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
            <div className="border-b bg-muted/20 p-5">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-[0.6875rem] font-semibold tracking-[0.1em] text-primary uppercase">
                    Resumen de creación
                  </p>
                  <h2 className="mt-2 text-lg font-semibold tracking-tight">
                    {title.trim() || 'Nuevo curso'}
                  </h2>
                </div>
                <Badge variant="secondary">Borrador</Badge>
              </div>
            </div>
            <dl className="divide-y px-5 text-sm">
              <SummaryRow
                icon={GraduationCap}
                label="Asignatura principal"
                value={primarySubject?.name ?? 'Por seleccionar'}
              />
              <SummaryRow
                icon={Layers3}
                label="Complementarias"
                value={String(supporting.length)}
              />
              <SummaryRow
                icon={Target}
                label="Objetivos"
                value={String(selectedObjectives.length)}
              />
              <SummaryRow
                icon={Clock3}
                label="Duración"
                value={duration ? `${duration} min` : 'Sin estimar'}
              />
            </dl>
            <div className="space-y-3 border-t p-5">
              <div className="flex gap-2 text-xs leading-5 text-muted-foreground">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-primary" />
                <p>
                  Se creará la revisión inicial en borrador. La estructura se
                  construye en el siguiente espacio.
                </p>
              </div>
              <Button
                className="w-full"
                disabled={mutation.isPending || !primary}
                size="lg"
                type="submit"
              >
                {mutation.isPending ? 'Creando…' : 'Crear curso'}
              </Button>
              <Button asChild className="w-full" variant="ghost">
                <Link href={`/organizaciones/${slug}/cursos`}>
                  <ArrowLeft data-icon="inline-start" />
                  Cancelar y volver
                </Link>
              </Button>
            </div>
          </div>
        </aside>
      </div>
    </form>
  );
}

function FormSection({
  children,
  description,
  icon: Icon,
  step,
  title,
}: Readonly<{
  children: React.ReactNode;
  description: string;
  icon: typeof FileText;
  step: string;
  title: string;
}>) {
  return (
    <fieldset className="overflow-hidden rounded-xl border bg-card shadow-sm">
      <legend className="sr-only">
        {step}. {title}
      </legend>
      <div className="flex gap-3 border-b bg-muted/15 px-5 py-4 sm:px-6">
        <div className="grid size-10 shrink-0 place-items-center rounded-lg border bg-background text-primary shadow-xs">
          <Icon className="size-4" />
        </div>
        <div>
          <p className="text-[0.6875rem] font-semibold tracking-[0.1em] text-primary uppercase">
            Paso {step}
          </p>
          <h2 className="mt-0.5 font-semibold">{title}</h2>
          <p className="mt-1 text-sm leading-5 text-muted-foreground">
            {description}
          </p>
        </div>
      </div>
      <div className="p-5 sm:p-6">{children}</div>
    </fieldset>
  );
}

function SummaryRow({
  icon: Icon,
  label,
  value,
}: Readonly<{ icon: typeof Clock3; label: string; value: string }>) {
  return (
    <div className="flex items-center gap-3 py-3.5">
      <Icon className="size-4 shrink-0 text-muted-foreground" />
      <dt className="min-w-0 flex-1 text-muted-foreground">{label}</dt>
      <dd className="max-w-36 truncate font-medium" title={value}>
        {value}
      </dd>
    </div>
  );
}
