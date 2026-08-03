'use client';

import {
  ArrowUpRight,
  FileStack,
  Search,
  SlidersHorizontal,
} from 'lucide-react';
import Link from 'next/link';
import { useMemo, useState } from 'react';

import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import type { AssessmentSummary } from '@/lib/assessments/server';

type PortfolioFilter = 'all' | 'draft' | 'review' | 'approved';

export function AssessmentPortfolio({
  assessments,
  slug,
}: Readonly<{ assessments: AssessmentSummary[]; slug: string }>) {
  const [filter, setFilter] = useState<PortfolioFilter>('all');
  const [query, setQuery] = useState('');
  const visible = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase();
    return assessments.filter((assessment) => {
      const matchesQuery =
        !normalized ||
        `${assessment.title} ${assessment.description}`
          .toLocaleLowerCase()
          .includes(normalized);
      const matchesFilter =
        filter === 'all' ||
        (filter === 'approved' && Boolean(assessment.latest_version_number)) ||
        (filter === 'draft' && assessment.authoring_status === 'draft') ||
        (filter === 'review' &&
          ['in_review', 'changes_requested'].includes(
            assessment.authoring_status,
          ));
      return matchesQuery && matchesFilter;
    });
  }, [assessments, filter, query]);

  return (
    <section className="assessment-portfolio">
      <div className="assessment-portfolio__toolbar">
        <label>
          <Search />
          <span className="sr-only">Buscar evaluación</span>
          <Input
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Buscar evaluación…"
            value={query}
          />
        </label>
        <div aria-label="Filtrar evaluaciones" role="group">
          <SlidersHorizontal aria-hidden="true" />
          {(
            [
              ['all', 'Todas'],
              ['draft', 'Borradores'],
              ['review', 'En revisión'],
              ['approved', 'Aprobadas'],
            ] as const
          ).map(([value, label]) => (
            <button
              aria-pressed={filter === value}
              data-active={filter === value}
              key={value}
              onClick={() => setFilter(value)}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
        <span className="assessment-library-count">
          {visible.length} de {assessments.length}
        </span>
      </div>
      {visible.length ? (
        <ul className="assessment-portfolio__list">
          {visible.map((assessment) => (
            <li key={assessment.id}>
              <Link
                href={`/organizaciones/${slug}/evaluaciones/${assessment.slug}`}
              >
                <div className="assessment-portfolio__titleline">
                  <Badge
                    className="assessment-status"
                    data-status={assessment.authoring_status}
                    variant="outline"
                  >
                    {authoringStatusLabel(assessment.authoring_status)}
                  </Badge>
                  <ArrowUpRight aria-hidden="true" />
                </div>
                <h3>{assessment.title}</h3>
                <p className="assessment-portfolio__description">
                  {assessment.description || 'Sin descripción editorial.'}
                </p>
                <div className="assessment-portfolio__facts">
                  <span>
                    {assessment.time_limit_minutes
                      ? `${assessment.time_limit_minutes} min`
                      : 'Sin límite de tiempo'}
                  </span>
                  <span>
                    {assessment.attempt_limit
                      ? `${assessment.attempt_limit} ${assessment.attempt_limit === 1 ? 'intento' : 'intentos'}`
                      : 'Intentos sin límite'}
                  </span>
                </div>
                <div
                  className="assessment-portfolio__meta"
                  aria-label="Estado de versión"
                >
                  <div>
                    <span>Revisión</span>
                    <strong>{assessment.latest_revision_number ?? '—'}</strong>
                  </div>
                  <div>
                    <span>Versión</span>
                    <strong>{assessment.latest_version_number ?? '—'}</strong>
                  </div>
                </div>
                <span className="assessment-portfolio__open">
                  Abrir instrumento
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <div className="assessment-empty">
          <FileStack />
          <h3>No hay instrumentos con este filtro</h3>
          <p>Ajusta la búsqueda o vuelve a mostrar todos los estados.</p>
        </div>
      )}
    </section>
  );
}

function authoringStatusLabel(status: string) {
  return (
    {
      approved: 'Aprobada',
      changes_requested: 'Cambios solicitados',
      draft: 'Borrador',
      in_review: 'En revisión',
    }[status] ?? status
  );
}
