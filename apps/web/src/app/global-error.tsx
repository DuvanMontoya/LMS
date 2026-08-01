'use client';

import * as Sentry from '@sentry/nextjs';
import { useEffect } from 'react';

export default function GlobalError({
  error,
  unstable_retry,
}: Readonly<{
  error: Error & { digest?: string };
  unstable_retry: () => void;
}>) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);
  return (
    <html lang="es">
      <body>
        <main className="grid min-h-screen place-items-center p-6">
          <div className="max-w-md text-center">
            <h1 className="text-xl font-semibold">
              No fue posible cargar la plataforma
            </h1>
            <p className="mt-2 text-muted-foreground">
              El incidente quedó registrado sin incluir tus datos privados.
            </p>
            <button
              className="mt-4 rounded-md bg-primary px-4 py-2 text-primary-foreground"
              onClick={unstable_retry}
            >
              Intentar de nuevo
            </button>
          </div>
        </main>
      </body>
    </html>
  );
}
