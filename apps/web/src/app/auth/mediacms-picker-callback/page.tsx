'use client';

import { useEffect } from 'react';

export default function MediaCmsPickerCallbackPage() {
  useEffect(() => {
    const params = new URL(window.location.href).searchParams;
    const channel = params.get('channel') ?? '';
    const mediaFriendlyToken = params.get('mediaFriendlyToken') ?? '';
    const nonce = params.get('nonce') ?? '';
    if (
      channel !== 'lms-mediacms-picker-v1' ||
      !/^[A-Za-z0-9_-]{1,64}$/.test(mediaFriendlyToken) ||
      !/^[A-Za-z0-9_-]{16,128}$/.test(nonce)
    )
      return;
    window.localStorage.setItem(
      'lms-mediacms-picker-selection',
      JSON.stringify({ channel, mediaFriendlyToken, nonce }),
    );
    window.setTimeout(() => window.close(), 250);
  }, []);

  return (
    <main className="grid min-h-screen place-items-center bg-muted/30 p-6">
      <div className="max-w-md rounded-xl border bg-background p-6 text-center shadow-sm">
        <h1 className="text-lg font-semibold">Vídeo seleccionado</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          La selección se está devolviendo a la configuración de la lección.
          Puedes cerrar esta ventana si permanece abierta.
        </p>
      </div>
    </main>
  );
}
