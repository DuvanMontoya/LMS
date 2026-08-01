'use client';

import {
  DisconnectButton,
  GridLayout,
  ParticipantTile,
  RoomAudioRenderer,
  RoomContext,
  StartAudio,
  TrackToggle,
  useParticipants,
  useTracks,
} from '@livekit/components-react';
import {
  Camera,
  CameraOff,
  DoorOpen,
  Loader2,
  Mic,
  MonitorUp,
} from 'lucide-react';
import { Room, RoomEvent, Track } from 'livekit-client';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import {
  endLiveSession,
  enterLiveSession,
  changeParticipantPermissions,
  removeParticipant,
  type LiveConnection,
} from '@/lib/scheduling/api';
import type { LiveSessionDetail } from '@/lib/scheduling/server';

type DeviceOption = { deviceId: string; label: string };

export function LiveClassroom({
  detail,
  slug,
}: Readonly<{ detail: LiveSessionDetail; slug: string }>) {
  const [connection, setConnection] = useState<LiveConnection | null>(null);
  const [devices, setDevices] = useState<{
    audio: DeviceOption[];
    video: DeviceOption[];
  }>({ audio: [], video: [] });
  const [audioDeviceId, setAudioDeviceId] = useState('');
  const [videoDeviceId, setVideoDeviceId] = useState('');
  const [permission, setPermission] = useState<
    'idle' | 'checking' | 'ready' | 'denied'
  >('idle');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    if (detail.status !== 'scheduled' || detail.canStart) return;
    const interval = window.setInterval(() => router.refresh(), 15_000);
    return () => window.clearInterval(interval);
  }, [detail.canStart, detail.status, router]);

  async function inspectDevices() {
    setPermission('checking');
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: true,
      });
      stream.getTracks().forEach((track) => track.stop());
      const available = await navigator.mediaDevices.enumerateDevices();
      const audio = available.filter((device) => device.kind === 'audioinput');
      const video = available.filter((device) => device.kind === 'videoinput');
      setDevices({ audio, video });
      setAudioDeviceId(audio[0]?.deviceId ?? '');
      setVideoDeviceId(video[0]?.deviceId ?? '');
      setPermission('ready');
    } catch {
      setPermission('denied');
    }
  }

  async function enter() {
    setBusy(true);
    setError('');
    try {
      const action = detail.canStart ? 'start' : 'join';
      setConnection(await enterLiveSession(slug, detail.id, action));
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
      <ConnectedClassroom
        audioDeviceId={audioDeviceId}
        connection={connection}
        slug={slug}
        onEnd={
          detail.canModerate ? () => endLiveSession(slug, detail.id) : undefined
        }
        videoDeviceId={videoDeviceId}
      />
    );
  }

  const mayEnter = detail.canStart || detail.canJoin;
  return (
    <section className="live-lobby">
      <div
        className="live-lobby__preview"
        aria-label="Vista previa de dispositivos"
      >
        {permission === 'ready' ? (
          <Camera className="size-10" />
        ) : (
          <CameraOff className="size-10" />
        )}
        <p>
          {permission === 'ready'
            ? 'Cámara y micrófono disponibles'
            : 'Prueba tus dispositivos antes de entrar'}
        </p>
      </div>
      <div className="live-lobby__panel">
        <span className="live-status" data-status={detail.status}>
          {statusLabel(detail.status)}
        </span>
        <h2>Antes de entrar</h2>
        <p>
          El token de acceso se solicita sólo cuando confirmas la entrada y
          nunca se guarda en el navegador.
        </p>
        {error ? (
          <Alert variant="destructive">
            <AlertTitle>No fue posible entrar</AlertTitle>
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        ) : null}
        {permission === 'denied' ? (
          <Alert>
            <AlertTitle>Permiso no concedido</AlertTitle>
            <AlertDescription>
              Puedes revisar la configuración del navegador y volver a probar.
            </AlertDescription>
          </Alert>
        ) : null}
        <div className="grid gap-3">
          <Label>
            Micrófono
            <select
              className="academic-select"
              value={audioDeviceId}
              onChange={(event) => setAudioDeviceId(event.target.value)}
            >
              {devices.audio.map((device, index) => (
                <option key={device.deviceId} value={device.deviceId}>
                  {device.label || `Micrófono ${index + 1}`}
                </option>
              ))}
            </select>
          </Label>
          <Label>
            Cámara
            <select
              className="academic-select"
              value={videoDeviceId}
              onChange={(event) => setVideoDeviceId(event.target.value)}
            >
              {devices.video.map((device, index) => (
                <option key={device.deviceId} value={device.deviceId}>
                  {device.label || `Cámara ${index + 1}`}
                </option>
              ))}
            </select>
          </Label>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="outline"
            onClick={() => void inspectDevices()}
            disabled={permission === 'checking'}
          >
            {permission === 'checking' ? (
              <Loader2 className="animate-spin" />
            ) : (
              <Mic />
            )}{' '}
            Probar dispositivos
          </Button>
          <Button
            type="button"
            onClick={() => void enter()}
            disabled={!mayEnter || busy}
          >
            {busy ? <Loader2 className="animate-spin" /> : <DoorOpen />}{' '}
            {detail.canStart ? 'Iniciar clase' : 'Entrar a clase'}
          </Button>
        </div>
        {!mayEnter ? (
          <p className="text-sm text-muted-foreground">
            La clase aún no está disponible o está fuera de su ventana de
            acceso.
          </p>
        ) : null}
      </div>
    </section>
  );
}

function ConnectedClassroom({
  audioDeviceId,
  connection,
  onEnd,
  slug,
  videoDeviceId,
}: Readonly<{
  audioDeviceId: string;
  connection: LiveConnection;
  onEnd?: (() => Promise<unknown>) | undefined;
  slug: string;
  videoDeviceId: string;
}>) {
  const room = useMemo(
    () => new Room({ adaptiveStream: true, dynacast: true }),
    [],
  );
  const [connectionError, setConnectionError] = useState('');

  useEffect(() => {
    const onDisconnected = () => undefined;
    room.on(RoomEvent.Disconnected, onDisconnected);
    void room
      .connect(connection.serverUrl, connection.token)
      .then(async () => {
        await Promise.all([
          room.localParticipant.setMicrophoneEnabled(
            true,
            audioDeviceId ? { deviceId: audioDeviceId } : undefined,
          ),
          room.localParticipant.setCameraEnabled(
            true,
            videoDeviceId ? { deviceId: videoDeviceId } : undefined,
          ),
        ]);
      })
      .catch((caught: unknown) =>
        setConnectionError(
          caught instanceof Error
            ? caught.message
            : 'No fue posible conectar con LiveKit.',
        ),
      );
    return () => {
      room.off(RoomEvent.Disconnected, onDisconnected);
      void room.disconnect();
    };
  }, [
    audioDeviceId,
    connection.serverUrl,
    connection.token,
    room,
    videoDeviceId,
  ]);

  return (
    <RoomContext.Provider value={room}>
      <section className="live-classroom" data-lk-theme="default">
        {connectionError ? (
          <Alert variant="destructive">
            <AlertTitle>Conexión interrumpida</AlertTitle>
            <AlertDescription>{connectionError}</AlertDescription>
          </Alert>
        ) : null}
        <ParticipantGrid />
        {connection.session.canModerate ? (
          <ParticipantPanel sessionId={connection.session.id} slug={slug} />
        ) : null}
        <RoomAudioRenderer />
        <StartAudio label="Activar audio" />
        <div
          className="live-classroom__controls"
          aria-label="Controles de clase"
        >
          <TrackToggle source={Track.Source.Microphone}>
            <Mic />
            <span>Micrófono</span>
          </TrackToggle>
          <TrackToggle source={Track.Source.Camera}>
            <Camera />
            <span>Cámara</span>
          </TrackToggle>
          {connection.session.canShareScreen ? (
            <TrackToggle source={Track.Source.ScreenShare}>
              <MonitorUp />
              <span>Compartir pantalla</span>
            </TrackToggle>
          ) : null}
          <DisconnectButton onClick={() => onEnd && void onEnd()}>
            <DoorOpen />
            <span>Salir</span>
          </DisconnectButton>
        </div>
      </section>
    </RoomContext.Provider>
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
