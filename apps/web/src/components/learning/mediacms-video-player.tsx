'use client';

import { Maximize2, MonitorUp, Minimize2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import type Hls from 'hls.js';

import { Button } from '@/components/ui/button';

type PlayerSize = 'normal' | 'wide' | 'full';

type QualityOption = {
  id: number;
  label: string;
};

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
  const hlsRef = useRef<Hls | null>(null);
  const [failed, setFailed] = useState(false);
  const [playerSize, setPlayerSize] = useState<PlayerSize>('normal');
  const [qualityOptions, setQualityOptions] = useState<QualityOption[]>([]);
  const [selectedQuality, setSelectedQuality] = useState('unavailable');
  const [qualityDescription, setQualityDescription] = useState(
    'Detectando las resoluciones disponibles.',
  );
  const source = `/api/v1/organizations/${encodeURIComponent(slug)}/learning/me/enrollments/${encodeURIComponent(enrollmentId)}/units/${encodeURIComponent(unitId)}/mediacms-stream/`;

  useEffect(() => {
    let hls: Hls | null = null;
    let active = true;
    const video = videoRef.current as HTMLVideoElement;
    if (!video) return;
    setFailed(false);
    setQualityOptions([]);
    setSelectedQuality('unavailable');
    setQualityDescription('Detectando las resoluciones disponibles.');

    async function attach() {
      try {
        const { default: HlsClient } = await import('hls.js');
        if (!active) return;
        if (!HlsClient.isSupported()) {
          if (video.canPlayType('application/vnd.apple.mpegurl')) {
            video.src = source;
            setQualityDescription(
              'Este navegador selecciona automáticamente la resolución HLS.',
            );
            return;
          }
          setFailed(true);
          return;
        }
        const hlsClient = new HlsClient({
          backBufferLength: 30,
          capLevelToPlayerSize: false,
          enableWorker: true,
          lowLatencyMode: false,
          maxBufferLength: 30,
        });
        hls = hlsClient;
        hlsRef.current = hlsClient;
        hlsClient.on(HlsClient.Events.MANIFEST_PARSED, (_event, data) => {
          if (!active) return;
          const options = data.levels
            .map((level, id) => ({
              id,
              height: level.height,
              bitrate: level.bitrate,
            }))
            .filter(
              (
                level,
              ): level is { bitrate: number; height: number; id: number } =>
                typeof level.height === 'number' && level.height > 0,
            )
            .sort((left, right) =>
              left.height === right.height
                ? right.bitrate - left.bitrate
                : right.height - left.height,
            )
            .filter(
              (level, index, levels) =>
                levels.findIndex(
                  (candidate) => candidate.height === level.height,
                ) === index,
            )
            .sort((left, right) => right.height - left.height)
            .map(({ height, id }) => ({ id, label: `${height}p` }));
          setQualityOptions(options);

          if (options.length <= 1) {
            setSelectedQuality(
              options[0] ? String(options[0].id) : 'unavailable',
            );
            setQualityDescription(
              options[0]
                ? `Única resolución disponible: ${options[0].label}.`
                : 'El manifiesto no informó resoluciones seleccionables.',
            );
            return;
          }

          const preferred1080p = options.find(
            (option) => option.label === '1080p',
          );
          if (preferred1080p) {
            hlsClient.startLevel = preferred1080p.id;
            hlsClient.currentLevel = preferred1080p.id;
            hlsClient.nextLevel = preferred1080p.id;
            setSelectedQuality(String(preferred1080p.id));
            setQualityDescription(
              '1080p es la resolución inicial porque está disponible.',
            );
            return;
          }

          hlsClient.startLevel = -1;
          setSelectedQuality('auto');
          setQualityDescription(
            'Resolución automática según la conexión; puedes elegir una disponible.',
          );
        });
        hlsClient.on(HlsClient.Events.ERROR, (_event, data) => {
          if (!data.fatal) return;
          if (data.type === HlsClient.ErrorTypes.NETWORK_ERROR) {
            hls?.startLoad();
          } else if (data.type === HlsClient.ErrorTypes.MEDIA_ERROR) {
            hls?.recoverMediaError();
          } else {
            setFailed(true);
          }
        });
        hlsClient.loadSource(source);
        hlsClient.attachMedia(video);
      } catch {
        if (active) setFailed(true);
      }
    }

    void attach();
    return () => {
      active = false;
      hls?.destroy();
      if (hlsRef.current === hls) hlsRef.current = null;
    };
  }, [source]);

  function changeQuality(value: string) {
    const hls = hlsRef.current;
    if (!hls) return;
    if (value === 'auto') {
      hls.currentLevel = -1;
      hls.nextLevel = -1;
      setSelectedQuality(value);
      setQualityDescription('Resolución automática según la conexión.');
      return;
    }
    const level = Number(value);
    if (
      !Number.isInteger(level) ||
      !qualityOptions.some((option) => option.id === level)
    ) {
      return;
    }
    hls.currentLevel = level;
    hls.nextLevel = level;
    setSelectedQuality(value);
    const label = qualityOptions.find((option) => option.id === level)?.label;
    setQualityDescription(
      `Resolución fijada en ${label ?? 'la opción seleccionada'}.`,
    );
  }

  return (
    <section
      aria-label="Vídeo de la lección"
      className="learning-native-video"
      data-size={playerSize}
    >
      <video
        className="aspect-video w-full bg-black"
        controls
        controlsList="nodownload"
        onError={() => setFailed(true)}
        playsInline
        preload="metadata"
        ref={videoRef}
      />
      <div className="learning-native-video__settings">
        <fieldset aria-label="Tamaño del reproductor">
          <legend>Tamaño</legend>
          <div>
            <Button
              aria-pressed={playerSize === 'normal'}
              onClick={() => setPlayerSize('normal')}
              size="sm"
              type="button"
              variant={playerSize === 'normal' ? 'secondary' : 'ghost'}
            >
              <Minimize2 />
              Normal
            </Button>
            <Button
              aria-pressed={playerSize === 'wide'}
              onClick={() => setPlayerSize('wide')}
              size="sm"
              type="button"
              variant={playerSize === 'wide' ? 'secondary' : 'ghost'}
            >
              <MonitorUp />
              Amplio
            </Button>
            <Button
              aria-pressed={playerSize === 'full'}
              onClick={() => setPlayerSize('full')}
              size="sm"
              type="button"
              variant={playerSize === 'full' ? 'secondary' : 'ghost'}
            >
              <Maximize2 />
              Todo el ancho
            </Button>
          </div>
        </fieldset>
        <label className="learning-native-video__quality">
          <span>Resolución</span>
          <select
            aria-describedby="learning-native-video-quality-description"
            disabled={qualityOptions.length <= 1}
            onChange={(event) => changeQuality(event.target.value)}
            value={selectedQuality}
          >
            {qualityOptions.length > 1 ? (
              <option value="auto">Automática</option>
            ) : null}
            {qualityOptions.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
            {qualityOptions.length === 0 ? (
              <option value="unavailable">Automática</option>
            ) : null}
          </select>
        </label>
      </div>
      <p className="sr-only" id="learning-native-video-quality-description">
        {qualityDescription}
      </p>
      {failed ? (
        <p className="mt-3 text-sm text-destructive" role="alert">
          No fue posible reproducir este vídeo.
        </p>
      ) : null}
    </section>
  );
}
