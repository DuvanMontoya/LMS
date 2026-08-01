import { PreferenceForm } from '@/components/notifications/preference-form';
import { PageHeader } from '@/components/platform/page-header';
import { getNotificationPreferences } from '@/lib/notifications/server';

export default async function NotificationPreferencesPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const preferences = await getNotificationPreferences();
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: 'Organización' },
          {
            href: `/organizaciones/${slug}/notificaciones`,
            label: 'Notificaciones',
          },
          { label: 'Preferencias' },
        ]}
        description="Elige por categoría qué avisos recibes en la plataforma y por correo."
        eyebrow="Preferencias personales"
        title="Canales de notificación"
      />
      <div className="mt-6">
        <PreferenceForm initial={preferences} />
      </div>
    </main>
  );
}
