'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useRouter } from 'next/navigation';
import { useForm, useWatch } from 'react-hook-form';
import { z } from 'zod';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import {
  useCreateCohort,
  useCreateEnrollment,
  useEnrollCohort,
} from '@/lib/learning/hooks';
import type {
  LearningAcademicGroupOption,
  LearningCohortOption,
  LearningCourseOption,
  LearningMemberOption,
} from '@/lib/learning/server';
import { roleLabel, sortRoles } from '@/lib/organizations/labels';

const optionalDate = z.string();

const cohortSchema = z
  .object({
    access_ends_at: optionalDate,
    access_starts_at: optionalDate,
    academic_group_id: z.string().uuid().or(z.literal('')),
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
  courses,
  slug,
}: Readonly<{
  academicGroups: LearningAcademicGroupOption[];
  courses: LearningCourseOption[];
  slug: string;
}>) {
  const router = useRouter();
  const mutation = useCreateCohort(slug);
  const initialCourse = courses[0];
  const form = useForm<CohortValues>({
    resolver: zodResolver(cohortSchema),
    defaultValues: {
      access_ends_at: '',
      access_starts_at: '',
      academic_group_id: '',
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
    await mutation.mutateAsync({
      access_ends_at: parsed.access_ends_at
        ? new Date(parsed.access_ends_at).toISOString()
        : null,
      access_starts_at: parsed.access_starts_at
        ? new Date(parsed.access_starts_at).toISOString()
        : null,
      academic_group_id: parsed.academic_group_id || null,
      course_slug: parsed.course_slug,
      description: parsed.description,
      name: parsed.name,
      release_number: parsed.release_number,
      ...(parsed.slug ? { slug: parsed.slug } : {}),
    });
    router.push(`/organizaciones/${slug}/aprendizaje/cohortes`);
    router.refresh();
  }

  return (
    <form
      className="academic-panel mt-6 grid max-w-4xl gap-x-5 gap-y-3 p-5 sm:grid-cols-2 sm:p-6"
      noValidate
      onSubmit={form.handleSubmit(submit)}
    >
      <Field
        error={form.formState.errors.name?.message}
        label="Nombre"
        name="cohort-name"
      >
        <Input id="cohort-name" {...form.register('name')} />
      </Field>
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
        disabled={!courses.length}
        error={mutation.error}
        label="Crear cohorte"
        pending={mutation.isPending}
      />
    </form>
  );
}

const enrollmentSchema = z
  .object({
    access_ends_at: optionalDate,
    access_starts_at: optionalDate,
    cohort_id: z.string().uuid().or(z.literal('')),
    course_slug: z.string().trim().min(1, 'Selecciona un curso.'),
    membership_id: z.string().uuid('Selecciona un estudiante.'),
    release_number: z
      .string()
      .regex(/^\d+$/, 'Selecciona un release.')
      .or(z.literal('')),
  })
  .superRefine(({ cohort_id, release_number }, context) => {
    if (!cohort_id && !release_number) {
      context.addIssue({
        code: 'custom',
        message: 'Selecciona un release.',
        path: ['release_number'],
      });
    }
  });

type EnrollmentValues = z.infer<typeof enrollmentSchema>;

export function EnrollmentCreateForm({
  cohorts,
  courses,
  members,
  slug,
}: Readonly<{
  cohorts: LearningCohortOption[];
  courses: LearningCourseOption[];
  members: LearningMemberOption[];
  slug: string;
}>) {
  const router = useRouter();
  const mutation = useCreateEnrollment(slug);
  const form = useForm<EnrollmentValues>({
    resolver: zodResolver(enrollmentSchema),
    defaultValues: {
      access_ends_at: '',
      access_starts_at: '',
      cohort_id: '',
      course_slug: '',
      membership_id: '',
      release_number: '',
    },
  });
  const selectedCohortId = useWatch({
    control: form.control,
    name: 'cohort_id',
  });
  const selectedCourseSlug = useWatch({
    control: form.control,
    name: 'course_slug',
  });
  const selectedCohort = cohorts.find(
    (cohort) => cohort.id === selectedCohortId,
  );
  const selectedCourse = courses.find(
    (course) => course.slug === selectedCourseSlug,
  );
  const cohortField = form.register('cohort_id');
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
      cohort_id: parsed.cohort_id || null,
      course_slug: parsed.course_slug,
      membership_id: parsed.membership_id,
      ...(parsed.release_number
        ? { release_number: Number(parsed.release_number) }
        : {}),
    });
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
        <select
          className="academic-control"
          id="enrollment-member"
          {...form.register('membership_id')}
        >
          <option value="">Selecciona un estudiante</option>
          {members.map((member) => (
            <option key={member.id} value={member.id}>
              {member.email} ·{' '}
              {sortRoles(member.roles).map(roleLabel).join(', ')}
            </option>
          ))}
        </select>
      </Field>
      <Field
        error={form.formState.errors.cohort_id?.message}
        hint="Usa una cohorte o conserva la matrícula como individual."
        label="Modalidad"
        name="enrollment-cohort"
      >
        <select
          className="academic-control"
          id="enrollment-cohort"
          {...cohortField}
          onChange={(event) => {
            void cohortField.onChange(event);
            const cohort = cohorts.find(
              (option) => option.id === event.target.value,
            );
            form.setValue('course_slug', cohort?.courseSlug ?? '', {
              shouldValidate: Boolean(cohort),
            });
            form.setValue('release_number', '');
          }}
        >
          <option value="">Matrícula individual</option>
          {cohorts.map((cohort) => (
            <option key={cohort.id} value={cohort.id}>
              Cohorte · {cohort.name}
            </option>
          ))}
        </select>
      </Field>
      {selectedCohort ? (
        <div className="rounded-md border bg-muted/20 p-4 sm:col-span-2">
          <p className="text-sm font-medium">{selectedCohort.name}</p>
          <p className="mt-1 text-sm leading-6 text-muted-foreground">
            {selectedCohort.courseTitle} · release{' '}
            {selectedCohort.releaseNumber}. La cohorte define el curso y el
            release.
          </p>
        </div>
      ) : (
        <>
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
        </>
      )}
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
        disabled={!members.length || (!cohorts.length && !courses.length)}
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
  enrolledEmails,
  members,
  slug,
}: Readonly<{
  cohortId: string;
  enrolledEmails: readonly string[];
  members: LearningMemberOption[];
  slug: string;
}>) {
  const router = useRouter();
  const mutation = useEnrollCohort(slug, cohortId);
  const availableMembers = members.filter(
    (member) => !enrolledEmails.includes(member.email),
  );
  const form = useForm<z.infer<typeof batchSchema>>({
    resolver: zodResolver(batchSchema),
    defaultValues: { membership_ids: [] },
  });

  async function submit({ membership_ids }: z.infer<typeof batchSchema>) {
    await mutation.mutateAsync(membership_ids);
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
        {availableMembers.length ? (
          <div className="mt-4 grid max-h-72 gap-2 overflow-y-auto rounded-md border p-2 sm:grid-cols-2">
            {availableMembers.map((member) => (
              <label
                className="flex min-w-0 cursor-pointer items-start gap-3 rounded-md p-3 transition-colors hover:bg-muted/40"
                key={member.id}
              >
                <input
                  className="mt-1 size-4 shrink-0 accent-primary"
                  type="checkbox"
                  value={member.id}
                  {...form.register('membership_ids')}
                />
                <span className="min-w-0">
                  <span className="block truncate text-sm font-medium">
                    {member.email}
                  </span>
                  <span className="block text-xs text-muted-foreground">
                    {sortRoles(member.roles).map(roleLabel).join(', ')}
                  </span>
                </span>
              </label>
            ))}
          </div>
        ) : (
          <p className="mt-4 rounded-md border border-dashed p-4 text-sm text-muted-foreground">
            No hay membresías activas pendientes de matrícula en esta cohorte.
          </p>
        )}
      </fieldset>
      <p aria-live="polite" className="text-sm text-destructive">
        {form.formState.errors.membership_ids?.message}
      </p>
      <SubmitState
        disabled={!availableMembers.length}
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
