'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { LogOut } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { mapAllauthErrorToSpanish } from '@/lib/auth/errors';
import { useLogout } from '@/lib/auth/hooks';

export function LogoutButton({
  className,
  compact = false,
}: Readonly<{ className?: string; compact?: boolean }>) {
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
      <Button
        type="button"
        disabled={logout.isPending}
        onClick={onLogout}
        className={cn(className)}
        size={compact ? 'sm' : 'default'}
        variant="ghost"
      >
        <LogOut data-icon="inline-start" />
        {logout.isPending ? 'Cerrando sesión…' : 'Cerrar sesión'}
      </Button>
      {message ? (
        <p role="alert" className="text-sm text-destructive">
          {message}
        </p>
      ) : null}
    </div>
  );
}
