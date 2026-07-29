'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { mapAllauthErrorToSpanish } from '@/lib/auth/errors';
import { useLogout } from '@/lib/auth/hooks';

export function LogoutButton() {
  const router = useRouter();
  const logout = useLogout();
  const [message, setMessage] = useState<string | null>(null);
  const onLogout = async () => {
    setMessage(null);
    try {
      await logout.mutateAsync();
      router.refresh();
      router.replace('/auth/iniciar-sesion');
    } catch {
      setMessage(mapAllauthErrorToSpanish('unknown', null));
    }
  };
  return (
    <div className="space-y-2">
      <button
        type="button"
        disabled={logout.isPending}
        onClick={onLogout}
        className="rounded-lg border border-slate-300 px-4 py-2 font-medium text-slate-900 disabled:opacity-60"
      >
        {logout.isPending ? 'Cerrando sesión…' : 'Cerrar sesión'}
      </button>
      {message ? (
        <p role="alert" className="text-sm text-red-700">
          {message}
        </p>
      ) : null}
    </div>
  );
}
