import {
  ArrowRight,
  CheckCircle2,
  CircleDotDashed,
  FileStack,
  LibraryBig,
  Plus,
  ShieldCheck,
} from 'lucide-react';
import Link from 'next/link';

import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getAssessments } from '@/lib/assessments/server';

export default async function AssessmentsPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getAssessments(slug);
  const canManage = data.access.capabilities.includes(
    'assessment.authoring.manage',
  );
  const approved = data.assessments.results.filter(
    (assessment) => assessment.latest_version_number,
  ).length;
  const inReview = data.assessments.results.filter((assessment) =>
    ['in_review', 'changes_requested'].includes(assessment.authoring_status),
  ).length;
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          <div className="flex gap-2">
            <Button asChild size="sm" variant="outline">
              <Link href={`/organizaciones/${slug}/evaluaciones/bancos`}>
                <LibraryBig data-icon="inline-start" /> Bancos
              </Link>
            </Button>
            {canManage ? (
              <Button asChild size="sm">
                <Link href={`/organizaciones/${slug}/evaluaciones/nueva`}>
                  <Plus data-icon="inline-start" /> Nueva evaluación
                </Link>
              </Button>
            ) : null}
          </div>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Evaluaciones' },
        ]}
        description="Diseña instrumentos trazables, gobierna su revisión editorial y fija versiones inmutables antes de entregarlas."
        eyebrow="Centro de evaluación"
        title="Evaluaciones"
      />
      <section
        className="assessment-metric-grid"
        aria-label="Resumen de autoría"
      >
        <article>
          <span>
            <FileStack />
          </span>
          <div>
            <strong>{data.assessments.count}</strong>
            <p>Instrumentos</p>
          </div>
        </article>
        <article>
          <span>
            <CheckCircle2 />
          </span>
          <div>
            <strong>{approved}</strong>
            <p>Con versión aprobada</p>
          </div>
        </article>
        <article>
          <span>
            <CircleDotDashed />
          </span>
          <div>
            <strong>{inReview}</strong>
            <p>En circuito editorial</p>
          </div>
        </article>
        <article>
          <span>
            <ShieldCheck />
          </span>
          <div>
            <strong>100 %</strong>
            <p>Versionado auditable</p>
          </div>
        </article>
      </section>
      <section className="assessment-collection">
        <header className="assessment-collection__header">
          <div>
            <p className="assessment-rail-kicker">Portafolio institucional</p>
            <h2>Instrumentos en autoría</h2>
          </div>
          <span>Última revisión visible</span>
        </header>
        {data.assessments.results.length ? (
          <ul className="assessment-instrument-list">
            {data.assessments.results.map((assessment) => (
              <li key={assessment.id}>
                <div className="assessment-instrument-list__index">
                  {String(assessment.latest_revision_number ?? 1).padStart(
                    2,
                    '0',
                  )}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="assessment-resource-card__code">
                    /{assessment.slug}
                  </p>
                  <h3>{assessment.title}</h3>
                  <div className="assessment-instrument-list__meta">
                    <span>
                      Revisión {assessment.latest_revision_number ?? '—'}
                    </span>
                    <span>
                      {assessment.latest_version_number
                        ? `Versión aprobada v${assessment.latest_version_number}`
                        : 'Sin snapshot aprobado'}
                    </span>
                  </div>
                </div>
                <Badge
                  className="assessment-status"
                  data-status={assessment.authoring_status}
                  variant="outline"
                >
                  {authoringStatusLabel(assessment.authoring_status)}
                </Badge>
                <Button asChild variant="outline">
                  <Link
                    href={`/organizaciones/${slug}/evaluaciones/${assessment.slug}`}
                  >
                    Abrir compositor <ArrowRight data-icon="inline-end" />
                  </Link>
                </Button>
              </li>
            ))}
          </ul>
        ) : (
          <div className="assessment-empty">
            <FileStack />
            <h3>No hay evaluaciones en autoría</h3>
            <p>Crea un instrumento para iniciar su diseño y aprobación.</p>
          </div>
        )}
      </section>
    </main>
  );
}

function authoringStatusLabel(status: string) {
  const labels: Record<string, string> = {
    approved: 'Aprobada',
    changes_requested: 'Cambios solicitados',
    draft: 'Borrador',
    in_review: 'En revisión',
  };
  return labels[status] ?? status;
}
