import { CheckCircle2, CircleAlert, History, ShieldCheck } from 'lucide-react';
import Link from 'next/link';

import { PublicationActions } from '@/components/publishing/publication-actions';
import { PageHeader } from '@/components/platform/page-header';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  formatDuration,
  publicationStatusLabel,
  shortDigest,
} from '@/lib/publishing/labels';
import { getPublicationWorkspace } from '@/lib/publishing/server';

const dateFormatter = new Intl.DateTimeFormat('es-CO', {
  dateStyle: 'medium',
  timeStyle: 'short',
});

export default async function PublicationPage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getPublicationWorkspace(slug, courseSlug);
  const capabilities = data.access.capabilities;
  const current = data.releases.find(
    (release) => release.number === data.state.current_release_number,
  );

  return (
    <main className="academic-page">
      <PageHeader
        actions={
          <Button asChild size="sm" variant="outline">
            <Link href={`/organizaciones/${slug}/cursos/${courseSlug}`}>
              Volver a autoría
            </Link>
          </Button>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { href: `/organizaciones/${slug}/cursos`, label: 'Cursos' },
          {
            href: `/organizaciones/${slug}/cursos/${courseSlug}`,
            label: courseSlug,
          },
          { label: 'Publicación' },
        ]}
        description="Canal institucional de releases inmutables y acceso a biblioteca."
        eyebrow="Gobierno de publicación"
        title={current?.title ?? 'Publicación del curso'}
      />

      <section className="mt-5 grid gap-4 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <div className="border">
          <header className="flex flex-wrap items-center justify-between gap-3 border-b px-5 py-4">
            <div>
              <p className="text-xs text-muted-foreground">Estado actual</p>
              <h2 className="mt-1 font-semibold">
                {publicationStatusLabel(data.state.status)}
              </h2>
            </div>
            <Badge
              variant={data.state.status === 'active' ? 'secondary' : 'outline'}
            >
              {data.state.current_release_number
                ? `Release ${data.state.current_release_number}`
                : 'Sin release'}
            </Badge>
          </header>
          <dl className="grid sm:grid-cols-2">
            <Fact
              label="Última publicación"
              value={
                data.state.last_published_at
                  ? dateFormatter.format(new Date(data.state.last_published_at))
                  : 'Aún no publicada'
              }
            />
            <Fact
              label="Versión de concurrencia"
              value={String(data.state.lock_version)}
            />
            <Fact
              label="Revisión aprobada disponible"
              value={data.state.approved_revision_id ? 'Sí' : 'No'}
            />
            <Fact
              label="Integridad del current release"
              value={
                data.verification
                  ? data.verification.valid
                    ? 'Verificada'
                    : 'Fallida'
                  : 'Sin release'
              }
            />
          </dl>
          {data.state.status === 'withdrawn' ? (
            <Alert className="m-5" variant="destructive">
              <CircleAlert />
              <AlertTitle>Publicación retirada</AlertTitle>
              <AlertDescription>{data.state.withdrawal_note}</AlertDescription>
            </Alert>
          ) : null}
        </div>

        <aside className="border p-5">
          <h2 className="font-semibold">Acciones</h2>
          <p className="mt-1 mb-4 text-sm text-muted-foreground">
            Cada cambio exige la versión de publicación que ves en pantalla.
          </p>
          <PublicationActions
            approvedRevisionId={data.state.approved_revision_id}
            canPublish={capabilities.includes('course.release.publish')}
            canWithdraw={capabilities.includes('course.release.withdraw')}
            courseSlug={courseSlug}
            lockVersion={data.state.lock_version}
            slug={slug}
            status={data.state.status}
          />
        </aside>
      </section>

      <section className="mt-7 grid gap-4 lg:grid-cols-2">
        <div className="border p-5">
          <div className="flex items-start gap-3">
            {data.readiness?.ready ? (
              <CheckCircle2 className="mt-0.5 size-5 text-primary" />
            ) : (
              <CircleAlert className="mt-0.5 size-5 text-muted-foreground" />
            )}
            <div>
              <h2 className="font-semibold">Readiness de revisión aprobada</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {data.readiness
                  ? data.readiness.ready
                    ? 'La revisión cumple las reglas estructurales y de contenido.'
                    : 'La revisión aún contiene bloqueos.'
                  : 'No hay una revisión aprobada disponible.'}
              </p>
            </div>
          </div>
          {data.readiness?.issues.length ? (
            <ul className="mt-4 list-disc space-y-1 pl-5 text-sm">
              {data.readiness.issues.map((issue) => (
                <li key={`${issue.code}-${issue.path}`}>{issue.message}</li>
              ))}
            </ul>
          ) : null}
        </div>
        <div className="border p-5">
          <div className="flex items-start gap-3">
            <ShieldCheck className="mt-0.5 size-5 text-primary" />
            <div>
              <h2 className="font-semibold">Cadena de integridad</h2>
              <p className="mt-1 text-sm text-muted-foreground">
                {data.verification?.valid
                  ? `${data.verification.checked_releases} release verificado sin alteraciones.`
                  : data.verification
                    ? 'La verificación detectó inconsistencias.'
                    : 'La cadena comenzará con la primera publicación.'}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-7 border">
        <header className="flex items-center gap-3 border-b px-5 py-4">
          <History className="size-5" />
          <div>
            <h2 className="font-semibold">Historial inmutable</h2>
            <p className="text-sm text-muted-foreground">
              Los releases anteriores permanecen disponibles para auditoría.
            </p>
          </div>
        </header>
        {data.releases.length ? (
          <ol className="divide-y">
            {data.releases.map((release) => (
              <li
                className="grid gap-3 px-5 py-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-center"
                key={release.number}
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <strong>Release {release.number}</strong>
                    {release.is_current ? (
                      <Badge variant="secondary">Vigente</Badge>
                    ) : null}
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {dateFormatter.format(new Date(release.created_at))} ·{' '}
                    {release.module_count} módulos · {release.unit_count}{' '}
                    unidades
                    {' · '}
                    {formatDuration(release.estimated_duration_minutes)}
                  </p>
                  <code className="mt-2 block text-xs text-muted-foreground">
                    SHA-256 {shortDigest(release.snapshot_digest)}
                  </code>
                </div>
                <Button asChild size="sm" variant="outline">
                  <Link
                    href={`/organizaciones/${slug}/cursos/${courseSlug}/publicaciones/${release.number}`}
                  >
                    Inspeccionar
                  </Link>
                </Button>
              </li>
            ))}
          </ol>
        ) : (
          <p className="px-5 py-8 text-sm text-muted-foreground">
            Este curso aún no tiene releases.
          </p>
        )}
      </section>
    </main>
  );
}

function Fact({ label, value }: Readonly<{ label: string; value: string }>) {
  return (
    <div className="border-b px-5 py-4 sm:border-r sm:nth-[2n]:border-r-0">
      <dt className="text-xs text-muted-foreground">{label}</dt>
      <dd className="mt-1 text-sm font-medium">{value}</dd>
    </div>
  );
}
