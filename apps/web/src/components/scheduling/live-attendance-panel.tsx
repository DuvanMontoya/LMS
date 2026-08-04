'use client';

import {
  CircleCheck,
  Clock3,
  Loader2,
  RefreshCw,
  UsersRound,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import type { components } from '@/lib/api/generated/platform';
import { getLiveAttendance } from '@/lib/scheduling/api';

type AttendanceSummary = components['schemas']['AttendanceSummary'];

export function LiveAttendancePanel({
  sessionId,
  sessionStatus,
  slug,
  thresholdMinutes,
}: Readonly<{
  sessionId: string;
  sessionStatus: string;
  slug: string;
  thresholdMinutes: number | null;
}>) {
  const [rows, setRows] = useState<AttendanceSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const refresh = useCallback(async () => {
    try {
      const result = await getLiveAttendance(slug, sessionId);
      setRows(result);
      setError('');
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : 'No fue posible consultar la asistencia.',
      );
    } finally {
      setLoading(false);
    }
  }, [sessionId, slug]);

  useEffect(() => {
    const initial = window.setTimeout(() => void refresh(), 0);
    if (sessionStatus !== 'live') {
      return () => window.clearTimeout(initial);
    }
    const interval = window.setInterval(() => void refresh(), 15_000);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(interval);
    };
  }, [refresh, sessionStatus]);

  const studentRows = rows.filter((row) => row.role === 'student');
  return (
    <section
      className="live-attendance-panel"
      aria-labelledby="attendance-title"
    >
      <header>
        <div>
          <p className="academic-kicker">Seguimiento verificable</p>
          <h2 id="attendance-title">Asistencia de la clase</h2>
          <p>
            Duración acumulada por estudiante a partir de entradas y salidas del
            aula.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {thresholdMinutes === null ? null : (
            <span className="live-attendance-panel__threshold">
              <Clock3 /> Mínimo {thresholdMinutes} min
            </span>
          )}
          <Button
            aria-label="Actualizar asistencia"
            disabled={loading}
            onClick={() => {
              setLoading(true);
              void refresh();
            }}
            size="icon-sm"
            type="button"
            variant="outline"
          >
            {loading ? <Loader2 className="animate-spin" /> : <RefreshCw />}
          </Button>
        </div>
      </header>
      {error ? (
        <p className="live-attendance-panel__error" role="alert">
          {error}
        </p>
      ) : studentRows.length ? (
        <ul>
          {studentRows.map((row) => {
            const attendedMinutes =
              row.duration_seconds === null
                ? null
                : Math.floor(row.duration_seconds / 60);
            const satisfied =
              thresholdMinutes === null ||
              (attendedMinutes !== null && attendedMinutes >= thresholdMinutes);
            return (
              <li key={`${row.user_id ?? 'guest'}-${row.participant_identity}`}>
                <span className="live-attendance-panel__avatar">
                  {participantInitial(row)}
                </span>
                <div>
                  <strong>{participantLabel(row)}</strong>
                  <span>Estudiante</span>
                </div>
                <div className="live-attendance-panel__duration">
                  <strong>
                    {attendedMinutes === null
                      ? sessionStatus === 'live'
                        ? 'En sala'
                        : 'Sin duración'
                      : durationLabel(row.duration_seconds ?? 0)}
                  </strong>
                  <span>
                    {attendedMinutes === null && sessionStatus === 'live'
                      ? 'Se consolidará al salir'
                      : thresholdMinutes === null
                        ? 'Registro informativo'
                        : satisfied
                          ? 'Mínimo cumplido'
                          : `Faltan ${Math.max(0, thresholdMinutes - (attendedMinutes ?? 0))} min`}
                  </span>
                </div>
                <span
                  className="live-attendance-panel__result"
                  data-satisfied={satisfied}
                >
                  {satisfied ? <CircleCheck /> : <Clock3 />}
                  {satisfied ? 'Cumple' : 'Pendiente'}
                </span>
              </li>
            );
          })}
        </ul>
      ) : loading ? (
        <p className="live-attendance-panel__empty" role="status">
          <Loader2 className="animate-spin" /> Consultando asistencia…
        </p>
      ) : (
        <p className="live-attendance-panel__empty">
          <UsersRound /> Aún no hay asistencia estudiantil registrada.
        </p>
      )}
    </section>
  );
}

function participantLabel(row: AttendanceSummary): string {
  const displayName = row.display_name?.trim();
  if (displayName) return displayName;
  const identity = row.participant_identity;
  const candidate = identity.split(':').at(-1) ?? identity;
  return candidate.includes('@') ? candidate : candidate.replaceAll('-', ' ');
}

function participantInitial(row: AttendanceSummary): string {
  return participantLabel(row).trim().charAt(0).toUpperCase() || 'E';
}

function durationLabel(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes} min ${remainingSeconds.toString().padStart(2, '0')} s`;
}
