'use client';

import {
  BookOpenCheck,
  CalendarRange,
  LoaderCircle,
  ShieldCheck,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import {
  MembershipSearchPicker,
  type MembershipOption,
} from '@/components/learning/membership-search-picker';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

type Course = components['schemas']['CourseList'];
type CourseException = components['schemas']['CourseTeachingException'];

export function CourseTeachingExceptionsPanel({
  canManage,
  courses,
  exceptions,
  slug,
}: Readonly<{
  canManage: boolean;
  courses: Course[];
  exceptions: CourseException[];
  slug: string;
}>) {
  const router = useRouter();
  const [member, setMember] = useState<MembershipOption | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const active = exceptions.filter((item) => item.ended_at === null);

  async function closeException(id: string) {
    setPending(true);
    setError('');
    const { error: apiError, response } = await platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/courses/teaching-exceptions/{exception_id}/close/',
      {
        body: { ended_on: localDate() },
        params: { path: { exception_id: id, slug } },
      },
    );
    setPending(false);
    if (!response.ok) {
      setError(errorMessage(apiError));
      return;
    }
    router.refresh();
  }

  return (
    <section
      className="mt-10 border-t pt-8"
      aria-labelledby="course-exceptions-title"
    >
      <header className="max-w-3xl">
        <p className="text-xs font-semibold tracking-wider text-primary uppercase">
          Excepción controlada
        </p>
        <h2 className="mt-1 text-xl font-semibold" id="course-exceptions-title">
          Alcance por curso
        </h2>
        <p className="mt-2 text-sm text-muted-foreground">
          Úsalo sólo cuando la responsabilidad por asignatura no representa el
          caso. No sustituye el staff operativo de un grupo.
        </p>
      </header>
      <div
        className={
          canManage
            ? 'mt-5 grid gap-5 xl:grid-cols-[23rem_minmax(0,1fr)]'
            : 'mt-5'
        }
      >
        {canManage ? (
          <form
            className="academic-panel h-fit space-y-4 p-5"
            onSubmit={(event) => {
              event.preventDefault();
              if (!member) {
                setError('Selecciona una persona activa.');
                return;
              }
              const form = event.currentTarget;
              const values = new FormData(form);
              setPending(true);
              setError('');
              void platformBrowserClient
                .POST(
                  '/api/v1/organizations/{slug}/courses/teaching-exceptions/',
                  {
                    body: {
                      course_id: String(values.get('course_id')),
                      ends_on: String(values.get('ends_on')) || null,
                      membership_id: member.id,
                      rationale: String(values.get('rationale')),
                      starts_on: String(values.get('starts_on')),
                    },
                    params: { path: { slug } },
                  },
                )
                .then(({ error: apiError, response }) => {
                  if (!response.ok) throw new Error(errorMessage(apiError));
                  form.reset();
                  setMember(null);
                  router.refresh();
                })
                .catch((reason: unknown) =>
                  setError(
                    reason instanceof Error
                      ? reason.message
                      : 'No fue posible crear la excepción.',
                  ),
                )
                .finally(() => setPending(false));
            }}
          >
            <div className="space-y-2">
              <Label htmlFor="exception-course">Curso</Label>
              <select
                className="academic-control"
                id="exception-course"
                name="course_id"
                required
              >
                <option value="">Selecciona un curso</option>
                {courses.map((course) => (
                  <option key={course.id} value={course.id}>
                    {course.title}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Persona</Label>
              {member ? (
                <div className="flex items-center justify-between gap-2 rounded-md border p-3 text-sm">
                  <span className="truncate">{member.email}</span>
                  <Button
                    onClick={() => setMember(null)}
                    size="sm"
                    type="button"
                    variant="ghost"
                  >
                    Cambiar
                  </Button>
                </div>
              ) : (
                <MembershipSearchPicker
                  ariaLabel="Buscar persona para la excepción"
                  onSelect={setMember}
                  slug={slug}
                />
              )}
            </div>
            <DateField label="Inicio" name="starts_on" required />
            <DateField label="Fin opcional" name="ends_on" />
            <div className="space-y-2">
              <Label htmlFor="exception-rationale">
                Justificación excepcional
              </Label>
              <Textarea
                id="exception-rationale"
                maxLength={1000}
                name="rationale"
                required
              />
            </div>
            {error ? (
              <p className="text-sm text-destructive" role="alert">
                {error}
              </p>
            ) : null}
            <Button
              className="w-full"
              disabled={pending || !courses.length}
              type="submit"
            >
              {pending ? (
                <LoaderCircle className="animate-spin" />
              ) : (
                <ShieldCheck />
              )}
              Registrar excepción
            </Button>
          </form>
        ) : null}
        <div className="grid gap-4 md:grid-cols-2">
          {active.map((item) => {
            const course = courses.find(
              (candidate) => candidate.id === item.course_id,
            );
            return (
              <article className="academic-panel p-5" key={item.id}>
                <div className="flex items-start justify-between gap-3">
                  <span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                    <BookOpenCheck />
                  </span>
                  <Badge variant="secondary">Activa</Badge>
                </div>
                <h3 className="mt-4 font-semibold">
                  {course?.title ?? item.course_slug}
                </h3>
                <p className="mt-1 text-sm text-muted-foreground">
                  {item.member_email}
                </p>
                <p className="mt-3 text-sm">{item.rationale}</p>
                <p className="mt-4 flex items-center gap-2 border-t pt-4 text-sm text-muted-foreground">
                  <CalendarRange className="size-4" /> Desde{' '}
                  {formatDate(item.starts_on)}
                  {item.ends_on ? ` hasta ${formatDate(item.ends_on)}` : ''}
                </p>
                {canManage ? (
                  <Button
                    className="mt-4"
                    disabled={pending}
                    onClick={() => void closeException(item.id)}
                    size="sm"
                    variant="outline"
                  >
                    Cerrar hoy
                  </Button>
                ) : null}
              </article>
            );
          })}
          {!active.length ? (
            <div className="rounded-lg border border-dashed p-8 text-center text-sm text-muted-foreground md:col-span-2">
              No hay excepciones vigentes.
            </div>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function DateField({
  label,
  name,
  required = false,
}: Readonly<{ label: string; name: string; required?: boolean }>) {
  return (
    <div className="space-y-2">
      <Label htmlFor={`exception-${name}`}>{label}</Label>
      <Input
        defaultValue={name === 'starts_on' ? localDate() : undefined}
        id={`exception-${name}`}
        name={name}
        required={required}
        type="date"
      />
    </div>
  );
}

function localDate() {
  const now = new Date();
  return new Date(now.getTime() - now.getTimezoneOffset() * 60_000)
    .toISOString()
    .slice(0, 10);
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium' }).format(
    new Date(`${value}T12:00:00`),
  );
}

function errorMessage(value: unknown) {
  if (value && typeof value === 'object' && 'detail' in value) {
    const detail = (value as { detail?: unknown }).detail;
    if (typeof detail === 'string') return detail;
  }
  return 'No fue posible actualizar la excepción.';
}
