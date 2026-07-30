import { CheckCircle2, CircleAlert, FileLock2 } from 'lucide-react';
import Link from 'next/link';
import { notFound } from 'next/navigation';

import { CreateDraftAction } from '@/components/publishing/publication-actions';
import { PageHeader } from '@/components/platform/page-header';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { formatDuration } from '@/lib/publishing/labels';
import { getHistoricalRelease } from '@/lib/publishing/server';

const dateFormatter = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'long',
  timeStyle: 'short',
});

export default async function HistoricalReleasePage({
  params,
}: Readonly<{
  params: Promise<{
    courseSlug: string;
    releaseNumber: string;
    slug: string;
  }>;
}>) {
  const { courseSlug, releaseNumber: value, slug } = await params;
  const releaseNumber = Number(value);
  if (!Number.isSafeInteger(releaseNumber) || releaseNumber < 1) notFound();
  const data = await getHistoricalRelease(slug, courseSlug, releaseNumber);

  return (
    <main className="academic-page">
      <PageHeader
        actions={
          <CreateDraftAction
            canCreate={data.access.capabilities.includes(
              'course.release.create_draft',
            )}
            courseSlug={courseSlug}
            lockVersion={data.state.lock_version}
            releaseNumber={releaseNumber}
            slug={slug}
          />
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/cursos/${courseSlug}/publicacion`,
            label: 'Publicación',
          },
          { label: `Release ${releaseNumber}` },
        ]}
        description={data.release.summary}
        eyebrow="Registro histórico inmutable"
        title={data.release.title}
      />
      <Alert className="mt-5">
        <FileLock2 />
        <AlertTitle>Release {data.release.number}</AlertTitle>
        <AlertDescription>
          Creado el {dateFormatter.format(new Date(data.release.created_at))}.
          Este registro no admite edición ni eliminación.
        </AlertDescription>
      </Alert>
      <dl className="mt-5 grid border sm:grid-cols-2 lg:grid-cols-4">
        <ReleaseFact
          label="Integridad"
          value={data.verification.valid ? 'Verificada' : 'Fallida'}
        />
        <ReleaseFact
          label="Fuente"
          value={`Revisión ${data.release.source_revision_number}`}
        />
        <ReleaseFact
          label="Estructura"
          value={`${data.release.module_count} módulos · ${data.release.unit_count} unidades`}
        />
        <ReleaseFact
          label="Duración"
          value={formatDuration(data.release.estimated_duration_minutes)}
        />
      </dl>
      <section className="mt-7 grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="border">
          <header className="border-b px-5 py-4">
            <h2 className="font-semibold">Outline capturado</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Derivado únicamente del snapshot del release.
            </p>
          </header>
          <ol className="divide-y">
            {data.outline.modules.map((module) => (
              <li className="px-5 py-4" key={module.id}>
                <strong className="text-sm">
                  {module.position}. {module.title}
                </strong>
                <ol className="mt-2 space-y-1 pl-4 text-sm text-muted-foreground">
                  {module.units.map((unit) => (
                    <li key={unit.id}>
                      {module.position}.{unit.position} {unit.title}
                    </li>
                  ))}
                </ol>
              </li>
            ))}
          </ol>
        </div>
        <aside className="grid content-start gap-4">
          <div className="border p-5">
            <div className="flex items-center gap-2">
              {data.verification.valid ? (
                <CheckCircle2 className="size-5 text-primary" />
              ) : (
                <CircleAlert className="size-5 text-destructive" />
              )}
              <h2 className="font-semibold">Verificación</h2>
            </div>
            <p className="mt-2 text-sm text-muted-foreground">
              {data.verification.valid
                ? 'Schema, digest, tamaño, índices y enlace anterior coinciden.'
                : 'Se detectaron inconsistencias; no clones este release.'}
            </p>
          </div>
          <div className="border p-5">
            <h2 className="font-semibold">Identidad criptográfica</h2>
            <code className="mt-2 block break-all text-xs">
              {data.release.snapshot_digest}
            </code>
            <p className="mt-2 text-xs text-muted-foreground">
              SHA-256 ·{' '}
              {data.release.snapshot_size_bytes.toLocaleString('es-CO')} bytes ·
              schema v{data.release.schema_version}
            </p>
          </div>
          <Button asChild variant="outline">
            <Link
              href={`/organizaciones/${slug}/cursos/${courseSlug}/publicacion`}
            >
              Volver al historial
            </Link>
          </Button>
        </aside>
      </section>
    </main>
  );
}

function ReleaseFact({
  label,
  value,
}: Readonly<{ label: string; value: string }>) {
  return (
    <div className="border-b px-5 py-4 lg:border-r lg:border-b-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm font-medium">
        <Badge variant="outline">{value}</Badge>
      </dd>
    </div>
  );
}
