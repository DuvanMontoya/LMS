'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  MembershipSearchPicker,
  type MembershipOption,
} from '@/components/learning/membership-search-picker';
import {
  useCreateCohort,
  useCreateEnrollment,
  useEnrollCohort,
} from '@/lib/learning/hooks';
import type {
  LearningAcademicGroupOption,
  LearningAcademicPeriodOption,
  LearningCourseOption,
} from '@/lib/learning/server';

const optionalDate = z.string();

const cohortSchema = z
  .object({
    access_ends_at: optionalDate,
    access_starts_at: optionalDate,
    academic_group_id: z.string().uuid().or(z.literal('')),
    academic_period_id: z.string().uuid('Selecciona un periodo académico.'),
    course_slug: z.string().trim().min(1, 'Selecciona un curso.'),
    description: z.string().trim().max(2000),
    name: z.string().trim().min(1, 'Escribe el nombre.').max(200),
    release_number: z.number().int().positive('Selecciona un release.'),
    slug: z
      .string()
      .trim()
      .regex(/^[a-z0-9]+(?:-[a-z0-9]+)*$/, 'Usa minúsculas y guiones.')
      .or(z.literal('')),
  })
  .refine(
    ({ access_ends_at, access_starts_at }) =>
      !access_ends_at ||
      !access_starts_at ||
      new Date(access_ends_at) > new Date(access_starts_at),
    {
      message: 'La fecha final debe ser posterior al inicio.',
      path: ['access_ends_at'],
    },
  );

type CohortValues = z.infer<typeof cohortSchema>;

export function CohortCreateForm({
  academicGroups,
  academicPeriods,
  courses,
  slug,
}: Readonly<{
  academicGroups: LearningAcademicGroupOption[];
  academicPeriods: LearningAcademicPeriodOption[];
  courses: LearningCourseOption[];
  slug: string;
}>) {
  const router = useRouter();
  const mutation = useCreateCohort(slug);
  const [staff, setStaff] = useState<
    Record<
      string,
      MembershipOption & {
        role: 'lead_instructor' | 'instructor' | 'assistant';
      }
    >
  >({});
  const initialCourse = courses[0];
  const form = useForm<CohortValues>({
    resolver: zodResolver(cohortSchema),
    defaultValues: {
      access_ends_at: '',
      access_starts_at: '',
      academic_group_id: '',
      academic_period_id: academicPeriods[0]?.id ?? '',
      course_slug: initialCourse?.slug ?? '',
      description: '',
      name: '',
      release_number: initialCourse?.releases[0]?.number ?? 0,
      slug: '',
    },
  });
  const selectedCourseSlug = useWatch({
    control: form.control,
    name: 'course_slug',
  });
  const selectedCourse = courses.find(
    (course) => course.slug === selectedCourseSlug,
  );
  const courseField = form.register('course_slug');

  async function submit(values: CohortValues) {
    const parsed = cohortSchema.parse(values);
    const created = await mutation.mutateAsync({
      access_ends_at: parsed.access_ends_at
        ? new Date(parsed.access_ends_at).toISOString()
        : null,
      access_starts_at: parsed.access_starts_at
        ? new Date(parsed.access_starts_at).toISOString()
        : null,
      academic_group_id: parsed.academic_group_id || null,
      academic_period_id: parsed.academic_period_id,
      course_slug: parsed.course_slug,
      description: parsed.description,
      name: parsed.name,
      release_number: parsed.release_number,
      roster_mode: parsed.academic_group_id ? 'synced' : 'manual',
      staff: Object.values(staff).map(({ id, role }) => ({
        membership_id: id,
        role,
      })),
      ...(parsed.slug ? { slug: parsed.slug } : {}),
    });
    router.push(
      parsed.academic_group_id
        ? `/organizaciones/${slug}/aprendizaje/cohortes/${created.id}`
        : `/organizaciones/${slug}/aprendizaje/cohortes`,
    );
    router.refresh();
  }

  return (
    <form
      className="academic-panel mt-6 grid max-w-4xl gap-x-5 gap-y-3 p-5 sm:grid-cols-2 sm:p-6"
      noValidate
      onSubmit={form.handleSubmit(submit)}
    >
      <Field
        error={form.formState.errors.academic_period_id?.message}
        hint="Obligatorio. Define el calendario institucional que gobierna el grupo."
        label="Periodo académico"
        name="cohort-academic-period"
      >
        <select
          className="academic-control"
          id="cohort-academic-period"
          {...form.register('academic_period_id')}
        >
          {!academicPeriods.length ? (
            <option value="">No hay periodos académicos activos</option>
          ) : null}
          {academicPeriods.map((period) => (
            <option key={period.id} value={period.id}>
              {period.name} · {period.startsOn} a {period.endsOn}
            </option>
          ))}
        </select>
      </Field>
      <Field
        error={form.formState.errors.name?.message}
        label="Nombre"
        name="cohort-name"
      >
        <Input id="cohort-name" {...form.register('name')} />
      </Field>
      <fieldset className="space-y-2 sm:col-span-2">
        <legend className="text-sm font-medium">Equipo docente</legend>
        <p className="text-xs leading-5 text-muted-foreground">
          Asigna las personas que podrán gestionar este grupo de curso. Los
          roles institucionales permanecen en la membresía.
        </p>
        <MembershipSearchPicker
          ariaLabel="Buscar persona para el equipo docente"
          excludeIds={Object.keys(staff)}
          onSelect={(member) =>
            setStaff((current) => ({
              ...current,
              [member.id]: { ...member, role: 'instructor' },
            }))
          }
          slug={slug}
        />
        {Object.values(staff).length ? (
          <div className="mt-2 grid gap-2 rounded-md border p-2 sm:grid-cols-2">
            {Object.values(staff).map((member) => (
              <div
                className="grid gap-2 rounded-md p-2 sm:grid-cols-[minmax(0,1fr)_10rem_auto] sm:items-center"
                key={member.id}
              >
                <span className="truncate text-sm">{member.email}</span>
                <select
                  aria-label={`Rol de ${member.email}`}
                  className="academic-control"
                  onChange={(event) =>
                    setStaff((current) => ({
                      ...current,
                      [member.id]: {
                        ...member,
                        role: event.target.value as
                          'lead_instructor' | 'instructor' | 'assistant',
                      },
                    }))
                  }
                  value={member.role}
                >
                  <option value="lead_instructor">Docente principal</option>
                  <option value="instructor">Docente</option>
                  <option value="assistant">Asistente</option>
                </select>
                <Button
                  onClick={() =>
                    setStaff((current) => {
                      const next = { ...current };
                      delete next[member.id];
                      return next;
                    })
                  }
                  size="sm"
                  type="button"
                  variant="ghost"
                >
                  Quitar
                </Button>
              </div>
            ))}
          </div>
        ) : null}
      </fieldset>
      <Field
        error={form.formState.errors.slug?.message}
        hint="Si lo dejas vacío, se genera a partir del nombre."
        label="Slug (opcional)"
        name="cohort-slug"
      >
        <Input id="cohort-slug" {...form.register('slug')} />
      </Field>
      <Field
        error={form.formState.errors.course_slug?.message}
        hint="Sólo aparecen cursos que ya tienen un release."
        label="Curso"
        name="cohort-course"
      >
        <select
          className="academic-control"
          id="cohort-course"
          {...courseField}
          onChange={(event) => {
            void courseField.onChange(event);
            const course = courses.find(
              (option) => option.slug === event.target.value,
            );
            form.setValue('release_number', course?.releases[0]?.number ?? 0, {
              shouldValidate: true,
            });
          }}
        >
          {!courses.length ? (
            <option value="">No hay cursos publicados</option>
          ) : null}
          {courses.map((course) => (
            <option key={course.slug} value={course.slug}>
              {course.title}
            </option>
          ))}
        </select>
      </Field>
      <Field
        error={form.formState.errors.release_number?.message}
        hint="La cohorte permanecerá fijada a esta versión."
        label="Release asignado"
        name="cohort-release"
      >
        <select
          className="academic-control"
          disabled={!selectedCourse?.releases.length}
          id="cohort-release"
          {...form.register('release_number', { valueAsNumber: true })}
        >
          {selectedCourse?.releases.map((release) => (
            <option key={release.number} value={release.number}>
              Release {release.number}
              {release.current ? ' · actual' : ''} · {release.unitCount}{' '}
              unidades
            </option>
          ))}
        </select>
      </Field>
      <Field
        error={form.formState.errors.academic_group_id?.message}
        hint="Opcional. Organiza la cohorte institucionalmente; no matricula integrantes por sí solo."
        label="Grupo académico"
        name="cohort-academic-group"
      >
        <select
          className="academic-control"
          id="cohort-academic-group"
          {...form.register('academic_group_id')}
        >
          <option value="">Sin grupo académico</option>
          {academicGroups.map((group) => (
            <option key={group.id} value={group.id}>
              {group.name} · {group.academicYear}
              {group.section ? ` · ${group.section}` : ''}
            </option>
          ))}
        </select>
      </Field>
      <Field
        error={form.formState.errors.access_starts_at?.message}
        hint="Opcional. Sin fecha, el acceso puede comenzar de inmediato."
        label="Inicio de acceso"
        name="cohort-start"
      >
        <Input
          id="cohort-start"
          type="datetime-local"
          {...form.register('access_starts_at')}
        />
      </Field>
      <Field
        error={form.formState.errors.access_ends_at?.message}
        hint="Opcional. Sin fecha, el acceso no vence automáticamente."
        label="Fin de acceso"
        name="cohort-end"
      >
        <Input
          id="cohort-end"
          type="datetime-local"
          {...form.register('access_ends_at')}
        />
      </Field>
      <div className="space-y-2 sm:col-span-2">
        <Label htmlFor="cohort-description">Descripción</Label>
        <Textarea id="cohort-description" {...form.register('description')} />
        <p className="text-xs leading-5 text-muted-foreground">
          Contexto interno para reconocer el grupo y su propósito.
        </p>
      </div>
      <SubmitState
        disabled={!courses.length || !academicPeriods.length}
        error={mutation.error}
        label="Crear cohorte"
        pending={mutation.isPending}
      />
    </form>
  );
}

const enrollmentSchema = z.object({
  access_ends_at: optionalDate,
  access_starts_at: optionalDate,
  course_slug: z.string().trim().min(1, 'Selecciona un curso.'),
  membership_id: z.string().uuid('Selecciona un estudiante.'),
  release_number: z.string().regex(/^\d+$/, 'Selecciona un release.'),
});

type EnrollmentValues = z.infer<typeof enrollmentSchema>;

export function EnrollmentCreateForm({
  courses,
  slug,
}: Readonly<{
  courses: LearningCourseOption[];
  slug: string;
}>) {
  const router = useRouter();
  const mutation = useCreateEnrollment(slug);
  const [student, setStudent] = useState<MembershipOption | null>(null);
  const form = useForm<EnrollmentValues>({
    resolver: zodResolver(enrollmentSchema),
    defaultValues: {
      access_ends_at: '',
      access_starts_at: '',
      course_slug: '',
      membership_id: '',
      release_number: '',
    },
  });
  const selectedCourseSlug = useWatch({
    control: form.control,
    name: 'course_slug',
  });
  const selectedCourse = courses.find(
    (course) => course.slug === selectedCourseSlug,
  );
  const courseField = form.register('course_slug');

  async function submit(values: EnrollmentValues) {
    const parsed = enrollmentSchema.parse(values);
    await mutation.mutateAsync({
      access_ends_at: parsed.access_ends_at
        ? new Date(parsed.access_ends_at).toISOString()
        : null,
      access_starts_at: parsed.access_starts_at
        ? new Date(parsed.access_starts_at).toISOString()
        : null,
      course_slug: parsed.course_slug,
      membership_id: parsed.membership_id,
      release_number: Number(parsed.release_number),
    });
    setStudent(null);
    form.reset();
    router.refresh();
  }

  return (
    <form
      className="grid gap-x-5 gap-y-3 sm:grid-cols-2"
      noValidate
      onSubmit={form.handleSubmit(submit)}
    >
      <Field
        error={form.formState.errors.membership_id?.message}
        hint="Selecciona una membresía activa de la institución."
        label="Estudiante"
        name="enrollment-member"
      >
        <>
          <input type="hidden" {...form.register('membership_id')} />
          <MembershipSearchPicker
            ariaLabel="Buscar estudiante para matrícula individual"
            excludeIds={student ? [student.id] : []}
            onSelect={(member) => {
              setStudent(member);
              form.setValue('membership_id', member.id, {
                shouldValidate: true,
              });
            }}
            slug={slug}
          />
          {student ? (
            <div className="mt-2 flex items-center justify-between gap-2 rounded-md border px-3 py-2 text-sm">
              <span className="truncate">{student.email}</span>
              <Button
                onClick={() => {
                  setStudent(null);
                  form.setValue('membership_id', '', { shouldValidate: true });
                }}
                size="sm"
                type="button"
                variant="ghost"
              >
                Quitar
              </Button>
            </div>
          ) : null}
        </>
      </Field>
      <Field
        error={form.formState.errors.course_slug?.message}
        hint="Sólo aparecen cursos con releases disponibles."
        label="Curso"
        name="enrollment-course"
      >
        <select
          className="academic-control"
          id="enrollment-course"
          {...courseField}
          onChange={(event) => {
            void courseField.onChange(event);
            const course = courses.find(
              (option) => option.slug === event.target.value,
            );
            form.setValue(
              'release_number',
              course?.releases[0]?.number
                ? String(course.releases[0].number)
                : '',
              { shouldValidate: true },
            );
          }}
        >
          <option value="">Selecciona un curso</option>
          {courses.map((course) => (
            <option key={course.slug} value={course.slug}>
              {course.title}
            </option>
          ))}
        </select>
      </Field>
      <Field
        error={form.formState.errors.release_number?.message}
        hint="Cambiarlo después requiere un upgrade explícito."
        label="Release asignado"
        name="enrollment-release"
      >
        <select
          className="academic-control"
          disabled={!selectedCourse}
          id="enrollment-release"
          {...form.register('release_number')}
        >
          <option value="">Selecciona un release</option>
          {selectedCourse?.releases.map((release) => (
            <option key={release.number} value={release.number}>
              Release {release.number}
              {release.current ? ' · actual' : ''} · {release.unitCount}{' '}
              unidades
            </option>
          ))}
        </select>
      </Field>
      <Field
        error={form.formState.errors.access_starts_at?.message}
        hint="Opcional; puede restringir esta matrícula individualmente."
        label="Inicio de acceso"
        name="enrollment-start"
      >
        <Input
          id="enrollment-start"
          type="datetime-local"
          {...form.register('access_starts_at')}
        />
      </Field>
      <Field
        error={form.formState.errors.access_ends_at?.message}
        hint="Opcional; sin fecha no vence automáticamente."
        label="Fin de acceso"
        name="enrollment-end"
      >
        <Input
          id="enrollment-end"
          type="datetime-local"
          {...form.register('access_ends_at')}
        />
      </Field>
      <SubmitState
        disabled={!student || !courses.length}
        error={mutation.error}
        label="Crear matrícula"
        pending={mutation.isPending}
      />
    </form>
  );
}

const batchSchema = z.object({
  membership_ids: z
    .array(z.string().uuid())
    .min(1, 'Selecciona al menos un estudiante.'),
});

export function CohortBatchEnrollForm({
  cohortId,
  cohortVersion,
  enrolledEmails,
  slug,
}: Readonly<{
  cohortId: string;
  cohortVersion: number;
  enrolledEmails: readonly string[];
  slug: string;
}>) {
  const router = useRouter();
  const mutation = useEnrollCohort(slug, cohortId);
  const [students, setStudents] = useState<Record<string, MembershipOption>>(
    {},
  );
  const form = useForm<z.infer<typeof batchSchema>>({
    resolver: zodResolver(batchSchema),
    defaultValues: { membership_ids: [] },
  });

  async function submit({ membership_ids }: z.infer<typeof batchSchema>) {
    await mutation.mutateAsync({
      membershipIds: membership_ids,
      version: cohortVersion,
    });
    form.reset();
    router.refresh();
  }

  return (
    <form
      className="academic-panel mt-6 grid gap-4 p-5 sm:p-6"
      noValidate
      onSubmit={form.handleSubmit(submit)}
    >
      <fieldset>
        <legend className="text-sm font-semibold">Añadir estudiantes</legend>
        <p className="mt-1 text-sm leading-6 text-muted-foreground">
          Selecciona una o varias membresías activas. El lote se guarda de forma
          atómica.
        </p>
        <MembershipSearchPicker
          ariaLabel="Buscar estudiante para el grupo de curso"
          excludeIds={Object.keys(students)}
          onSelect={(member) => {
            if (enrolledEmails.includes(member.email)) {
              form.setError('membership_ids', {
                message:
                  'Esta persona ya tiene una matrícula activa en el grupo.',
              });
              return;
            }
            setStudents((current) => {
              const next = { ...current, [member.id]: member };
              form.setValue('membership_ids', Object.keys(next), {
                shouldValidate: true,
              });
              return next;
            });
          }}
          slug={slug}
        />
        {Object.values(students).length ? (
          <div className="mt-3 grid gap-2 rounded-md border p-2 sm:grid-cols-2">
            {Object.values(students).map((member) => (
              <div
                className="flex items-center justify-between gap-2 rounded-md px-2 py-1 text-sm"
                key={member.id}
              >
                <span className="truncate">{member.email}</span>
                <Button
                  onClick={() =>
                    setStudents((current) => {
                      const next = { ...current };
                      delete next[member.id];
                      form.setValue('membership_ids', Object.keys(next), {
                        shouldValidate: true,
                      });
                      return next;
                    })
                  }
                  size="sm"
                  type="button"
                  variant="ghost"
                >
                  Quitar
                </Button>
              </div>
            ))}
          </div>
        ) : null}
      </fieldset>
      <p aria-live="polite" className="text-sm text-destructive">
        {form.formState.errors.membership_ids?.message}
      </p>
      <SubmitState
        disabled={!Object.keys(students).length}
        error={mutation.error}
        label="Matricular selección"
        pending={mutation.isPending}
      />
    </form>
  );
}

function Field({
  children,
  error,
  hint,
  label,
  name,
}: Readonly<{
  children: React.ReactNode;
  error: string | undefined;
  hint?: string;
  label: string;
  name: string;
}>) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={name}>{label}</Label>
      {children}
      <p
        aria-live={error ? 'polite' : undefined}
        className={
          error
            ? 'min-h-5 text-sm text-destructive'
            : 'min-h-5 text-xs leading-5 text-muted-foreground'
        }
      >
        {error ?? hint}
      </p>
    </div>
  );
}

function SubmitState({
  disabled = false,
  error,
  label,
  pending,
}: Readonly<{
  disabled?: boolean;
  error: Error | null;
  label: string;
  pending: boolean;
}>) {
  return (
    <div className="flex flex-wrap items-center gap-4 sm:col-span-2">
      <Button disabled={disabled || pending} type="submit">
        {pending ? 'Guardando…' : label}
      </Button>
      <p aria-live="polite" className="text-sm text-destructive">
        {error?.message}
      </p>
    </div>
  );
}
