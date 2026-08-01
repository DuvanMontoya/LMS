'use client';

import { useRouter } from 'next/navigation';
import { useState } from 'react';

import { Button } from '@/components/ui/button';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';
import type { NotificationPreferences } from '@/lib/notifications/server';

const categoryLabel: Record<string, string> = {
  learning: 'Aprendizaje',
  assessment: 'Evaluaciones',
  authoring: 'Autoría',
  asset: 'Recursos',
  publication: 'Publicación',
  system: 'Sistema',
};

export function PreferenceForm({
  initial,
}: Readonly<{ initial: NotificationPreferences }>) {
  const router = useRouter();
  const [preferences, setPreferences] = useState(initial.preferences);
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState('');
  async function save() {
    setSaving(true);
    setStatus('');
    const { response } = await platformBrowserClient.PUT(
      '/api/v1/notifications/preferences/',
      { body: { preferences } },
    );
    setSaving(false);
    setStatus(
      response.ok ? 'Preferencias guardadas.' : 'No fue posible guardar.',
    );
    if (response.ok) router.refresh();
  }
  return (
    <form
      className="rounded-xl border bg-card"
      onSubmit={(event) => {
        event.preventDefault();
        void save();
      }}
    >
      <div className="grid grid-cols-[1fr_auto_auto] gap-4 border-b px-4 py-3 text-sm font-medium">
        <span>Categoría</span>
        <span>En plataforma</span>
        <span>Correo</span>
      </div>
      {preferences.map((item, index) => (
        <fieldset
          className="grid grid-cols-[1fr_auto_auto] items-center gap-4 border-b px-4 py-4 last:border-0"
          key={item.category}
        >
          <legend className="contents font-medium">
            {categoryLabel[item.category] ?? item.category}
          </legend>
          <input
            aria-label={`${categoryLabel[item.category]} en plataforma`}
            checked={item.in_app_enabled}
            onChange={(event) =>
              setPreferences((current) =>
                current.map((value, position) =>
                  position === index
                    ? { ...value, in_app_enabled: event.target.checked }
                    : value,
                ),
              )
            }
            type="checkbox"
          />
          <input
            aria-label={`${categoryLabel[item.category]} por correo`}
            checked={item.email_enabled}
            onChange={(event) =>
              setPreferences((current) =>
                current.map((value, position) =>
                  position === index
                    ? { ...value, email_enabled: event.target.checked }
                    : value,
                ),
              )
            }
            type="checkbox"
          />
        </fieldset>
      ))}
      <div className="flex flex-col items-start gap-2 p-4 sm:flex-row sm:items-center">
        <Button disabled={saving} type="submit">
          {saving ? 'Guardando…' : 'Guardar preferencias'}
        </Button>
        <span aria-live="polite" className="text-sm text-muted-foreground">
          {saving ? 'Guardando preferencias' : status}
        </span>
      </div>
    </form>
  );
}
