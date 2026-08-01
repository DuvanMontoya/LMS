import 'server-only';

import type { operations } from '@/lib/api/generated/platform';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';

export type NotificationList =
  operations['notifications_list']['responses'][200]['content']['application/json'];
export type NotificationPreferences =
  operations['notification_preferences_retrieve']['responses'][200]['content']['application/json'];

export async function getNotifications(page = 1): Promise<NotificationList> {
  const client = await createPlatformServerClient();
  const { data, response } = await client.GET('/api/v1/notifications/', {
    params: { query: { page } },
  });
  if (!response.ok || !data) {
    throw new Error('No fue posible consultar las notificaciones.');
  }
  return data;
}

export async function getNotificationPreferences(): Promise<NotificationPreferences> {
  const client = await createPlatformServerClient();
  const { data, response } = await client.GET(
    '/api/v1/notifications/preferences/',
  );
  if (!response.ok || !data) {
    throw new Error('No fue posible consultar las preferencias.');
  }
  return data;
}
