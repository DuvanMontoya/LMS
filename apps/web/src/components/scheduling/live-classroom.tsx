'use client';

import {
  Chat,
  ChatToggle,
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
  Radio,
} from 'lucide-react';
import { Room, RoomEvent, Track } from 'livekit-client';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef, useState } from 'react';

import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
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
  const [recordingAcknowledged, setRecordingAcknowledged] = useState(false);
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
        audio: detail.canPublishAudio,
        video: detail.canPublishVideo,
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
  const recordingEnabled = detail.recordingMode !== 'off';
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
        {recordingEnabled ? (
          <Alert className="border-amber-600/30 bg-amber-500/10">
            <AlertTitle>Esta clase puede ser grabada</AlertTitle>
            <AlertDescription>
              La grabación es privada y su estado se muestra dentro de la sala.
              El chat es efímero y no forma parte de un historial académico.
            </AlertDescription>
          </Alert>
        ) : null}
        <div className="grid gap-3">
          {detail.canPublishAudio ? (
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
          ) : null}
          {detail.canPublishVideo ? (
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
          ) : null}
        </div>
        {recordingEnabled ? (
          <label className="flex items-start gap-2 rounded-lg border p-3 text-sm">
            <input
              className="mt-1"
              checked={recordingAcknowledged}
              onChange={(event) =>
                setRecordingAcknowledged(event.target.checked)
              }
              type="checkbox"
            />
            <span>
              Entiendo que la sesión puede grabarse y que veré un indicador
              cuando la grabación esté activa.
            </span>
          </label>
        ) : null}
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
            disabled={
              !mayEnter || busy || (recordingEnabled && !recordingAcknowledged)
            }
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
  const [mediaError, setMediaError] = useState('');
  const [recordingStatus, setRecordingStatus] = useState(
    connection.session.recordingStatus,
  );
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
        return;
      }
      try {
        const tracks: Promise<unknown>[] = [];
        if (audioDeviceId && connection.session.canPublishAudio) {
          tracks.push(
            room.localParticipant.setMicrophoneEnabled(true, {
              deviceId: audioDeviceId,
            }),
          );
        }
        if (videoDeviceId && connection.session.canPublishVideo) {
          tracks.push(
            room.localParticipant.setCameraEnabled(true, {
              deviceId: videoDeviceId,
            }),
          );
        }
        await Promise.all(tracks);
      } catch {
        setMediaError(
          'Entraste a la sala, pero Chrome no permitió activar cámara o micrófono.',
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
              Grabación {recordingStatus === 'active' ? 'activa' : 'iniciando'}
            </AlertTitle>
            <AlertDescription>
              LiveKit Egress está componiendo esta sala en un archivo privado.
            </AlertDescription>
          </Alert>
        ) : null}
        <ParticipantGrid />
        {connection.session.chatEnabled ? <Chat /> : null}
        {connection.session.canModerate ? (
          <ParticipantPanel sessionId={connection.session.id} slug={slug} />
        ) : null}
        <RoomAudioRenderer />
        <StartAudio label="Activar audio" />
        <div
          className="live-classroom__controls"
          aria-label="Controles de clase"
        >
          {connection.session.canPublishAudio ? (
            <TrackToggle source={Track.Source.Microphone}>
              <Mic />
              <span>Micrófono</span>
            </TrackToggle>
          ) : null}
          {connection.session.canPublishVideo ? (
            <TrackToggle source={Track.Source.Camera}>
              <Camera />
              <span>Cámara</span>
            </TrackToggle>
          ) : null}
          {connection.session.canShareScreen ? (
            <TrackToggle source={Track.Source.ScreenShare}>
              <MonitorUp />
              <span>Compartir pantalla</span>
            </TrackToggle>
          ) : null}
          {connection.session.chatEnabled ? (
            <ChatToggle>Chat</ChatToggle>
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
