import { ArrowLeft, ArrowRight } from 'lucide-react';
import Link from 'next/link';

import { Button } from '@/components/ui/button';

export function LearningPagination({
  baseHref,
  page,
  pageSize,
  params,
  total,
}: Readonly<{
  baseHref: string;
  page: number;
  pageSize: number;
  params: Record<string, string | undefined>;
  total: number;
}>) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  if (totalPages <= 1) return null;

  return (
    <nav
      aria-label="Paginación"
      className="mt-5 flex flex-wrap items-center justify-between gap-3"
    >
      <p className="text-sm text-muted-foreground">
        Página {page} de {totalPages} · {total} resultados
      </p>
      <div className="flex items-center gap-2">
        <Button asChild={page > 1} disabled={page <= 1} variant="outline">
          {page > 1 ? (
            <Link href={pageHref(baseHref, page - 1, params)}>
              <ArrowLeft data-icon="inline-start" />
              Anterior
            </Link>
          ) : (
            <span>
              <ArrowLeft data-icon="inline-start" />
              Anterior
            </span>
          )}
        </Button>
        <Button
          asChild={page < totalPages}
          disabled={page >= totalPages}
          variant="outline"
        >
          {page < totalPages ? (
            <Link href={pageHref(baseHref, page + 1, params)}>
              Siguiente
              <ArrowRight data-icon="inline-end" />
            </Link>
          ) : (
            <span>
              Siguiente
              <ArrowRight data-icon="inline-end" />
            </span>
          )}
        </Button>
      </div>
    </nav>
  );
}

function pageHref(
  baseHref: string,
  page: number,
  params: Record<string, string | undefined>,
) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value) query.set(key, value);
  });
  query.set('page', String(page));
  return `${baseHref}?${query.toString()}`;
}
