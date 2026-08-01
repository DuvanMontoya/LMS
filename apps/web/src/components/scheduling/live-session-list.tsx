import { CalendarClock, GraduationCap, Radio, Video } from 'lucide-react';
import Link from 'next/link';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { components } from '@/lib/api/generated/platform';

type Session = components['schemas']['LiveSessionDetail'];

const statusLabels: Record<string, string> = {
  cancelled: 'Cancelada',
  ended: 'Finalizada',
  live: 'En vivo',
  scheduled: 'Programada',
};

export function LiveSessionList({
  emptyMessage = 'No hay clases en vivo en este periodo.',
  sessions,
  slug,
}: Readonly<{ emptyMessage?: string; sessions: Session[]; slug: string }>) {
  if (!sessions.length) {
    return (
      <div className="rounded-xl border border-dashed p-8 text-center">
        <Video className="mx-auto mb-3 size-8 text-muted-foreground" />
        <p className="font-medium">Sin clases programadas</p>
        <p className="mt-1 text-sm text-muted-foreground">{emptyMessage}</p>
      </div>
    );
  }
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {sessions.map((session) => (
        <article
          className="rounded-xl border bg-card p-5 shadow-sm"
          key={session.id}
        >
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <Badge
                  variant={session.status === 'live' ? 'default' : 'secondary'}
                >
                  {session.status === 'live' ? <Radio /> : <CalendarClock />}
                  {statusLabels[session.status] ?? session.status}
                </Badge>
                {session.countsTowardProgress ? (
                  <Badge variant="outline">Cuenta para el progreso</Badge>
                ) : null}
              </div>
              <h2 className="truncate text-lg font-semibold">
                {session.title}
              </h2>
              <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">
                {session.description || 'Sesión académica sincrónica.'}
              </p>
            </div>
            <Video className="size-5 shrink-0 text-primary" />
          </div>
          <dl className="mt-4 grid gap-2 text-sm sm:grid-cols-2">
            <div>
              <dt className="text-muted-foreground">Fecha y hora</dt>
              <dd className="font-medium">
                {new Intl.DateTimeFormat('es-CO', {
                  dateStyle: 'medium',
                  timeStyle: 'short',
                }).format(new Date(session.scheduledStart))}
              </dd>
            </div>
            <div>
              <dt className="text-muted-foreground">Profesor</dt>
              <dd className="font-medium">{session.hostName}</dd>
            </div>
          </dl>
          <div className="mt-5 flex flex-wrap items-center justify-between gap-3">
            {session.course ? (
              <span className="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                <GraduationCap className="size-4" /> Clase de curso
              </span>
            ) : (
              <span className="text-xs text-muted-foreground">
                Sesión independiente
              </span>
            )}
            <Button asChild size="sm">
              <Link href={`/organizaciones/${slug}/clases/${session.id}`}>
                {session.canJoin
                  ? 'Entrar a clase'
                  : session.canStart
                    ? 'Iniciar clase'
                    : 'Ver detalles'}
              </Link>
            </Button>
          </div>
        </article>
      ))}
    </div>
  );
}
