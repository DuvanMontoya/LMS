'use client';

import {
  CarouselLayout,
  ChatEntry,
  ChatToggle,
  DisconnectButton,
  FocusLayout,
  FocusLayoutContainer,
  GridLayout,
  LayoutContextProvider,
  MediaDeviceMenu,
  ParticipantTile,
  RoomAudioRenderer,
  RoomContext,
  StartAudio,
  TrackToggle,
  formatChatMessageLinks,
  isTrackReference,
  useChat,
  useLayoutContext,
  useParticipants,
  useTracks,
} from '@livekit/components-react';
import {
  CalendarClock,
  ChevronDown,
  DoorOpen,
  LayoutGrid,
  Loader2,
  MessageCircle,
  MicOff,
  PanelsTopLeft,
  Presentation,
  Radio,
  Send,
  Timer,
  UserRound,
  Users,
  VideoOff,
  X,
} from 'lucide-react';
import { Room, RoomEvent, Track } from 'livekit-client';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
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
import {
  endLiveSession,
  enterLiveSession,
  changeParticipantPermissions,
  muteParticipantAudio,
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
  const [recordingLayout, setRecordingLayout] = useState<RecordingLayout>(
    isRecordingLayout(connection.session.recordingLayout)
      ? connection.session.recordingLayout
      : 'screen_share',
  );
  const [recordingResolution, setRecordingResolution] = useState<
    '720p' | '1080p'
  >(connection.session.recordingResolution === '720p' ? '720p' : '1080p');
  const [recordingBusy, setRecordingBusy] = useState(false);
  const [recordingError, setRecordingError] = useState('');
  const [participantsOpen, setParticipantsOpen] = useState(false);
  const [controlsHost, setControlsHost] = useState<HTMLElement | null>(null);
  const [deviceAvailability, setDeviceAvailability] = useState<{
    audio: boolean | null;
    video: boolean | null;
  }>({ audio: null, video: null });
  const recordingObservedRef = useRef(room.isRecording);
  const disconnectTimer = useRef<number | null>(null);

  useEffect(() => {
    let recordingSyncTimer: number | undefined;
    if (disconnectTimer.current !== null) {
      window.clearTimeout(disconnectTimer.current);
      disconnectTimer.current = null;
    }
    const onDisconnected = () => undefined;
    const syncRecordingStatus = () =>
      setRecordingStatus((current) => {
        const next = reconcileRecordingStatus(
          current,
          room.isRecording,
          recordingObservedRef.current,
        );
        recordingObservedRef.current = next.observed;
        return next.status;
      });
    const onRecordingStatusChanged = () => syncRecordingStatus();
    room.on(RoomEvent.Disconnected, onDisconnected);
    room.on(RoomEvent.RecordingStatusChanged, onRecordingStatusChanged);
    void (async () => {
      try {
        await room.connect(connection.serverUrl, connection.token);
        syncRecordingStatus();
        recordingSyncTimer = window.setInterval(syncRecordingStatus, 1_000);
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
      room.off(RoomEvent.RecordingStatusChanged, onRecordingStatusChanged);
      if (recordingSyncTimer !== undefined) {
        window.clearInterval(recordingSyncTimer);
      }
      disconnectTimer.current = window.setTimeout(() => {
        void room.disconnect();
        disconnectTimer.current = null;
      }, 0);
    };
  }, [connection.serverUrl, connection.token, room]);

  useEffect(() => {
    let mounted = true;
    const refreshDevices = async () => {
      try {
        const [audioDevices, videoDevices] = await Promise.all([
          Room.getLocalDevices('audioinput'),
          Room.getLocalDevices('videoinput'),
        ]);
        if (mounted) {
          setDeviceAvailability({
            audio: audioDevices.length > 0,
            video: videoDevices.length > 0,
          });
        }
      } catch {
        if (mounted) {
          setDeviceAvailability({ audio: false, video: false });
        }
      }
    };
    const onDevicesChanged = () => void refreshDevices();
    void refreshDevices();
    room.on(RoomEvent.MediaDevicesChanged, onDevicesChanged);
    return () => {
      mounted = false;
      room.off(RoomEvent.MediaDevicesChanged, onDevicesChanged);
    };
  }, [room]);

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

  const reportDeviceError = (kind: 'audio' | 'video', error: Error) => {
    setMediaError(mediaErrorMessage(error));
    if (
      error.name === 'NotFoundError' ||
      /requested device not found|device not found/i.test(error.message)
    ) {
      setDeviceAvailability((current) => ({ ...current, [kind]: false }));
    }
  };

  const controls = (
    <div className="live-classroom__controls" aria-label="Controles de clase">
      {connection.session.canPublishAudio ? (
        <div className="live-classroom__device-control">
          {deviceAvailability.audio === false ? (
            <button
              aria-label="No hay micrófono disponible"
              disabled
              title="Conecta un micrófono para activarlo"
              type="button"
            >
              <MicOff />
              <span>Micrófono</span>
            </button>
          ) : (
            <TrackToggle
              aria-label="Micrófono"
              onClick={() => setMediaError('')}
              onDeviceError={(error) => reportDeviceError('audio', error)}
              source={Track.Source.Microphone}
              title="Activar o silenciar micrófono"
            >
              <span>Micrófono</span>
            </TrackToggle>
          )}
          {deviceAvailability.audio ? (
            <MediaDeviceMenu
              aria-label="Elegir micrófono"
              kind="audioinput"
              title="Elegir micrófono"
            >
              <ChevronDown />
            </MediaDeviceMenu>
          ) : null}
        </div>
      ) : null}
      {connection.session.canPublishVideo ? (
        <div className="live-classroom__device-control">
          {deviceAvailability.video === false ? (
            <button
              aria-label="No hay cámara disponible"
              disabled
              title="Conecta una cámara para activarla"
              type="button"
            >
              <VideoOff />
              <span>Cámara</span>
            </button>
          ) : (
            <TrackToggle
              aria-label="Cámara"
              onClick={() => setMediaError('')}
              onDeviceError={(error) => reportDeviceError('video', error)}
              source={Track.Source.Camera}
              title="Activar o desactivar cámara"
            >
              <span>Cámara</span>
            </TrackToggle>
          )}
          {deviceAvailability.video ? (
            <MediaDeviceMenu
              aria-label="Elegir cámara"
              kind="videoinput"
              title="Elegir cámara"
            >
              <ChevronDown />
            </MediaDeviceMenu>
          ) : null}
        </div>
      ) : null}
      {connection.session.canShareScreen ? (
        <TrackToggle
          aria-label="Compartir pantalla"
          onClick={() => setMediaError('')}
          onDeviceError={(error) => setMediaError(mediaErrorMessage(error))}
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
      {connection.session.canModerate ? (
        <button
          aria-label="Abrir o cerrar participantes"
          aria-pressed={participantsOpen}
          onClick={() => setParticipantsOpen((current) => !current)}
          title="Participantes"
          type="button"
        >
          <Users />
          <span>Participantes</span>
        </button>
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
          {recordingError ? (
            <Alert variant="destructive">
              <AlertTitle>No fue posible controlar la grabación</AlertTitle>
              <AlertDescription>{recordingError}</AlertDescription>
            </Alert>
          ) : null}
          <ClassroomSurface
            chatEnabled={connection.session.chatEnabled}
            controls={controls}
            controlsHost={controlsHost}
            recordingControl={({ hasCamera, hasScreenShare }) =>
              connection.session.canModerate &&
              connection.session.recordingMode !== 'off' ? (
                <RecordingControl
                  busy={recordingBusy}
                  hasCamera={hasCamera}
                  hasScreenShare={hasScreenShare}
                  layout={recordingLayout}
                  onLayoutChange={setRecordingLayout}
                  onResolutionChange={setRecordingResolution}
                  onStart={async (layout, resolution) => {
                    setRecordingBusy(true);
                    setRecordingError('');
                    try {
                      const result = await startLiveRecording(
                        slug,
                        connection.session.id,
                        layout,
                        resolution,
                      );
                      setRecordingLayout(layout);
                      setRecordingResolution(resolution);
                      setRecordingStatus(result.status);
                      return true;
                    } catch (caught) {
                      setRecordingError(errorMessage(caught));
                      return false;
                    } finally {
                      setRecordingBusy(false);
                    }
                  }}
                  onStop={async () => {
                    setRecordingBusy(true);
                    setRecordingError('');
                    try {
                      const result = await stopLiveRecording(
                        slug,
                        connection.session.id,
                      );
                      setRecordingStatus(result.status);
                    } catch (caught) {
                      setRecordingError(errorMessage(caught));
                    } finally {
                      setRecordingBusy(false);
                    }
                  }}
                  resolution={recordingResolution}
                  status={recordingStatus}
                />
              ) : recordingStatus === 'active' ||
                recordingStatus === 'starting' ? (
                <span
                  aria-live="polite"
                  className="live-classroom__recording-indicator"
                  role="status"
                >
                  <Radio />
                  Grabando
                </span>
              ) : null
            }
          />
          {connection.session.canModerate && participantsOpen ? (
            <ParticipantPanel
              onClose={() => setParticipantsOpen(false)}
              sessionId={connection.session.id}
              slug={slug}
            />
          ) : null}
          <RoomAudioRenderer />
          <StartAudio label="Activar audio" />
        </section>
      </LayoutContextProvider>
    </RoomContext.Provider>
  );
}

export function RecordingControl({
  busy,
  hasCamera,
  hasScreenShare,
  layout,
  onLayoutChange,
  onResolutionChange,
  onStart,
  onStop,
  resolution,
  status,
}: Readonly<{
  busy: boolean;
  hasCamera: boolean;
  hasScreenShare: boolean;
  layout: RecordingLayout;
  onLayoutChange: (layout: RecordingLayout) => void;
  onResolutionChange: (resolution: '720p' | '1080p') => void;
  onStart: (
    layout: RecordingLayout,
    resolution: '720p' | '1080p',
  ) => Promise<boolean>;
  onStop: () => Promise<void>;
  resolution: '720p' | '1080p';
  status: string;
}>) {
  const [open, setOpen] = useState(false);
  const [draftLayout, setDraftLayout] = useState<RecordingLayout>(layout);
  const [draftResolution, setDraftResolution] = useState<'720p' | '1080p'>(
    resolution,
  );
  const active = status === 'active' || status === 'starting';
  const hasVisualTrack = hasCamera || hasScreenShare;

  function changeOpen(next: boolean) {
    if (next) {
      setDraftLayout(
        layout === 'screen_share' && !hasScreenShare ? 'grid' : layout,
      );
      setDraftResolution(resolution);
    }
    setOpen(next);
  }

  if (active) {
    return (
      <Button
        aria-label={`Detener grabación ${recordingLayoutLabel(layout)} en ${resolution}`}
        className="live-classroom__recording-active"
        disabled={busy}
        onClick={() => void onStop()}
        size="sm"
        type="button"
        variant="destructive"
      >
        {busy ? <Loader2 className="animate-spin" /> : <Radio />}
        <span>
          {status === 'starting' ? 'Iniciando' : 'Grabando'} · {resolution} ·{' '}
          {recordingLayoutShortLabel(layout)}
        </span>
      </Button>
    );
  }

  return (
    <Dialog onOpenChange={changeOpen} open={open}>
      <DialogTrigger asChild>
        <Button
          className="border-white/10 bg-white/6 text-slate-200 hover:bg-white/10 hover:text-white"
          size="sm"
          type="button"
          variant="outline"
        >
          <Radio />
          Grabar
        </Button>
      </DialogTrigger>
      <DialogContent className="border-slate-700 bg-slate-900 text-slate-100 sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Iniciar grabación</DialogTitle>
          <DialogDescription className="text-slate-400">
            Tú decides qué ve el archivo. El audio de la sala se mezcla en las
            tres composiciones y el chat queda fuera.
          </DialogDescription>
        </DialogHeader>

        <fieldset className="grid gap-2" disabled={busy}>
          <legend className="mb-1 text-xs font-semibold tracking-wide text-slate-400 uppercase">
            Composición
          </legend>
          <RecordingLayoutOption
            checked={draftLayout === 'screen_share'}
            description={
              hasScreenShare
                ? 'Sólo el contenido compartido; nunca muestra las cámaras.'
                : 'Disponible cuando empieces a compartir una pantalla.'
            }
            disabled={!hasScreenShare}
            icon={<Presentation />}
            label="Pantalla compartida sola"
            onSelect={() => setDraftLayout('screen_share')}
          />
          <RecordingLayoutOption
            checked={draftLayout === 'speaker'}
            description="Enfoca automáticamente la presentación o a quien está hablando y conserva a los demás."
            icon={<PanelsTopLeft />}
            label="Enfoque automático"
            disabled={!hasVisualTrack}
            onSelect={() => setDraftLayout('speaker')}
          />
          <RecordingLayoutOption
            checked={draftLayout === 'grid'}
            description="Muestra las cámaras publicadas en un mosaico equilibrado."
            icon={<LayoutGrid />}
            label="Mosaico de participantes"
            disabled={!hasVisualTrack}
            onSelect={() => setDraftLayout('grid')}
          />
        </fieldset>

        {!hasVisualTrack ? (
          <p className="text-xs leading-relaxed text-slate-400">
            Activa una cámara o comparte una pantalla para que la grabación
            tenga una fuente visual real.
          </p>
        ) : null}

        <fieldset className="grid gap-2" disabled={busy}>
          <legend className="mb-1 text-xs font-semibold tracking-wide text-slate-400 uppercase">
            Calidad
          </legend>
          <div className="grid grid-cols-2 rounded-lg bg-slate-950 p-1">
            {(['1080p', '720p'] as const).map((value) => (
              <label
                className="cursor-pointer rounded-md px-3 py-2 text-center text-sm font-semibold transition-colors has-checked:bg-slate-700 has-checked:text-white"
                key={value}
              >
                <input
                  checked={draftResolution === value}
                  className="sr-only"
                  name="recording-resolution"
                  onChange={() => setDraftResolution(value)}
                  type="radio"
                  value={value}
                />
                {value === '1080p' ? '1080p · Full HD' : '720p · HD'}
              </label>
            ))}
          </div>
        </fieldset>

        <p className="rounded-lg border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-xs leading-relaxed text-amber-100">
          Al iniciar, todos los participantes verán el indicador de grabación.
          Puedes detenerla y comenzar otra con una composición diferente.
        </p>

        <DialogFooter className="border-slate-700 bg-slate-950/60">
          <Button
            disabled={
              busy ||
              !hasVisualTrack ||
              (draftLayout === 'screen_share' && !hasScreenShare)
            }
            onClick={() =>
              void onStart(draftLayout, draftResolution).then((started) => {
                if (!started) return;
                onLayoutChange(draftLayout);
                onResolutionChange(draftResolution);
                setOpen(false);
              })
            }
            type="button"
          >
            {busy ? <Loader2 className="animate-spin" /> : <Radio />}
            Iniciar grabación
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RecordingLayoutOption({
  checked,
  description,
  disabled = false,
  icon,
  label,
  onSelect,
}: Readonly<{
  checked: boolean;
  description: string;
  disabled?: boolean;
  icon: ReactNode;
  label: string;
  onSelect: () => void;
}>) {
  return (
    <label className="group grid cursor-pointer grid-cols-[2.25rem_1fr_1rem] items-center gap-3 rounded-lg border border-slate-700 bg-slate-950/60 p-3 transition-colors has-checked:border-sky-400 has-checked:bg-sky-400/10 has-disabled:cursor-not-allowed has-disabled:opacity-45">
      <span className="grid size-9 place-items-center rounded-md bg-slate-800 text-slate-300 group-has-checked:bg-sky-400/15 group-has-checked:text-sky-300">
        {icon}
      </span>
      <span>
        <strong className="block text-sm">{label}</strong>
        <small className="mt-0.5 block leading-snug text-slate-400">
          {description}
        </small>
      </span>
      <input
        checked={checked}
        disabled={disabled}
        name="recording-layout"
        onChange={onSelect}
        type="radio"
        value={label}
      />
    </label>
  );
}

type ClassroomLayoutMode = 'auto' | 'grid' | 'presentation';
type RecordingLayout = 'grid' | 'screen_share' | 'speaker';
type RecordingAvailability = { hasCamera: boolean; hasScreenShare: boolean };

export function reconcileRecordingStatus(
  current: string,
  isRecording: boolean,
  observed: boolean,
): { observed: boolean; status: string } {
  if (isRecording) return { observed: true, status: 'active' };
  if (!observed) return { observed: false, status: current };
  return {
    observed: false,
    status: current === 'active' || current === 'starting' ? 'ended' : current,
  };
}

function ClassroomSurface({
  chatEnabled,
  controls,
  controlsHost,
  recordingControl,
}: Readonly<{
  chatEnabled: boolean;
  controls: ReactNode;
  controlsHost: HTMLElement | null;
  recordingControl: (availability: RecordingAvailability) => ReactNode;
}>) {
  const layout = useLayoutContext();
  const chatOpen = Boolean(layout.widget.state?.showChat);
  const [layoutMode, setLayoutMode] = useState<ClassroomLayoutMode>('auto');
  const cameraTracks = useTracks([
    { source: Track.Source.Camera, withPlaceholder: true },
  ]);
  const screenShareTracks = useTracks([
    { source: Track.Source.ScreenShare, withPlaceholder: false },
  ]);
  const hasScreenShare = screenShareTracks.length > 0;
  const hasCamera = cameraTracks.some(isTrackReference);
  const effectiveLayout =
    layoutMode === 'auto' ? (hasScreenShare ? 'focus' : 'grid') : layoutMode;
  const headerControls = (
    <div className="live-classroom__header-controls">
      <div
        aria-label="Distribución del aula"
        className="live-classroom__layout-switcher"
        role="group"
      >
        <LayoutButton
          active={layoutMode === 'auto'}
          icon={<PanelsTopLeft />}
          label="Automática"
          onClick={() => setLayoutMode('auto')}
        />
        <LayoutButton
          active={layoutMode === 'presentation'}
          disabled={!hasScreenShare}
          icon={<Presentation />}
          label="Sólo presentación"
          onClick={() => setLayoutMode('presentation')}
        />
        <LayoutButton
          active={layoutMode === 'grid'}
          icon={<LayoutGrid />}
          label="Mosaico"
          onClick={() => setLayoutMode('grid')}
        />
      </div>
      {recordingControl({ hasCamera, hasScreenShare })}
      {controls}
    </div>
  );
  return (
    <>
      <div
        className="live-classroom__surface"
        data-chat-open={chatOpen}
        data-layout={effectiveLayout}
      >
        <ClassroomStage
          cameraTracks={cameraTracks}
          layout={effectiveLayout}
          screenShareTracks={screenShareTracks}
        />
        {chatEnabled && chatOpen ? <ClassroomChat /> : null}
      </div>
      {controlsHost
        ? createPortal(headerControls, controlsHost)
        : headerControls}
    </>
  );
}

function LayoutButton({
  active,
  disabled = false,
  icon,
  label,
  onClick,
}: Readonly<{
  active: boolean;
  disabled?: boolean;
  icon: ReactNode;
  label: string;
  onClick: () => void;
}>) {
  return (
    <button
      aria-label={label}
      aria-pressed={active}
      disabled={disabled}
      onClick={onClick}
      title={disabled ? 'Comparte una pantalla para usar esta vista' : label}
      type="button"
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function ClassroomStage({
  cameraTracks,
  layout,
  screenShareTracks,
}: Readonly<{
  cameraTracks: ReturnType<typeof useTracks>;
  layout: 'focus' | 'grid' | 'presentation';
  screenShareTracks: ReturnType<typeof useTracks>;
}>) {
  const screenShare = screenShareTracks[0];
  if (layout === 'presentation' && screenShare) {
    return (
      <FocusLayout
        className="live-classroom__presentation"
        trackRef={screenShare}
      />
    );
  }
  if (layout === 'focus' && screenShare) {
    return (
      <FocusLayoutContainer className="live-classroom__focus-layout">
        <CarouselLayout
          className="live-classroom__carousel"
          orientation="vertical"
          tracks={cameraTracks}
        >
          <ParticipantTile />
        </CarouselLayout>
        <FocusLayout trackRef={screenShare} />
      </FocusLayoutContainer>
    );
  }
  return (
    <GridLayout tracks={cameraTracks} className="live-classroom__grid">
      <ParticipantTile />
    </GridLayout>
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
  onClose,
  sessionId,
  slug,
}: Readonly<{ onClose: () => void; sessionId: string; slug: string }>) {
  const participants = useParticipants();
  const [busyIdentity, setBusyIdentity] = useState('');
  const [removeIdentity, setRemoveIdentity] = useState('');
  const [panelError, setPanelError] = useState('');

  async function run(identity: string, operation: () => Promise<unknown>) {
    setBusyIdentity(identity);
    setPanelError('');
    try {
      await operation();
    } catch (caught) {
      setPanelError(errorMessage(caught));
    } finally {
      setBusyIdentity('');
    }
  }

  return (
    <aside className="live-classroom__participants" aria-label="Participantes">
      <header>
        <h2>Participantes ({participants.length})</h2>
        <button
          aria-label="Cerrar participantes"
          onClick={onClose}
          type="button"
        >
          <X />
        </button>
      </header>
      {panelError ? <p role="alert">{panelError}</p> : null}
      <ul>
        {participants.map((participant) => {
          const restricted = participant.permissions?.canPublish === false;
          const microphone = participant.getTrackPublication(
            Track.Source.Microphone,
          );
          const busy = busyIdentity === participant.identity;
          return (
            <li key={participant.identity}>
              <span>{participant.name || 'Participante'}</span>
              {!participant.isLocal ? (
                <div>
                  <button
                    disabled={busy || !microphone || microphone.isMuted}
                    onClick={() =>
                      void run(participant.identity, () =>
                        muteParticipantAudio(
                          slug,
                          sessionId,
                          participant.identity,
                        ),
                      )
                    }
                    type="button"
                  >
                    Silenciar micrófono
                  </button>
                  <button
                    disabled={busy}
                    onClick={() =>
                      void run(participant.identity, () =>
                        changeParticipantPermissions(
                          slug,
                          sessionId,
                          participant.identity,
                          {
                            can_publish_audio: restricted,
                            can_publish_video: restricted,
                            can_share_screen: restricted,
                          },
                        ),
                      )
                    }
                    type="button"
                  >
                    {restricted ? 'Permitir medios' : 'Restringir medios'}
                  </button>
                  {removeIdentity === participant.identity ? (
                    <>
                      <button
                        disabled={busy}
                        onClick={() => setRemoveIdentity('')}
                        type="button"
                      >
                        Cancelar
                      </button>
                      <button
                        className="live-classroom__participant-remove"
                        disabled={busy}
                        onClick={() =>
                          void run(participant.identity, () =>
                            removeParticipant(
                              slug,
                              sessionId,
                              participant.identity,
                            ),
                          ).finally(() => setRemoveIdentity(''))
                        }
                        type="button"
                      >
                        Confirmar expulsión
                      </button>
                    </>
                  ) : (
                    <button
                      className="live-classroom__participant-remove"
                      disabled={busy}
                      onClick={() => setRemoveIdentity(participant.identity)}
                      type="button"
                    >
                      Expulsar
                    </button>
                  )}
                </div>
              ) : null}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

function mediaErrorMessage(error: Error) {
  if (
    error.name === 'NotFoundError' ||
    /requested device not found|device not found/i.test(error.message)
  ) {
    return 'No se encontró el dispositivo. Conéctalo y vuelve a intentarlo; el aula lo detectará automáticamente.';
  }
  if (
    error.name === 'NotAllowedError' ||
    /permission|not allowed|denied/i.test(error.message)
  ) {
    return 'Chrome bloqueó el permiso del dispositivo. Habilítalo para este sitio desde la barra de direcciones.';
  }
  return (
    error.message ||
    'No fue posible activar el dispositivo. Revisa su conexión y vuelve a intentarlo.'
  );
}

function isRecordingLayout(value: string): value is RecordingLayout {
  return ['grid', 'screen_share', 'speaker'].includes(value);
}

function recordingLayoutLabel(layout: RecordingLayout) {
  if (layout === 'screen_share') return 'sólo de la pantalla compartida';
  if (layout === 'grid') return 'en mosaico';
  return 'del participante activo';
}

function recordingLayoutShortLabel(layout: RecordingLayout) {
  if (layout === 'screen_share') return 'Pantalla';
  if (layout === 'grid') return 'Mosaico';
  return 'Enfoque';
}

function errorMessage(caught: unknown) {
  return caught instanceof Error
    ? caught.message
    : 'LiveKit no pudo completar la operación solicitada.';
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
