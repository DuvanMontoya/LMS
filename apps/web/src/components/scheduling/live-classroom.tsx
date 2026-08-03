'use client';

import {
  ChatEntry,
  ChatToggle,
  DisconnectButton,
  GridLayout,
  LayoutContextProvider,
  ParticipantTile,
  RoomAudioRenderer,
  RoomContext,
  StartAudio,
  TrackToggle,
  formatChatMessageLinks,
  useChat,
  useLayoutContext,
  useParticipants,
  useTracks,
} from '@livekit/components-react';
import {
  CalendarClock,
  DoorOpen,
  Loader2,
  MessageCircle,
  Radio,
  Send,
  Timer,
  UserRound,
  X,
} from 'lucide-react';
import { Room, RoomEvent, Track } from 'livekit-client';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import {
  endLiveSession,
  enterLiveSession,
  changeParticipantPermissions,
  removeParticipant,
  startLiveRecording,
  stopLiveRecording,
  type LiveConnection,
} from '@/lib/scheduling/api';
import type { LiveSessionDetail } from '@/lib/scheduling/server';

export function LiveClassroom({
  detail,
  slug,
}: Readonly<{ detail: LiveSessionDetail; slug: string }>) {
  const [connection, setConnection] = useState<LiveConnection | null>(null);
  const [busy, setBusy] = useState(false);
  const [recordingAcknowledged, setRecordingAcknowledged] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    if (detail.status !== 'scheduled' || detail.canStart) return;
    const interval = window.setInterval(() => router.refresh(), 15_000);
    return () => window.clearInterval(interval);
  }, [detail.canStart, detail.status, router]);

  async function enter() {
    setBusy(true);
    setError('');
    try {
      const action = detail.canStart ? 'start' : 'join';
      setConnection(
        await enterLiveSession(slug, detail.id, action, recordingAcknowledged),
      );
    } catch (caught) {
      setError(
        caught instanceof Error
          ? caught.message
          : 'No fue posible entrar a la clase.',
      );
    } finally {
      setBusy(false);
    }
  }

  if (connection) {
    return (
      <div className="live-class-experience" data-state="active">
        <ConnectedClassroom
          connection={connection}
          slug={slug}
          onEnd={
            detail.canModerate
              ? () => endLiveSession(slug, detail.id)
              : undefined
          }
        />
      </div>
    );
  }

  const mayEnter = detail.canStart || detail.canJoin;
  const recordingEnabled = detail.recordingMode !== 'off';
  return (
    <section className="live-class-experience" data-state="briefing">
      <header className="live-briefing__header">
        <div>
          <span className="live-status" data-status={detail.status}>
            {statusLabel(detail.status)}
          </span>
          <p>Clase sincrónica</p>
          <h2>{detail.title}</h2>
          {detail.description ? <div>{detail.description}</div> : null}
        </div>
        <dl className="live-briefing__facts">
          <LiveFact
            icon={<CalendarClock />}
            label="Inicio"
            value={dateTimeLabel(detail.scheduledStart)}
          />
          <LiveFact
            icon={<Timer />}
            label="Duración"
            value={sessionDurationLabel(
              detail.scheduledStart,
              detail.scheduledEnd,
            )}
          />
          <LiveFact
            icon={<UserRound />}
            label="Docente"
            value={detail.hostName}
          />
        </dl>
      </header>

      <div className="live-lobby">
        <div className="live-lobby__panel">
          {error ? (
            <Alert variant="destructive">
              <AlertTitle>No fue posible entrar</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : null}
          {recordingEnabled ? (
            <label className="live-lobby__recording">
              <input
                checked={recordingAcknowledged}
                onChange={(event) =>
                  setRecordingAcknowledged(event.target.checked)
                }
                type="checkbox"
              />
              <span>
                Comprendo que esta clase puede grabarse de forma privada.
              </span>
            </label>
          ) : null}
          <p className="live-lobby__note">
            Cámara, micrófono y pantalla se activan únicamente desde la sala.
            {detail.chatEnabled
              ? ' El chat está disponible en tiempo real.'
              : ''}
          </p>
          <div className="live-lobby__actions">
            <Button
              type="button"
              onClick={() => void enter()}
              disabled={
                !mayEnter ||
                busy ||
                (recordingEnabled && !recordingAcknowledged)
              }
            >
              {busy ? <Loader2 className="animate-spin" /> : <DoorOpen />}{' '}
              {entryActionLabel(detail, mayEnter)}
            </Button>
          </div>
          {!mayEnter ? (
            <p className="live-lobby__waiting" role="status">
              <CalendarClock />
              {waitingMessage(detail)}
            </p>
          ) : null}
        </div>
      </div>
    </section>
  );
}

function ConnectedClassroom({
  connection,
  onEnd,
  slug,
}: Readonly<{
  connection: LiveConnection;
  onEnd?: (() => Promise<unknown>) | undefined;
  slug: string;
}>) {
  const room = useMemo(
    () => new Room({ adaptiveStream: true, dynacast: true }),
    [],
  );
  const [connectionError, setConnectionError] = useState('');
  const [mediaError, setMediaError] = useState('');
  const [recordingStatus, setRecordingStatus] = useState(
    connection.session.recordingStatus,
  );
  const [controlsHost, setControlsHost] = useState<HTMLElement | null>(null);
  const disconnectTimer = useRef<number | null>(null);

  useEffect(() => {
    if (disconnectTimer.current !== null) {
      window.clearTimeout(disconnectTimer.current);
      disconnectTimer.current = null;
    }
    const onDisconnected = () => undefined;
    room.on(RoomEvent.Disconnected, onDisconnected);
    void (async () => {
      try {
        await room.connect(connection.serverUrl, connection.token);
      } catch (caught: unknown) {
        setConnectionError(
          caught instanceof Error
            ? caught.message
            : 'No fue posible conectar con LiveKit.',
        );
      }
    })();
    return () => {
      room.off(RoomEvent.Disconnected, onDisconnected);
      disconnectTimer.current = window.setTimeout(() => {
        void room.disconnect();
        disconnectTimer.current = null;
      }, 0);
    };
  }, [connection.serverUrl, connection.token, room]);

  useEffect(() => {
    let mounted = true;
    queueMicrotask(() => {
      if (mounted) {
        setControlsHost(
          document.getElementById('learning-player-live-controls'),
        );
      }
    });
    return () => {
      mounted = false;
    };
  }, []);

  const reportDeviceError = (error: Error) =>
    setMediaError(
      error.message ||
        'Chrome no permitió activar el dispositivo solicitado. Revisa el permiso y vuelve a intentarlo.',
    );

  const controls = (
    <div className="live-classroom__controls" aria-label="Controles de clase">
      {connection.session.canPublishAudio ? (
        <TrackToggle
          aria-label="Micrófono"
          onDeviceError={reportDeviceError}
          source={Track.Source.Microphone}
        >
          <span>Micrófono</span>
        </TrackToggle>
      ) : null}
      {connection.session.canPublishVideo ? (
        <TrackToggle
          aria-label="Cámara"
          onDeviceError={reportDeviceError}
          source={Track.Source.Camera}
        >
          <span>Cámara</span>
        </TrackToggle>
      ) : null}
      {connection.session.canShareScreen ? (
        <TrackToggle
          aria-label="Compartir pantalla"
          onDeviceError={reportDeviceError}
          source={Track.Source.ScreenShare}
        >
          <span>Compartir pantalla</span>
        </TrackToggle>
      ) : null}
      {connection.session.chatEnabled ? (
        <ChatToggle aria-label="Abrir o cerrar el chat">
          <MessageCircle />
          <span>Chat</span>
        </ChatToggle>
      ) : null}
      {connection.session.canModerate &&
      connection.session.recordingMode !== 'off' ? (
        recordingStatus === 'active' || recordingStatus === 'starting' ? (
          <Button
            type="button"
            variant="destructive"
            onClick={() =>
              void stopLiveRecording(slug, connection.session.id).then(
                (result) => setRecordingStatus(result.status),
              )
            }
          >
            Detener grabación
          </Button>
        ) : (
          <Button
            type="button"
            variant="outline"
            onClick={() =>
              void startLiveRecording(slug, connection.session.id).then(
                (result) => setRecordingStatus(result.status),
              )
            }
          >
            <Radio />
            Grabar
          </Button>
        )
      ) : null}
      <DisconnectButton onClick={() => onEnd && void onEnd()}>
        <DoorOpen />
        <span>Salir</span>
      </DisconnectButton>
    </div>
  );

  return (
    <RoomContext.Provider value={room}>
      <LayoutContextProvider>
        <section className="live-classroom" data-lk-theme="default">
          {connectionError ? (
            <Alert variant="destructive">
              <AlertTitle>Conexión interrumpida</AlertTitle>
              <AlertDescription>{connectionError}</AlertDescription>
            </Alert>
          ) : null}
          {mediaError ? (
            <Alert>
              <AlertTitle>Dispositivos no disponibles</AlertTitle>
              <AlertDescription>{mediaError}</AlertDescription>
            </Alert>
          ) : null}
          {recordingStatus === 'active' || recordingStatus === 'starting' ? (
            <Alert className="border-red-600/30 bg-red-500/10">
              <Radio className="animate-pulse text-red-700" />
              <AlertTitle>
                Grabación{' '}
                {recordingStatus === 'active' ? 'activa' : 'iniciando'}
              </AlertTitle>
              <AlertDescription>
                LiveKit Egress está componiendo esta sala en un archivo privado.
              </AlertDescription>
            </Alert>
          ) : null}
          <ClassroomSurface chatEnabled={connection.session.chatEnabled} />
          {connection.session.canModerate ? (
            <ParticipantPanel sessionId={connection.session.id} slug={slug} />
          ) : null}
          <RoomAudioRenderer />
          <StartAudio label="Activar audio" />
          {controlsHost ? createPortal(controls, controlsHost) : controls}
        </section>
      </LayoutContextProvider>
    </RoomContext.Provider>
  );
}

function ClassroomSurface({ chatEnabled }: Readonly<{ chatEnabled: boolean }>) {
  const layout = useLayoutContext();
  const chatOpen = Boolean(layout.widget.state?.showChat);
  return (
    <div className="live-classroom__surface" data-chat-open={chatOpen}>
      <ParticipantGrid />
      {chatEnabled && chatOpen ? <ClassroomChat /> : null}
    </div>
  );
}

function ClassroomChat() {
  const { chatMessages, isSending, send } = useChat();
  const [message, setMessage] = useState('');
  const listRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    listRef.current?.scrollTo({ top: listRef.current.scrollHeight });
  }, [chatMessages]);

  return (
    <aside className="live-classroom__chat" aria-label="Chat de la clase">
      <header>
        <div>
          <strong>Chat</strong>
          <span>Mensajes de esta sesión</span>
        </div>
        <ChatToggle aria-label="Cerrar chat">
          <X />
        </ChatToggle>
      </header>
      <ul ref={listRef} aria-live="polite">
        {chatMessages.length ? (
          chatMessages.map((entry, index) => (
            <ChatEntry
              entry={entry}
              key={entry.id ?? `${entry.timestamp}-${index}`}
              messageFormatter={formatChatMessageLinks}
            />
          ))
        ) : (
          <li className="live-classroom__chat-empty">
            Aún no hay mensajes. Inicia la conversación con tu grupo.
          </li>
        )}
      </ul>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          const value = message.trim();
          if (!value || isSending) return;
          void send(value).then(() => setMessage(''));
        }}
      >
        <label className="sr-only" htmlFor="live-class-message">
          Mensaje
        </label>
        <input
          autoComplete="off"
          id="live-class-message"
          maxLength={1000}
          onChange={(event) => setMessage(event.target.value)}
          placeholder="Escribe un mensaje…"
          value={message}
        />
        <button
          aria-label="Enviar mensaje"
          disabled={isSending || !message.trim()}
          type="submit"
        >
          <Send />
        </button>
      </form>
    </aside>
  );
}

function ParticipantPanel({
  sessionId,
  slug,
}: Readonly<{ sessionId: string; slug: string }>) {
  const participants = useParticipants();
  return (
    <aside className="live-classroom__participants" aria-label="Participantes">
      <h2>Participantes ({participants.length})</h2>
      <ul>
        {participants.map((participant) => (
          <li key={participant.identity}>
            <span>{participant.name || participant.identity}</span>
            {!participant.isLocal ? (
              <div>
                <button
                  type="button"
                  onClick={() =>
                    void changeParticipantPermissions(
                      slug,
                      sessionId,
                      participant.identity,
                      {
                        can_publish_audio: false,
                        can_publish_video: false,
                        can_share_screen: false,
                      },
                    )
                  }
                >
                  Silenciar
                </button>
                <button
                  type="button"
                  onClick={() =>
                    void removeParticipant(
                      slug,
                      sessionId,
                      participant.identity,
                    )
                  }
                >
                  Expulsar
                </button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </aside>
  );
}

function ParticipantGrid() {
  const tracks = useTracks([
    { source: Track.Source.Camera, withPlaceholder: true },
    { source: Track.Source.ScreenShare, withPlaceholder: false },
  ]);
  return (
    <GridLayout tracks={tracks} className="live-classroom__grid">
      <ParticipantTile />
    </GridLayout>
  );
}

function statusLabel(status: string) {
  return (
    (
      {
        scheduled: 'Programada',
        live: 'En vivo',
        ended: 'Finalizada',
        cancelled: 'Cancelada',
      } as Record<string, string>
    )[status] ?? status
  );
}

function LiveFact({
  icon,
  label,
  value,
}: Readonly<{ icon: ReactNode; label: string; value: string }>) {
  return (
    <div>
      {icon}
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function dateTimeLabel(value: string) {
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value));
}

function sessionDurationLabel(start: string, end: string) {
  const minutes = Math.max(
    0,
    Math.round((new Date(end).getTime() - new Date(start).getTime()) / 60_000),
  );
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

function entryActionLabel(detail: LiveSessionDetail, mayEnter: boolean) {
  if (detail.canStart) return 'Iniciar clase';
  if (detail.canJoin) return 'Entrar a clase';
  if (detail.status === 'ended') return 'Clase finalizada';
  if (detail.status === 'cancelled') return 'Clase cancelada';
  return mayEnter ? 'Entrar a clase' : 'Esperar apertura';
}

function waitingMessage(detail: LiveSessionDetail) {
  if (detail.status === 'ended') {
    return 'La clase ya finalizó. La asistencia registrada permanece vinculada al curso.';
  }
  if (detail.status === 'cancelled') {
    return 'La clase fue cancelada. El docente deberá programar una nueva sesión.';
  }
  return `El ingreso todavía no está habilitado. La sesión está programada para ${dateTimeLabel(detail.scheduledStart)}.`;
}
