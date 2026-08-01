'use client';

import { Button } from '@/components/ui/button';

export default function SearchError({
  reset,
}: Readonly<{ reset: () => void }>) {
  return (
    <main className="academic-page" id="contenido-principal">
      <section
        aria-live="assertive"
        className="platform-empty-state"
        role="alert"
      >
        <h1 className="font-semibold">No fue posible completar la búsqueda</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Vuelve a intentarlo. La consulta no se registró en telemetría.
        </p>
        <Button className="mt-4" onClick={reset}>
          Reintentar
        </Button>
      </section>
    </main>
  );
}
