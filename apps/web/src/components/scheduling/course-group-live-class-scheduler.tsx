'use client';

import { CalendarPlus, CheckCircle2, LoaderCircle } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

type Slot = { starts_at: string; weekday: number };

const weekdayOptions = [
  ['0', 'Lunes'],
  ['1', 'Martes'],
  ['2', 'Miércoles'],
  ['3', 'Jueves'],
  ['4', 'Viernes'],
  ['5', 'Sábado'],
  ['6', 'Domingo'],
] as const;

const defaultSlots: Slot[] = [
  { weekday: 0, starts_at: '08:00' },
  { weekday: 0, starts_at: '10:00' },
  { weekday: 2, starts_at: '08:00' },
  { weekday: 2, starts_at: '10:00' },
];

function nextMonday(value = new Date()) {
  const date = new Date(value);
  const daysUntilMonday = (8 - date.getDay()) % 7 || 7;
  date.setDate(date.getDate() + daysUntilMonday);
  return date.toISOString().slice(0, 10);
}

export function CourseGroupLiveClassScheduler({
  cohortId,
  slug,
}: Readonly<{ cohortId: string; slug: string }>) {
  const router = useRouter();
  const [firstWeekStartsOn, setFirstWeekStartsOn] = useState(nextMonday);
  const [slots, setSlots] = useState<Slot[]>(defaultSlots);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isPending, setIsPending] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setMessage(null);
    setIsPending(true);
    try {
      const {
        data,
        error: responseError,
        response,
      } = await platformBrowserClient.POST(
        '/api/v1/organizations/{slug}/scheduling/course-groups/{course_group_id}/live-classes/materialize/',
        {
          body: {
            first_week_starts_on: firstWeekStartsOn,
            slots,
            timezone_name: 'America/Bogota',
          },
          params: { path: { course_group_id: cohortId, slug } },
        },
      );
      if (!response.ok || !data) {
        const payload =
          responseError && typeof responseError === 'object'
            ? (responseError as Record<string, unknown>)
            : {};
        throw new Error(
          typeof payload.detail === 'string'
            ? payload.detail
            : 'No fue posible programar las clases en vivo.',
        );
      }
      setMessage(
        data.created_count
          ? `${data.created_count} clases quedaron programadas para esta sección.`
          : `Las ${data.already_scheduled_count} clases ya estaban programadas.`,
      );
      router.refresh();
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : 'No fue posible programar las clases en vivo.',
      );
    } finally {
      setIsPending(false);
    }
  }

  function updateSlot(index: number, patch: Partial<Slot>) {
    setSlots((current) =>
      current.map((slot, slotIndex) =>
        slotIndex === index ? { ...slot, ...patch } : slot,
      ),
    );
  }

  return (
    <section
      className="academic-panel mt-6 p-5"
      aria-labelledby="programar-clases"
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="academic-kicker">Operación de la sección</p>
          <h2 className="text-xl font-semibold" id="programar-clases">
            Programar clases en vivo
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Convierte las actividades LiveKit aprobadas del release en sesiones
            reales de esta sección. Cada clase conserva su asistencia, chat,
            permisos y política de grabación.
          </p>
        </div>
        <CalendarPlus className="size-6 text-primary" />
      </div>
      <form className="mt-5 grid gap-4" onSubmit={submit}>
        <label className="grid gap-1 text-sm font-medium sm:max-w-xs">
          Inicio de la semana 1
          <input
            className="h-10 rounded-md border bg-background px-3"
            min={new Date().toISOString().slice(0, 10)}
            onChange={(event) => setFirstWeekStartsOn(event.target.value)}
            required
            type="date"
            value={firstWeekStartsOn}
          />
        </label>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          {slots.map((slot, index) => (
            <fieldset className="rounded-lg border p-3" key={index}>
              <legend className="px-1 text-sm font-medium">
                Bloque {index + 1}
              </legend>
              <label className="grid gap-1 text-xs text-muted-foreground">
                Día
                <select
                  className="h-9 rounded-md border bg-background px-2 text-sm text-foreground"
                  onChange={(event) =>
                    updateSlot(index, { weekday: Number(event.target.value) })
                  }
                  value={slot.weekday}
                >
                  {weekdayOptions.map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="mt-2 grid gap-1 text-xs text-muted-foreground">
                Hora
                <input
                  className="h-9 rounded-md border bg-background px-2 text-sm text-foreground"
                  onChange={(event) =>
                    updateSlot(index, { starts_at: event.target.value })
                  }
                  required
                  type="time"
                  value={slot.starts_at}
                />
              </label>
            </fieldset>
          ))}
        </div>
        {error ? (
          <Alert variant="destructive">
            <AlertTitle>No se programaron las clases</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        {message ? (
          <Alert>
            <CheckCircle2 />
            <AlertTitle>Programación lista</AlertTitle>
            <AlertDescription>{message}</AlertDescription>
          </Alert>
        ) : null}
        <div>
          <Button disabled={isPending} type="submit">
            {isPending ? (
              <LoaderCircle className="animate-spin" />
            ) : (
              <CalendarPlus />
            )}
            Programar todas las clases pendientes
          </Button>
        </div>
      </form>
    </section>
  );
}
