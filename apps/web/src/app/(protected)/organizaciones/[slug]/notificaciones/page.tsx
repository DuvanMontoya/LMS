import Link from 'next/link';

import { NotificationCenter } from '@/components/notifications/notification-center';
import { PageHeader } from '@/components/platform/page-header';
import { Button } from '@/components/ui/button';
import {
  getNotifications,
  type NotificationList,
} from '@/lib/notifications/server';

export default async function NotificationsPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ page?: string }>;
}>) {
  const { slug } = await params;
  const query = await searchParams;
  const page = Number.parseInt(query.page ?? '1', 10);
  const currentPage = Number.isFinite(page) ? page : 1;
  let notifications: NotificationList;
  let loadError = false;
  try {
    notifications = await getNotifications(currentPage);
  } catch {
    loadError = true;
    notifications = {
      pagination: { page: currentPage, page_size: 20, total: 0 },
      results: [],
    };
  }
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          <Button asChild variant="outline">
            <Link href={`/organizaciones/${slug}/notificaciones/preferencias`}>
              Preferencias
            </Link>
          </Button>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: 'Organización' },
          { label: 'Notificaciones' },
        ]}
        description="Avisos académicos y operacionales dirigidos exclusivamente a tu cuenta."
        eyebrow="Centro personal"
        title="Notificaciones"
      />
      <div className="mt-6">
        {loadError ? (
          <section className="platform-empty-state" role="alert">
            <h2 className="font-semibold">
              No pudimos cargar tus notificaciones
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              El servicio no respondió correctamente. Puedes intentarlo de nuevo
              sin perder ningún dato.
            </p>
            <Button asChild className="mt-4" variant="outline">
              <Link
                href={`/organizaciones/${slug}/notificaciones?page=${currentPage}`}
              >
                Reintentar
              </Link>
            </Button>
          </section>
        ) : (
          <NotificationCenter items={notifications} organizationSlug={slug} />
        )}
      </div>
    </main>
  );
}
