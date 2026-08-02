'use client';

import { Bell, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import type { components } from '@/lib/api/generated/platform';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

type Notification = components['schemas']['Notification'];

export function NotificationBadge({ href }: Readonly<{ href: string }>) {
  const [count, setCount] = useState(0);
  const [items, setItems] = useState<Notification[]>([]);
  const [loading, setLoading] = useState(false);
  const [loaded, setLoaded] = useState(false);

  const refreshCount = useCallback(async () => {
    if (document.visibilityState !== 'visible') return;
    const { data, response } = await platformBrowserClient.GET(
      '/api/v1/notifications/unread-count/',
    );
    if (response.ok && data) setCount(data.count);
  }, []);

  const refreshItems = useCallback(async () => {
    setLoading(true);
    try {
      const { data, response } = await platformBrowserClient.GET(
        '/api/v1/notifications/',
        { params: { query: { page: 1 } } },
      );
      if (response.ok && data) {
        setItems(data.results.slice(0, 5));
        setLoaded(true);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const initial = window.setTimeout(() => void refreshCount(), 0);
    const timer = window.setInterval(() => void refreshCount(), 60_000);
    document.addEventListener('visibilitychange', refreshCount);
    window.addEventListener('notifications:changed', refreshCount);
    return () => {
      window.clearTimeout(initial);
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', refreshCount);
      window.removeEventListener('notifications:changed', refreshCount);
    };
  }, [refreshCount]);

  return (
    <DropdownMenu
      onOpenChange={(open) => {
        if (open) void refreshItems();
      }}
    >
      <DropdownMenuTrigger asChild>
        <button
          aria-label={`Notificaciones${count ? `, ${count} sin leer` : ''}`}
          className="relative grid size-9 place-items-center rounded-full border bg-background shadow-xs transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          type="button"
        >
          <Bell className="size-4" />
          {count ? (
            <span
              aria-hidden="true"
              className="absolute -top-1 -right-1 min-w-5 rounded-full bg-primary px-1 text-center text-[0.65rem] font-semibold leading-5 text-primary-foreground ring-2 ring-background"
            >
              {Math.min(count, 99)}
            </span>
          ) : null}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-[22rem] max-w-[calc(100vw-1rem)] p-0"
      >
        <DropdownMenuLabel className="flex items-center justify-between px-4 py-3">
          <span className="text-base font-semibold">Notificaciones</span>
          {count ? (
            <span className="text-xs font-normal text-muted-foreground">
              {count} sin leer
            </span>
          ) : null}
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="m-0" />
        <div aria-live="polite" className="max-h-[24rem] overflow-y-auto p-1.5">
          {loading && !loaded ? (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">
              Cargando actividad…
            </p>
          ) : items.length ? (
            items.map((item) => (
              <DropdownMenuItem asChild key={item.id}>
                <Link
                  className="items-start gap-3 px-3 py-2.5"
                  href={item.action_url || href}
                >
                  <span
                    aria-hidden="true"
                    className={`mt-1 size-2 shrink-0 rounded-full ${item.read_at ? 'bg-muted-foreground/30' : 'bg-primary'}`}
                  />
                  <span className="min-w-0 flex-1">
                    <span className="block truncate font-medium">
                      {item.title}
                    </span>
                    <span className="mt-0.5 line-clamp-2 block text-xs leading-5 text-muted-foreground">
                      {item.body}
                    </span>
                    <time
                      className="mt-1 block text-[0.7rem] text-muted-foreground"
                      dateTime={item.created_at}
                    >
                      {formatRelativeDate(item.created_at)}
                    </time>
                  </span>
                </Link>
              </DropdownMenuItem>
            ))
          ) : (
            <div className="px-4 py-8 text-center">
              <CheckCircle2 className="mx-auto size-7 text-primary" />
              <p className="mt-2 text-sm font-medium">Todo al día</p>
              <p className="mt-1 text-xs text-muted-foreground">
                No tienes actividad reciente.
              </p>
            </div>
          )}
        </div>
        <DropdownMenuSeparator className="m-0" />
        <div className="p-1.5">
          <DropdownMenuItem asChild>
            <Link
              className="justify-center py-2 font-medium text-primary"
              href={href}
            >
              Ver todas las notificaciones
            </Link>
          </DropdownMenuItem>
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

function formatRelativeDate(value: string) {
  const date = new Date(value);
  const differenceMinutes = Math.round((date.getTime() - Date.now()) / 60_000);
  if (Math.abs(differenceMinutes) < 60) {
    return new Intl.RelativeTimeFormat('es-CO', { numeric: 'auto' }).format(
      differenceMinutes,
      'minute',
    );
  }
  const differenceHours = Math.round(differenceMinutes / 60);
  if (Math.abs(differenceHours) < 24) {
    return new Intl.RelativeTimeFormat('es-CO', { numeric: 'auto' }).format(
      differenceHours,
      'hour',
    );
  }
  return new Intl.DateTimeFormat('es-CO', {
    dateStyle: 'medium',
  }).format(date);
}
