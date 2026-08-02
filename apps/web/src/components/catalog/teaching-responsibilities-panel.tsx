'use client';

import {
  BookMarked,
  CalendarRange,
  LoaderCircle,
  UserRoundCheck,
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

type Responsibility = components['schemas']['SubjectTeachingResponsibility'];
type Subject = components['schemas']['Subject'];

export function TeachingResponsibilitiesPanel({
  canManage,
  responsibilities,
  slug,
  subjects,
}: Readonly<{
  canManage: boolean;
  responsibilities: Responsibility[];
  slug: string;
  subjects: Subject[];
}>) {
  const router = useRouter();
  const [member, setMember] = useState<MembershipOption | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const active = responsibilities.filter((item) => item.ended_at === null);

  async function closeResponsibility(id: string) {
    setPending(true);
    setError('');
    const { error: apiError, response } = await platformBrowserClient.POST(
      '/api/v1/organizations/{slug}/catalog/teaching-responsibilities/{responsibility_id}/close/',
      {
        body: { ended_on: localDate() },
        params: { path: { responsibility_id: id, slug } },
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
    <div
      className={
        canManage
          ? 'mt-6 grid gap-5 xl:grid-cols-[23rem_minmax(0,1fr)]'
          : 'mt-6'
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
                '/api/v1/organizations/{slug}/catalog/teaching-responsibilities/',
                {
                  body: {
                    ends_on: String(values.get('ends_on')) || null,
                    membership_id: member.id,
                    rationale: String(values.get('rationale')),
                    starts_on: String(values.get('starts_on')),
                    subject_id: String(values.get('subject_id')),
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
                    : 'No fue posible asignar la responsabilidad.',
                ),
              )
              .finally(() => setPending(false));
          }}
        >
          <div>
            <p className="text-xs font-semibold tracking-wider text-primary uppercase">
              Alcance académico
            </p>
            <h2 className="mt-1 text-lg font-semibold">
              Asignar responsabilidad
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              No concede acceso automático a grupos de curso.
            </p>
          </div>
          <div className="space-y-2">
            <Label htmlFor="responsibility-subject">Asignatura</Label>
            <select
              className="academic-control"
              id="responsibility-subject"
              name="subject_id"
              required
            >
              <option value="">Selecciona una asignatura</option>
              {subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>
                  {subject.name}
                </option>
              ))}
            </select>
          </div>
          <div className="space-y-2">
            <Label>Persona responsable</Label>
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
                ariaLabel="Buscar persona responsable"
                onSelect={setMember}
                slug={slug}
              />
            )}
          </div>
          <DateField label="Inicio" name="starts_on" required />
          <DateField label="Fin opcional" name="ends_on" />
          <div className="space-y-2">
            <Label htmlFor="responsibility-rationale">Justificación</Label>
            <Textarea
              id="responsibility-rationale"
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
            disabled={pending || !subjects.length}
            type="submit"
          >
            {pending ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <UserRoundCheck />
            )}
            Asignar
          </Button>
        </form>
      ) : null}
      <section>
        {active.length ? (
          <div className="grid gap-4 md:grid-cols-2">
            {active.map((item) => (
              <article className="academic-panel p-5" key={item.id}>
                <div className="flex items-start justify-between gap-3">
                  <span className="grid size-10 place-items-center rounded-lg bg-primary/10 text-primary">
                    <BookMarked />
                  </span>
                  <Badge variant="secondary">Activa</Badge>
                </div>
                <h2 className="mt-4 text-lg font-semibold">
                  {item.subject_name}
                </h2>
                <p className="mt-2 text-sm text-muted-foreground">
                  {item.rationale}
                </p>
                <dl className="mt-5 grid gap-3 border-t pt-4 text-sm">
                  <div className="flex items-center gap-2">
                    <CalendarRange className="size-4 text-muted-foreground" />
                    <dt className="sr-only">Vigencia</dt>
                    <dd>
                      Desde {formatDate(item.starts_on)}
                      {item.ends_on ? ` hasta ${formatDate(item.ends_on)}` : ''}
                    </dd>
                  </div>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <UserRoundCheck className="size-4" />
                    <dt className="sr-only">Persona responsable</dt>
                    <dd>{item.member_email}</dd>
                  </div>
                </dl>
                {canManage ? (
                  <Button
                    className="mt-4"
                    disabled={pending}
                    onClick={() => void closeResponsibility(item.id)}
                    size="sm"
                    variant="outline"
                  >
                    Cerrar hoy
                  </Button>
                ) : null}
              </article>
            ))}
          </div>
        ) : (
          <div className="rounded-lg border border-dashed p-10 text-center">
            <BookMarked className="mx-auto size-8 text-muted-foreground" />
            <h2 className="mt-3 font-semibold">Sin asignaturas vigentes</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Un owner o administrator debe registrar la responsabilidad
              académica.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}

function DateField({
  label,
  name,
  required = false,
}: Readonly<{ label: string; name: string; required?: boolean }>) {
  return (
    <div className="space-y-2">
      <Label htmlFor={`responsibility-${name}`}>{label}</Label>
      <Input
        defaultValue={name === 'starts_on' ? localDate() : undefined}
        id={`responsibility-${name}`}
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
  return 'No fue posible actualizar la responsabilidad.';
}
