'use client';

import { RefreshCw, ShieldCheck, Video } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';

type LaunchState =
  | { status: 'loading' }
  | { status: 'ready'; url: string }
  | { status: 'error' };

function isLaunchDescriptor(value: unknown): value is { launch_url: string } {
  return Boolean(
    value &&
    typeof value === 'object' &&
    'launch_url' in value &&
    typeof value.launch_url === 'string',
  );
}

export function MediaCMSVideoPlayer({
  enrollmentId,
  slug,
  unitId,
}: Readonly<{
  enrollmentId: string;
  slug: string;
  unitId: string;
}>) {
  const [reloadKey, setReloadKey] = useState(0);
  const [state, setState] = useState<LaunchState>({ status: 'loading' });

  const requestLaunch = useCallback(
    async (signal: AbortSignal) => {
      setState({ status: 'loading' });
      const response = await fetch(
        `/api/v1/organizations/${encodeURIComponent(slug)}/learning/me/enrollments/${encodeURIComponent(enrollmentId)}/units/${encodeURIComponent(unitId)}/mediacms-launch/`,
        { cache: 'no-store', credentials: 'same-origin', signal },
      );
      const payload: unknown = await response.json().catch(() => null);
      if (!response.ok || !isLaunchDescriptor(payload)) {
        throw new Error('No fue posible autorizar el vídeo.');
      }
      setState({ status: 'ready', url: payload.launch_url });
    },
    [enrollmentId, slug, unitId],
  );

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      void requestLaunch(controller.signal).catch(() => {
        if (!controller.signal.aborted) setState({ status: 'error' });
      });
    }, 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [reloadKey, requestLaunch]);

  return (
    <section
      aria-label="Vídeo de la lección"
      className="overflow-hidden rounded-xl border bg-card shadow-xs"
      data-mediacms-delivery="lti"
    >
      <header className="flex flex-wrap items-center justify-between gap-3 border-b bg-muted/20 px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="rounded-md bg-primary/10 p-1.5 text-primary">
            <Video className="size-4" />
          </span>
          <div>
            <h2 className="text-sm font-semibold">Vídeo de la lección</h2>
            <p className="text-xs text-muted-foreground">
              Reproducción privada autorizada por tu matrícula.
            </p>
          </div>
        </div>
        <span className="inline-flex items-center gap-1 text-xs text-muted-foreground">
          <ShieldCheck className="size-3.5 text-primary" />
          LTI 1.3
        </span>
      </header>
      {state.status === 'ready' ? (
        <div className="aspect-video bg-black">
          <iframe
            allow="fullscreen; picture-in-picture"
            allowFullScreen
            className="size-full border-0"
            referrerPolicy="no-referrer"
            sandbox="allow-forms allow-same-origin allow-scripts"
            src={state.url}
            title="Reproductor seguro de MediaCMS"
          />
        </div>
      ) : (
        <div className="grid min-h-64 place-items-center px-6 py-10 text-center">
          <div>
            {state.status === 'loading' ? (
              <>
                <Video className="mx-auto size-6 animate-pulse text-primary" />
                <p className="mt-3 text-sm font-medium">
                  Autorizando la reproducción…
                </p>
              </>
            ) : (
              <>
                <p className="text-sm font-medium">
                  No fue posible abrir el vídeo de forma segura.
                </p>
                <p className="mt-1 text-xs text-muted-foreground">
                  Verifica tu matrícula o vuelve a solicitar un lanzamiento.
                </p>
                <Button
                  className="mt-4"
                  onClick={() => setReloadKey((value) => value + 1)}
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  <RefreshCw /> Reintentar
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
