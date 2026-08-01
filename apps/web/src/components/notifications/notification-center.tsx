'use client';

import { Archive, CheckCheck, Mail, MailOpen } from 'lucide-react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import type { NotificationList } from '@/lib/notifications/server';

export function NotificationCenter({
  items,
  organizationSlug,
}: Readonly<{ items: NotificationList; organizationSlug: string }>) {
  const router = useRouter();
  const [busy, setBusy] = useState<string>();
  const [error, setError] = useState<string>();
  async function mutate(path: 'archive' | 'read' | 'unread', id: string) {
    setBusy(id);
    setError(undefined);
    try {
      const params = { params: { path: { notification_id: id } } } as const;
      const result =
        path === 'archive'
          ? await platformBrowserClient.POST(
              '/api/v1/notifications/{notification_id}/archive/',
              params,
            )
          : path === 'read'
            ? await platformBrowserClient.POST(
                '/api/v1/notifications/{notification_id}/read/',
                params,
              )
            : await platformBrowserClient.POST(
                '/api/v1/notifications/{notification_id}/unread/',
                params,
              );
      if (!result.response.ok) throw new Error('notification_update_failed');
      window.dispatchEvent(new Event('notifications:changed'));
      router.refresh();
    } catch {
      setError(
        'No fue posible actualizar la notificación. Inténtalo de nuevo.',
      );
    } finally {
      setBusy(undefined);
    }
  }
  async function readAll() {
    setBusy('all');
    setError(undefined);
    try {
      const result = await platformBrowserClient.POST(
        '/api/v1/notifications/read-all/',
      );
      if (!result.response.ok) throw new Error('notification_update_failed');
      window.dispatchEvent(new Event('notifications:changed'));
      router.refresh();
    } catch {
      setError(
        'No fue posible actualizar las notificaciones. Inténtalo de nuevo.',
      );
    } finally {
      setBusy(undefined);
    }
  }
  if (!items.results.length) {
    return (
      <section className="platform-empty-state">
        <MailOpen className="mx-auto size-7 text-muted-foreground" />
        <h2 className="mt-3 font-semibold">Todo al día</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          No tienes notificaciones activas.
        </p>
      </section>
    );
  }
  return (
    <section aria-labelledby="notification-list-heading">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-semibold" id="notification-list-heading">
          Actividad reciente
        </h2>
        <Button
          disabled={busy === 'all'}
          onClick={readAll}
          size="sm"
          variant="outline"
        >
          <CheckCheck />
          Marcar todas como leídas
        </Button>
      </div>
      {error ? (
        <p
          className="mb-3 rounded-lg border border-destructive/30 bg-destructive/5 p-3 text-sm"
          role="alert"
        >
          {error}
        </p>
      ) : null}
      <ul className="grid gap-3">
        {items.results.map((item) => (
          <li
            className={`rounded-xl border bg-card p-4 ${item.read_at ? '' : 'border-primary/30 shadow-sm'}`}
            key={item.id}
          >
            <div className="flex items-start gap-3">
              <span className="mt-0.5 grid size-9 shrink-0 place-items-center rounded-full bg-muted">
                <Mail className="size-4" />
              </span>
              <div className="min-w-0 flex-1">
                <p className="font-semibold">{item.title}</p>
                <p className="mt-1 text-sm text-muted-foreground">
                  {item.body}
                </p>
                <p className="mt-2 text-xs text-muted-foreground">
                  <time dateTime={item.created_at}>
                    {new Intl.DateTimeFormat('es-CO', {
                      dateStyle: 'medium',
                      timeStyle: 'short',
                    }).format(new Date(item.created_at))}
                  </time>
                </p>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-2 border-t pt-3">
              {item.action_url ? (
                <Button asChild size="sm">
                  <Link href={item.action_url}>Abrir</Link>
                </Button>
              ) : null}
              <Button
                disabled={busy === item.id}
                onClick={() =>
                  mutate(item.read_at ? 'unread' : 'read', item.id)
                }
                size="sm"
                variant="outline"
              >
                {item.read_at ? 'Marcar no leída' : 'Marcar leída'}
              </Button>
              <Button
                disabled={busy === item.id}
                onClick={() => mutate('archive', item.id)}
                size="sm"
                variant="ghost"
              >
                <Archive />
                Archivar
              </Button>
            </div>
          </li>
        ))}
      </ul>
      {items.pagination.total > items.pagination.page_size ? (
        <nav
          aria-label="Paginación de notificaciones"
          className="mt-5 flex items-center justify-between gap-3"
        >
          <Button
            asChild
            className={
              items.pagination.page <= 1 ? 'pointer-events-none opacity-50' : ''
            }
            variant="outline"
          >
            <Link
              aria-disabled={items.pagination.page <= 1}
              href={`/organizaciones/${organizationSlug}/notificaciones?page=${Math.max(1, items.pagination.page - 1)}`}
            >
              Anterior
            </Link>
          </Button>
          <span className="text-sm text-muted-foreground">
            Página {items.pagination.page}
          </span>
          <Button
            asChild
            className={
              items.pagination.page * items.pagination.page_size >=
              items.pagination.total
                ? 'pointer-events-none opacity-50'
                : ''
            }
            variant="outline"
          >
            <Link
              aria-disabled={
                items.pagination.page * items.pagination.page_size >=
                items.pagination.total
              }
              href={`/organizaciones/${organizationSlug}/notificaciones?page=${items.pagination.page + 1}`}
            >
              Siguiente
            </Link>
          </Button>
        </nav>
      ) : null}
      <p aria-live="polite" className="sr-only">
        {busy ? 'Actualizando notificación' : ''}
      </p>
    </section>
  );
}
