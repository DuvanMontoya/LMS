import { LoaderCircle } from 'lucide-react';

export default function SearchLoading() {
  return (
    <main className="academic-page" id="contenido-principal">
      <div aria-live="polite" className="platform-empty-state" role="status">
        <LoaderCircle className="mx-auto size-7 animate-spin text-primary" />
        <p className="mt-3 font-medium">Buscando contenido autorizado…</p>
      </div>
    </main>
  );
}
