'use client';

import { useState } from 'react';

export function CopyCodeButton({ code }: Readonly<{ code: string }>) {
  const [label, setLabel] = useState('Copiar código');

  return (
    <button
      className="rounded border border-slate-300 bg-white px-3 py-1.5 text-sm font-medium text-slate-800"
      onClick={async () => {
        await navigator.clipboard.writeText(code);
        setLabel('Código copiado');
        window.setTimeout(() => setLabel('Copiar código'), 1500);
      }}
      type="button"
    >
      {label}
    </button>
  );
}
