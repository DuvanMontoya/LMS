'use client';

import { Bell } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { platformBrowserClient } from '@/lib/api/platform-browser-client';

export function NotificationBadge({ href }: Readonly<{ href: string }>) {
  const [count, setCount] = useState(0);
  useEffect(() => {
    let active = true;
    async function refresh() {
      if (document.visibilityState !== 'visible') return;
      const { data, response } = await platformBrowserClient.GET(
        '/api/v1/notifications/unread-count/',
      );
      if (active && response.ok && data) setCount(data.count);
    }
    void refresh();
    const timer = window.setInterval(() => void refresh(), 60_000);
    document.addEventListener('visibilitychange', refresh);
    window.addEventListener('notifications:changed', refresh);
    return () => {
      active = false;
      window.clearInterval(timer);
      document.removeEventListener('visibilitychange', refresh);
      window.removeEventListener('notifications:changed', refresh);
    };
  }, []);
  return (
    <Link
      aria-label={`Notificaciones${count ? `, ${count} sin leer` : ''}`}
      className="relative grid size-9 place-items-center rounded-md border bg-background hover:bg-muted"
      href={href}
    >
      <Bell className="size-4" />
      {count ? (
        <span
          aria-hidden="true"
          className="absolute -top-1 -right-1 min-w-5 rounded-full bg-primary px-1 text-center text-[0.65rem] font-semibold leading-5 text-primary-foreground"
        >
          {Math.min(count, 99)}
        </span>
      ) : null}
    </Link>
  );
}
