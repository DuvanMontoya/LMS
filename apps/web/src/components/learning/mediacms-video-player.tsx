'use client';

import { useEffect, useRef, useState } from 'react';

import type Hls from 'hls.js';

/** A native LMS video surface; MediaCMS remains an authorization/data plane. */
export function MediaCMSVideoPlayer({
  enrollmentId,
  slug,
  unitId,
}: Readonly<{
  enrollmentId: string;
  slug: string;
  unitId: string;
}>) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [failed, setFailed] = useState(false);
  const source = `/api/v1/organizations/${encodeURIComponent(slug)}/learning/me/enrollments/${encodeURIComponent(enrollmentId)}/units/${encodeURIComponent(unitId)}/mediacms-stream/`;

  useEffect(() => {
    let hls: Hls | null = null;
    let active = true;
    const video = videoRef.current as HTMLVideoElement;
    if (!video) return;

    async function attach() {
      try {
        if (video.canPlayType('application/vnd.apple.mpegurl')) {
          video.src = source;
          return;
        }
        const { default: HlsClient } = await import('hls.js');
        if (!active || !HlsClient.isSupported()) {
          if (active) setFailed(true);
          return;
        }
        hls = new HlsClient({
          backBufferLength: 30,
          capLevelToPlayerSize: true,
          enableWorker: true,
          lowLatencyMode: false,
          maxBufferLength: 30,
        });
        hls.on(HlsClient.Events.ERROR, (_event, data) => {
          if (!data.fatal) return;
          if (data.type === HlsClient.ErrorTypes.NETWORK_ERROR) {
            hls?.startLoad();
          } else if (data.type === HlsClient.ErrorTypes.MEDIA_ERROR) {
            hls?.recoverMediaError();
          } else {
            setFailed(true);
          }
        });
        hls.loadSource(source);
        hls.attachMedia(video);
      } catch {
        if (active) setFailed(true);
      }
    }

    void attach();
    return () => {
      active = false;
      hls?.destroy();
    };
  }, [source]);

  return (
    <section aria-label="Vídeo de la lección" className="learning-native-video">
      <video
        className="aspect-video w-full bg-black"
        controls
        controlsList="nodownload"
        onError={() => setFailed(true)}
        playsInline
        preload="metadata"
        ref={videoRef}
      />
      {failed ? (
        <p className="mt-3 text-sm text-destructive" role="alert">
          No fue posible reproducir este vídeo.
        </p>
      ) : null}
    </section>
  );
}
