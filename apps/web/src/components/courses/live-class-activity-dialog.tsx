'use client';

import { useState } from 'react';
import {
  CalendarClock,
  Check,
  MessageSquareText,
  Radio,
  Settings2,
  Users,
  Video,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import type { components } from '@/lib/api/generated/platform';

type Objective = components['schemas']['Objective'];
type Activity = components['schemas']['CourseActivity'];
type Binding = components['schemas']['LiveClassActivityBinding'];

export function LiveClassActivityDialog({
  activity,
  binding,
  isSaving,
  objectives,
  onSubmit,
}: Readonly<{
  activity?: Activity;
  binding?: Binding;
  isSaving: boolean;
  objectives: Objective[];
  onSubmit: (formData: FormData) => Promise<boolean>;
}>) {
  const editing = Boolean(activity);
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState(binding?.session_mode ?? 'interactive');
  const [recording, setRecording] = useState(binding?.recording_mode ?? 'off');

  async function submit(formData: FormData) {
    if (await onSubmit(formData)) setOpen(false);
  }

  return (
    <Dialog
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (nextOpen) {
          setMode(binding?.session_mode ?? 'interactive');
          setRecording(binding?.recording_mode ?? 'off');
        }
      }}
      open={open}
    >
      <DialogTrigger asChild>
        {editing ? (
          <Button size="sm" variant="outline">
            <Settings2 />
            Configurar LiveKit
          </Button>
        ) : (
          <Button
            className="h-auto justify-start gap-3 px-3 py-3"
            variant="outline"
          >
            <span className="rounded-md bg-primary/10 p-1.5 text-primary">
              <Video className="size-4" />
            </span>
            <span className="text-left">
              <span className="block text-sm font-semibold">Clase en vivo</span>
              <span className="block text-xs font-normal text-muted-foreground">
                Sala LiveKit, participación y asistencia
              </span>
            </span>
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="max-h-[92vh] overflow-y-auto p-0 sm:max-w-5xl">
        <DialogHeader className="border-b px-5 pt-5 pb-4">
          <div className="flex items-center gap-2">
            <Badge variant="outline">LiveKit</Badge>
            <Badge className="bg-emerald-600 text-white">Sesión real</Badge>
          </div>
          <DialogTitle className="text-xl">
            {editing
              ? `Configurar «${activity?.title}»`
              : 'Configurar clase en vivo'}
          </DialogTitle>
          <DialogDescription>
            {editing
              ? 'Actualiza la identidad, la alineación y la política reutilizable de la sala antes de publicar.'
              : 'Define una política reutilizable para la sala. La fecha, el grupo y el docente se programan después sobre la versión publicada del curso.'}
          </DialogDescription>
        </DialogHeader>
        <form action={submit}>
          <div className="grid gap-4 p-5 lg:grid-cols-[1.15fr_0.85fr]">
            <div className="space-y-4">
              <section className="rounded-xl border p-4">
                <div className="mb-3 flex items-start gap-3">
                  <span className="rounded-lg bg-primary/10 p-2 text-primary">
                    <Radio className="size-4" />
                  </span>
                  <div>
                    <h3 className="font-semibold">Identidad de la clase</h3>
                    <p className="text-xs text-muted-foreground">
                      Lo que verá el estudiante en su recorrido.
                    </p>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <label className="academic-field sm:col-span-2">
                    Título
                    <input
                      className="academic-control"
                      defaultValue={activity?.title}
                      maxLength={200}
                      name="live-title"
                      placeholder="Ej. Laboratorio de estabilidad y plano fase"
                      required
                    />
                  </label>
                  <label className="academic-field sm:col-span-2">
                    Propósito y dinámica
                    <textarea
                      className="academic-control min-h-20"
                      defaultValue={activity?.summary}
                      maxLength={1200}
                      name="live-summary"
                      placeholder="Qué resolverán y cómo participarán durante la sesión"
                    />
                  </label>
                  <label className="academic-field">
                    Duración prevista (min)
                    <input
                      className="academic-control"
                      defaultValue={activity?.estimated_duration_minutes ?? 90}
                      max={720}
                      min={5}
                      name="live-duration"
                      required
                      type="number"
                    />
                  </label>
                  <label className="academic-field">
                    Asistencia mínima (%)
                    <input
                      className="academic-control"
                      defaultValue={
                        activity?.minimum_attendance_basis_points
                          ? activity.minimum_attendance_basis_points / 100
                          : 75
                      }
                      max={100}
                      min={1}
                      name="live-threshold"
                      required
                      type="number"
                    />
                  </label>
                </div>
                <label className="mt-3 flex items-center gap-2 text-sm font-medium">
                  <input
                    defaultChecked={activity?.required ?? true}
                    name="live-required"
                    type="checkbox"
                  />
                  Actividad obligatoria
                </label>
              </section>

              <section className="rounded-xl border p-4">
                <div className="mb-3 flex items-start gap-3">
                  <span className="rounded-lg bg-primary/10 p-2 text-primary">
                    <Check className="size-4" />
                  </span>
                  <div>
                    <h3 className="font-semibold">Objetivos que trabaja</h3>
                    <p className="text-xs text-muted-foreground">
                      La alineación queda guardada junto con la actividad; no
                      tendrás que repararla al aprobar.
                    </p>
                  </div>
                </div>
                {objectives.length ? (
                  <div className="grid max-h-44 gap-2 overflow-y-auto pr-1">
                    {objectives.map((objective) => (
                      <label
                        className="flex items-start gap-2 rounded-lg border px-3 py-2 text-sm hover:bg-muted/30"
                        key={objective.id}
                      >
                        <input
                          className="mt-1"
                          defaultChecked={activity?.learning_objective_ids.includes(
                            objective.id,
                          )}
                          name="live-objective"
                          type="checkbox"
                          value={objective.id}
                        />
                        <span>
                          <strong className="font-medium">
                            {objective.code}
                          </strong>
                          <span className="mt-0.5 block text-xs text-muted-foreground">
                            {objective.statement}
                          </span>
                        </span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <p className="rounded-lg border border-dashed p-3 text-sm text-muted-foreground">
                    Alinea primero objetivos al curso.
                  </p>
                )}
              </section>
            </div>

            <div className="space-y-4">
              <section className="rounded-xl border p-4">
                <div className="mb-3 flex items-start gap-3">
                  <span className="rounded-lg bg-primary/10 p-2 text-primary">
                    <Users className="size-4" />
                  </span>
                  <div>
                    <h3 className="font-semibold">Experiencia de sala</h3>
                    <p className="text-xs text-muted-foreground">
                      Permisos iniciales; el docente conserva moderación.
                    </p>
                  </div>
                </div>
                <label className="academic-field">
                  Formato
                  <select
                    className="academic-control"
                    name="live-session-mode"
                    onChange={(event) => setMode(event.target.value)}
                    value={mode}
                  >
                    <option value="interactive">
                      Interactiva · todos participan
                    </option>
                    <option value="webinar">
                      Seminario · audiencia en escucha
                    </option>
                  </select>
                </label>
                <div className="mt-3 grid gap-2">
                  <label className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm">
                    <span>Micrófono de estudiantes</span>
                    <input
                      defaultChecked={
                        binding?.student_audio_enabled ?? mode === 'interactive'
                      }
                      key={`audio-${mode}`}
                      name="live-student-audio"
                      type="checkbox"
                    />
                  </label>
                  <label className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm">
                    <span>Cámara de estudiantes</span>
                    <input
                      defaultChecked={
                        binding?.student_video_enabled ?? mode === 'interactive'
                      }
                      key={`video-${mode}`}
                      name="live-student-video"
                      type="checkbox"
                    />
                  </label>
                  <label className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm">
                    <span>Compartir pantalla</span>
                    <input
                      defaultChecked={
                        binding?.student_screen_share_enabled ??
                        mode === 'interactive'
                      }
                      key={`screen-${mode}`}
                      name="live-student-screen"
                      type="checkbox"
                    />
                  </label>
                  <label className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2 text-sm">
                    <span className="flex items-center gap-2">
                      <MessageSquareText className="size-4" />
                      Chat en tiempo real
                    </span>
                    <input
                      defaultChecked={binding?.chat_enabled ?? true}
                      name="live-chat"
                      type="checkbox"
                    />
                  </label>
                </div>
                <div className="mt-3 grid grid-cols-2 gap-3">
                  <label className="academic-field">
                    Cupo máximo
                    <input
                      className="academic-control"
                      defaultValue={binding?.max_participants ?? 100}
                      max={1000}
                      min={2}
                      name="live-max-participants"
                      type="number"
                    />
                  </label>
                  <label className="academic-field">
                    Cerrar sala vacía (min)
                    <input
                      className="academic-control"
                      defaultValue={
                        (binding?.room_empty_timeout_seconds ?? 600) / 60
                      }
                      max={60}
                      min={1}
                      name="live-empty-timeout"
                      type="number"
                    />
                  </label>
                </div>
              </section>

              <section className="rounded-xl border p-4">
                <div className="mb-3 flex items-start gap-3">
                  <span className="rounded-lg bg-primary/10 p-2 text-primary">
                    <Video className="size-4" />
                  </span>
                  <div>
                    <h3 className="font-semibold">Grabación</h3>
                    <p className="text-xs text-muted-foreground">
                      Privada y con aviso explícito antes de ingresar.
                    </p>
                  </div>
                </div>
                <div className="grid gap-3 sm:grid-cols-3">
                  <label className="academic-field">
                    Disponibilidad
                    <select
                      className="academic-control"
                      name="live-recording-mode"
                      onChange={(event) => setRecording(event.target.value)}
                      value={recording}
                    >
                      <option value="off">No grabar</option>
                      <option value="manual">El docente decide en el aula</option>
                    </select>
                  </label>
                  <label className="academic-field">
                    Composición sugerida
                    <select
                      className="academic-control"
                      disabled={recording === 'off'}
                      name="live-recording-layout"
                      defaultValue={binding?.recording_layout ?? 'screen_share'}
                    >
                      <option value="screen_share">
                        Sólo pantalla compartida
                      </option>
                      <option value="speaker">Docente activo</option>
                      <option value="grid">Cuadrícula</option>
                    </select>
                  </label>
                  <label className="academic-field">
                    Calidad sugerida
                    <select
                      className="academic-control"
                      disabled={recording === 'off'}
                      name="live-recording-resolution"
                      defaultValue={binding?.recording_resolution ?? '1080p'}
                    >
                      <option value="1080p">1080p · Full HD</option>
                      <option value="720p">720p · HD</option>
                    </select>
                  </label>
                </div>
                {recording !== 'off' ? (
                  <div className="mt-3 space-y-2 rounded-lg bg-amber-500/10 px-3 py-2 text-xs text-amber-950">
                    <p>
                      Estos valores sólo preparan la selección inicial. El
                      docente elige en el aula cuándo empezar, la composición
                      y la calidad de cada grabación.
                    </p>
                    <p>
                      Todos deberán reconocer el aviso antes de conectarse. El
                      chat no se incorpora al archivo ni se convierte en
                      historial.
                    </p>
                  </div>
                ) : null}
              </section>

              <section className="rounded-xl border p-4">
                <div className="mb-3 flex items-start gap-3">
                  <span className="rounded-lg bg-primary/10 p-2 text-primary">
                    <CalendarClock className="size-4" />
                  </span>
                  <div>
                    <h3 className="font-semibold">Ventana operativa</h3>
                    <p className="text-xs text-muted-foreground">
                      Controla cuándo pueden entrar; no fija todavía una fecha.
                    </p>
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <label className="academic-field">
                    Entrada anticipada (min)
                    <input
                      className="academic-control"
                      defaultValue={binding?.join_before_minutes ?? 15}
                      max={120}
                      min={0}
                      name="live-join-before"
                      type="number"
                    />
                  </label>
                  <label className="academic-field">
                    Margen al finalizar (min)
                    <input
                      className="academic-control"
                      defaultValue={binding?.join_after_minutes ?? 15}
                      max={120}
                      min={0}
                      name="live-join-after"
                      type="number"
                    />
                  </label>
                </div>
                <input
                  name="live-departure-timeout"
                  type="hidden"
                  value={binding?.room_departure_timeout_seconds ?? 30}
                />
              </section>
            </div>
          </div>
          <DialogFooter className="mx-0 mb-0 rounded-none px-5">
            <Button disabled={isSaving || !objectives.length} type="submit">
              <Video />
              {isSaving
                ? editing
                  ? 'Guardando…'
                  : 'Creando sala…'
                : editing
                  ? 'Guardar configuración'
                  : 'Añadir clase en vivo'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
