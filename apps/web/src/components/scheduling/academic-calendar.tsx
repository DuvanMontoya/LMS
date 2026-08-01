'use client';

import 'temporal-polyfill/global';

import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/react/daygrid';
import interactionPlugin from '@fullcalendar/react/interaction';
import listPlugin from '@fullcalendar/react/list';
import esLocale from '@fullcalendar/react/locales/es';
import timeGridPlugin from '@fullcalendar/react/timegrid';
import classicThemePlugin from '@fullcalendar/react/themes/classic';
import type {
  DateClickInfo,
  DatesSetInfo,
  EventClickInfo,
  EventDropInfo,
  EventResizeDoneInfo,
} from '@fullcalendar/react';
import { CalendarPlus, ExternalLink, RefreshCcw, Trash2 } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useRef, useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  cancelCalendarEvent,
  createCalendarEvent,
  getCalendarEvents,
  rescheduleCalendarEvent,
  type CalendarEvent,
} from '@/lib/scheduling/api';

type CourseOption = { slug: string; title: string };
type ParticipantOption = { membershipId: string; display: string };
type RecurrenceScope = 'occurrence' | 'following' | 'series';
type MoveInfo = EventDropInfo | EventResizeDoneInfo;

export function AcademicCalendar({
  canCreate,
  courses,
  participantOptions,
  slug,
}: Readonly<{
  canCreate: boolean;
  courses: CourseOption[];
  participantOptions: ParticipantOption[];
  slug: string;
}>) {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selected, setSelected] = useState<CalendarEvent | null>(null);
  const [createStart, setCreateStart] = useState<string | null>(null);
  const [calendarView, setCalendarView] = useState<'timeGridWeek' | 'listWeek'>(
    'timeGridWeek',
  );
  const [pendingMove, setPendingMove] = useState<MoveInfo | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const lastRange = useRef<DatesSetInfo | null>(null);
  const request = useRef<AbortController | null>(null);
  const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

  useEffect(() => {
    const media = window.matchMedia('(max-width: 42rem)');
    const synchronizeView = () =>
      setCalendarView(media.matches ? 'listWeek' : 'timeGridWeek');
    synchronizeView();
    media.addEventListener('change', synchronizeView);
    window.addEventListener('resize', synchronizeView);
    return () => {
      media.removeEventListener('change', synchronizeView);
      window.removeEventListener('resize', synchronizeView);
    };
  }, []);

  const load = useCallback(
    async (range: DatesSetInfo) => {
      request.current?.abort();
      const controller = new AbortController();
      request.current = controller;
      setLoading(true);
      setError('');
      try {
        const data = await getCalendarEvents(
          slug,
          { start: range.startStr, end: range.endStr, timeZone },
          controller.signal,
        );
        setEvents(data);
      } catch (caught) {
        if (!controller.signal.aborted)
          setError(
            caught instanceof Error
              ? caught.message
              : 'No fue posible cargar la agenda.',
          );
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    },
    [slug, timeZone],
  );

  function onDatesSet(range: DatesSetInfo) {
    lastRange.current = range;
    void load(range);
  }

  async function persistMove(info: MoveInfo, scope: RecurrenceScope) {
    if (!info.event.start || !info.event.end) return info.revert();
    try {
      await rescheduleCalendarEvent(slug, info.event.id, {
        expected_version: Number(info.event.extendedProps.occurrenceVersion),
        starts_at: info.event.start.toISOString(),
        ends_at: info.event.end.toISOString(),
        scope,
      });
      if (lastRange.current) await load(lastRange.current);
    } catch (caught) {
      info.revert();
      setError(
        caught instanceof Error
          ? caught.message
          : 'No fue posible reprogramar.',
      );
    }
  }

  function findEvent(info: EventClickInfo) {
    const event = events.find((item) => item.id === info.event.id);
    if (event) setSelected(event);
  }

  return (
    <section className="academic-calendar" aria-busy={loading}>
      <div className="academic-calendar__actions">
        <p>{loading ? 'Actualizando agenda…' : `Zona horaria: ${timeZone}`}</p>
        <div>
          <Button
            onClick={() => lastRange.current && void load(lastRange.current)}
            size="sm"
            variant="outline"
          >
            <RefreshCcw /> Actualizar
          </Button>
          {canCreate ? (
            <Button
              onClick={() => setCreateStart(nextVisibleStart())}
              size="sm"
            >
              <CalendarPlus /> Nuevo evento
            </Button>
          ) : null}
        </div>
      </div>
      {error ? (
        <Alert variant="destructive">
          <AlertTitle>No se pudo completar la acción</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      ) : null}
      <div className="academic-calendar__surface">
        <FullCalendar
          key={calendarView}
          plugins={[
            classicThemePlugin,
            dayGridPlugin,
            timeGridPlugin,
            listPlugin,
            interactionPlugin,
          ]}
          locale={esLocale}
          timeZone={timeZone}
          initialView={calendarView}
          headerToolbar={{
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,listWeek',
          }}
          nowIndicator
          allDaySlot={false}
          slotMinTime="06:00:00"
          slotMaxTime="22:00:00"
          height="auto"
          editable
          eventResizableFromStart
          events={events}
          datesSet={onDatesSet}
          dateClick={(info: DateClickInfo) =>
            canCreate && setCreateStart(info.date.toISOString())
          }
          eventClick={findEvent}
          eventDrop={(info) =>
            info.event.extendedProps.recurring
              ? setPendingMove(info)
              : void persistMove(info, 'occurrence')
          }
          eventResize={(info) =>
            info.event.extendedProps.recurring
              ? setPendingMove(info)
              : void persistMove(info, 'occurrence')
          }
        />
      </div>
      <RecurrenceMoveDialog
        info={pendingMove}
        onClose={() => {
          pendingMove?.revert();
          setPendingMove(null);
        }}
        onConfirm={(scope) => {
          if (!pendingMove) return;
          const move = pendingMove;
          setPendingMove(null);
          void persistMove(move, scope);
        }}
      />
      <EventDialog
        event={selected}
        slug={slug}
        onClose={() => setSelected(null)}
        onChanged={async () => {
          setSelected(null);
          if (lastRange.current) await load(lastRange.current);
        }}
      />
      <CreateEventDialog
        canCreate={canCreate}
        courses={courses}
        participantOptions={participantOptions}
        slug={slug}
        startsAt={createStart}
        timeZone={timeZone}
        onClose={() => setCreateStart(null)}
        onCreated={async () => {
          setCreateStart(null);
          if (lastRange.current) await load(lastRange.current);
        }}
      />
    </section>
  );
}

function RecurrenceMoveDialog({
  info,
  onClose,
  onConfirm,
}: Readonly<{
  info: MoveInfo | null;
  onClose: () => void;
  onConfirm: (scope: RecurrenceScope) => void;
}>) {
  if (!info) return null;
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reprogramar una clase recurrente</DialogTitle>
          <DialogDescription>
            Elige qué parte de la serie debe adoptar el nuevo horario.
          </DialogDescription>
        </DialogHeader>
        <RecurrenceScopeButtons action="Reprogramar" onSelect={onConfirm} />
      </DialogContent>
    </Dialog>
  );
}

function RecurrenceScopeButtons({
  action,
  onSelect,
}: Readonly<{
  action: string;
  onSelect: (scope: RecurrenceScope) => void;
}>) {
  return (
    <div className="grid gap-2 sm:grid-cols-3">
      <Button variant="outline" onClick={() => onSelect('occurrence')}>
        {action} solo esta
      </Button>
      <Button variant="outline" onClick={() => onSelect('following')}>
        {action} esta y siguientes
      </Button>
      <Button variant="outline" onClick={() => onSelect('series')}>
        {action} toda la serie
      </Button>
    </div>
  );
}

function EventDialog({
  event,
  onChanged,
  onClose,
  slug,
}: Readonly<{
  event: CalendarEvent | null;
  onChanged: () => Promise<void>;
  onClose: () => void;
  slug: string;
}>) {
  if (!event) return null;
  const props = event.extendedProps;
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{event.title}</DialogTitle>
          <DialogDescription>
            {props.courseName} · {props.hostName}
          </DialogDescription>
        </DialogHeader>
        <p>{props.description || 'Sin descripción adicional.'}</p>
        <p className="text-xs text-muted-foreground">
          {new Intl.DateTimeFormat('es-CO', {
            dateStyle: 'full',
            timeStyle: 'short',
          }).format(new Date(event.start))}
        </p>
        <DialogFooter>
          {props.sessionId ? (
            <Button asChild>
              <Link href={`/organizaciones/${slug}/clases/${props.sessionId}`}>
                Abrir clase <ExternalLink />
              </Link>
            </Button>
          ) : null}
          {props.canDelete && !props.recurring ? (
            <Button
              variant="destructive"
              onClick={() =>
                void cancelCalendarEvent(slug, event.id, {
                  expected_version: props.occurrenceVersion,
                  scope: 'occurrence',
                }).then(onChanged)
              }
            >
              <Trash2 /> Cancelar
            </Button>
          ) : null}
        </DialogFooter>
        {props.canDelete && props.recurring ? (
          <>
            <p className="text-sm font-medium">Cancelar recurrencia</p>
            <RecurrenceScopeButtons
              action="Cancelar"
              onSelect={(scope) =>
                void cancelCalendarEvent(slug, event.id, {
                  expected_version: props.occurrenceVersion,
                  scope,
                }).then(onChanged)
              }
            />
          </>
        ) : null}
      </DialogContent>
    </Dialog>
  );
}

function CreateEventDialog({
  canCreate,
  courses,
  onClose,
  onCreated,
  participantOptions,
  slug,
  startsAt,
  timeZone,
}: Readonly<{
  canCreate: boolean;
  courses: CourseOption[];
  onClose: () => void;
  onCreated: () => Promise<void>;
  participantOptions: ParticipantOption[];
  slug: string;
  startsAt: string | null;
  timeZone: string;
}>) {
  const [courseSlug, setCourseSlug] = useState(courses[0]?.slug ?? '');
  const [countsTowardProgress, setCountsTowardProgress] = useState(false);
  const [submissionError, setSubmissionError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  if (!canCreate || !startsAt) return null;
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <form
          className="grid gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            const data = new FormData(event.currentTarget);
            setSubmissionError('');
            setSubmitting(true);
            void createCalendarEvent(slug, {
              course_slug: courseSlug || null,
              participant_membership_ids: courseSlug
                ? []
                : data.getAll('participants').map(String),
              title: String(data.get('title')),
              description: String(data.get('description') ?? ''),
              event_type: 'live_class',
              timezone_name: timeZone,
              starts_at: new Date(String(data.get('startsAt'))).toISOString(),
              duration_minutes: Number(data.get('duration')),
              rrule: String(data.get('rrule') ?? ''),
              counts_toward_progress: Boolean(
                courseSlug && countsTowardProgress,
              ),
              attendance_threshold_minutes:
                courseSlug && countsTowardProgress
                  ? Number(data.get('attendanceThreshold'))
                  : null,
            })
              .then(onCreated)
              .catch((caught) =>
                setSubmissionError(
                  caught instanceof Error
                    ? caught.message
                    : 'No fue posible crear la sesión.',
                ),
              )
              .finally(() => setSubmitting(false));
          }}
        >
          <DialogHeader>
            <DialogTitle>Programar evento académico</DialogTitle>
            <DialogDescription>
              Las recurrencias deben tener COUNT o UNTIL y un máximo de 366
              fechas.
            </DialogDescription>
          </DialogHeader>
          {submissionError ? (
            <Alert variant="destructive">
              <AlertTitle>No se pudo programar la sesión</AlertTitle>
              <AlertDescription>{submissionError}</AlertDescription>
            </Alert>
          ) : null}
          <Label>
            Vinculación académica
            <select
              className="academic-select"
              name="course"
              value={courseSlug}
              onChange={(event) => {
                setCourseSlug(event.target.value);
                if (!event.target.value) setCountsTowardProgress(false);
              }}
            >
              <option value="">Sesión independiente (sin curso)</option>
              {courses.map((course) => (
                <option key={course.slug} value={course.slug}>
                  {course.title}
                </option>
              ))}
            </select>
          </Label>
          {!courseSlug ? (
            <fieldset className="grid gap-2 rounded-lg border p-3">
              <legend className="px-1 text-sm font-medium">
                Participantes invitados
              </legend>
              <p className="text-xs text-muted-foreground">
                Sólo las personas seleccionadas y el profesor podrán verla y
                entrar.
              </p>
              <div className="max-h-40 space-y-2 overflow-y-auto">
                {participantOptions.map((participant) => (
                  <Label
                    className="flex items-center gap-2 font-normal"
                    key={participant.membershipId}
                  >
                    <input
                      name="participants"
                      type="checkbox"
                      value={participant.membershipId}
                    />
                    {participant.display}
                  </Label>
                ))}
              </div>
            </fieldset>
          ) : (
            <fieldset className="grid gap-2 rounded-lg border p-3">
              <legend className="px-1 text-sm font-medium">Progreso</legend>
              <Label className="flex items-center gap-2 font-normal">
                <input
                  checked={countsTowardProgress}
                  onChange={(event) =>
                    setCountsTowardProgress(event.target.checked)
                  }
                  type="checkbox"
                />
                Esta clase es requisito para completar el curso
              </Label>
              {countsTowardProgress ? (
                <Label>
                  Asistencia mínima en minutos
                  <Input
                    name="attendanceThreshold"
                    type="number"
                    min={1}
                    max={720}
                    defaultValue={45}
                    required
                  />
                </Label>
              ) : null}
            </fieldset>
          )}
          <Label>
            Título
            <Input name="title" required maxLength={200} />
          </Label>
          <Label>
            Inicio
            <Input
              name="startsAt"
              type="datetime-local"
              required
              defaultValue={toLocalInput(startsAt)}
            />
          </Label>
          <Label>
            Duración en minutos
            <Input
              name="duration"
              type="number"
              min={5}
              max={720}
              defaultValue={60}
              required
            />
          </Label>
          <Label>
            Recurrencia RFC 5545 opcional
            <Input name="rrule" placeholder="FREQ=WEEKLY;COUNT=8;BYDAY=MO" />
          </Label>
          <Label>
            Descripción
            <Input name="description" maxLength={2000} />
          </Label>
          <DialogFooter>
            <Button disabled={submitting} type="submit">
              {submitting ? 'Creando…' : 'Crear evento'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function toLocalInput(value: string) {
  const date = new Date(value);
  const offset = date.getTimezoneOffset();
  return new Date(date.getTime() - offset * 60_000).toISOString().slice(0, 16);
}

function nextVisibleStart() {
  const date = new Date();
  date.setMinutes(0, 0, 0);
  date.setHours(date.getHours() + 1);
  if (date.getHours() < 6) date.setHours(8);
  if (date.getHours() >= 22) {
    date.setDate(date.getDate() + 1);
    date.setHours(8);
  }
  return date.toISOString();
}
