import { notFound } from 'next/navigation';

import { PlatformRegistrationForm } from '@/components/organizations/platform-registration-form';
import { PageHeader } from '@/components/platform/page-header';
import { createPlatformServerClient } from '@/lib/api/platform-server-client';

export default async function PlatformConfigurationPage() {
  const client = await createPlatformServerClient();
  const { data, response } = await client.GET(
    '/api/v1/platform/registration-settings/',
  );
  if (!response.ok || !data) notFound();
  return (
    <main className="academic-page">
      <PageHeader
        breadcrumbs={[{ label: 'Configuración de plataforma' }]}
        description="Política global de creación de cuentas. La verificación de correo permanece obligatoria."
        eyebrow="Administración de plataforma"
        title="Registro y acceso"
      />
      <div className="mt-6 max-w-3xl">
        <PlatformRegistrationForm settings={data} />
      </div>
    </main>
  );
}
