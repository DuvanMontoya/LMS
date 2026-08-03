'use client';

import {
  RoomAudioRenderer,
  RoomContext,
  VideoTrack,
  isTrackReference,
  useTracks,
} from '@livekit/components-react';
import { ConnectionState, Room, RoomEvent, Track } from 'livekit-client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

type EgressCredentials = { serverUrl: string; token: string };

export function ScreenShareEgress() {
  const room = useMemo(
    () => new Room({ adaptiveStream: false, dynacast: false }),
    [],
  );
  const [ready, setReady] = useState(false);
  const [error, setError] = useState('');
  const recordingStarted = useRef(false);

  const startRecording = useCallback(() => {
    if (recordingStarted.current) return;
    recordingStarted.current = true;
    console.log('START_RECORDING');
  }, []);

  useEffect(() => {
    const credentials = readEgressCredentials();
    if (!credentials) {
      queueMicrotask(() => setError('Faltan credenciales de Egress válidas.'));
      return;
    }
    window.history.replaceState(null, '', window.location.pathname);
    let disposed = false;

    const endRecording = () => {
      if (!recordingStarted.current) return;
      console.log('END_RECORDING');
      recordingStarted.current = false;
    };
    const onDisconnected = () => {
      endRecording();
      if (!disposed) setReady(false);
    };
    room.on(RoomEvent.Disconnected, onDisconnected);

    void room
      .connect(credentials.serverUrl, credentials.token, {
        autoSubscribe: true,
      })
      .then(() => {
        if (disposed) return;
        setReady(true);
        startRecording();
      })
      .catch((caught: unknown) => {
        if (disposed) return;
        setError(
          caught instanceof Error
            ? caught.message
            : 'No fue posible conectar la plantilla de grabación.',
        );
      });

    return () => {
      disposed = true;
      room.off(RoomEvent.Disconnected, onDisconnected);
      endRecording();
      void room.disconnect();
    };
  }, [room, startRecording]);

  return (
    <main className="screen-share-egress" data-lk-theme="default">
      {error ? <p role="alert">{error}</p> : null}
      <RoomContext.Provider value={room}>
        {ready ? <ScreenShareRecordingSurface room={room} /> : null}
      </RoomContext.Provider>
    </main>
  );
}

function ScreenShareRecordingSurface({ room }: Readonly<{ room: Room }>) {
  const tracks = useTracks(
    [{ source: Track.Source.ScreenShare, withPlaceholder: false }],
    { onlySubscribed: true },
  );
  if (room.state === ConnectionState.Disconnected) return null;
  const screenShareTrack = tracks.find(isTrackReference);
  return (
    <>
      {screenShareTrack ? (
        <VideoTrack
          className="screen-share-egress__video"
          trackRef={screenShareTrack}
        />
      ) : (
        <div className="screen-share-egress__waiting">
          Esperando una pantalla compartida…
        </div>
      )}
      <RoomAudioRenderer room={room} />
    </>
  );
}

function readEgressCredentials(): EgressCredentials | null {
  const search = new URLSearchParams(window.location.search);
  const serverUrl = search.get('url') ?? '';
  const token = search.get('token') ?? '';
  if (!token || token.length > 8_192) return null;
  try {
    const parsed = new URL(serverUrl);
    if (!['ws:', 'wss:', 'http:', 'https:'].includes(parsed.protocol)) {
      return null;
    }
    return { serverUrl: parsed.toString(), token };
  } catch {
    return null;
  }
}
