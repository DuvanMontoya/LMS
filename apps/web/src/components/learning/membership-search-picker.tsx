'use client';

import {
  ChevronLeft,
  ChevronRight,
  LoaderCircle,
  Search,
  UserPlus,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { platformBrowserClient } from '@/lib/api/platform-browser-client';

type SearchResult = { email: string; id: string };

export type MembershipOption = {
  email: string;
  id: string;
};

export function MembershipSearchPicker({
  ariaLabel,
  excludeIds = [],
  onSelect,
  slug,
}: Readonly<{
  ariaLabel: string;
  excludeIds?: readonly string[];
  onSelect: (member: MembershipOption) => void;
  slug: string;
}>) {
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [hasNext, setHasNext] = useState(false);
  const [hasPrevious, setHasPrevious] = useState(false);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');
  const hasSearch = query.trim().length >= 2;

  useEffect(() => {
    const normalized = query.trim();
    if (normalized.length < 2) {
      return undefined;
    }

    let cancelled = false;
    const timeout = window.setTimeout(() => {
      setPending(true);
      void platformBrowserClient
        .GET('/api/v1/organizations/{slug}/memberships/', {
          params: {
            path: { slug },
            query: { page, page_size: 10, q: normalized, status: 'active' },
          },
        })
        .then(({ data, response }) => {
          if (cancelled) return;
          if (!response.ok || !data) {
            setError('No fue posible buscar personas activas.');
            setResults([]);
            return;
          }
          setError('');
          setResults(
            data.results.map((member) => ({
              email: member.user.email,
              id: member.membership_id,
            })),
          );
          setHasNext(Boolean(data.next));
          setHasPrevious(Boolean(data.previous));
        })
        .catch(() => {
          if (!cancelled) {
            setError('No fue posible buscar personas activas.');
            setResults([]);
          }
        })
        .finally(() => {
          if (!cancelled) setPending(false);
        });
    }, 250);

    return () => {
      cancelled = true;
      window.clearTimeout(timeout);
    };
  }, [page, query, slug]);

  return (
    <div className="mt-3 space-y-2 rounded-md border bg-muted/10 p-3">
      <label className="grid gap-1.5 text-sm font-medium">
        Buscar persona activa
        <span className="relative">
          <Search className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            aria-label={ariaLabel}
            className="pl-9"
            onChange={(event) => {
              setQuery(event.target.value);
              setPage(1);
            }}
            placeholder="Nombre, correo o nombre visible"
            type="search"
            value={query}
          />
        </span>
      </label>
      <p className="text-xs text-muted-foreground">
        Escribe al menos dos caracteres. La búsqueda consulta el directorio
        institucional de forma paginada.
      </p>
      {hasSearch && pending ? (
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <LoaderCircle className="size-4 animate-spin" /> Buscando personas…
        </p>
      ) : null}
      {hasSearch && error ? (
        <p className="text-sm text-destructive">{error}</p>
      ) : null}
      {hasSearch && results.length ? (
        <ul className="grid gap-2" aria-label="Resultados de personas">
          {results.map((member) => {
            const selected = excludeIds.includes(member.id);
            return (
              <li
                className="flex flex-wrap items-center justify-between gap-2 rounded-md border bg-background px-3 py-2"
                key={member.id}
              >
                <span className="min-w-0 truncate text-sm">{member.email}</span>
                <Button
                  disabled={selected}
                  onClick={() =>
                    onSelect({
                      email: member.email,
                      id: member.id,
                    })
                  }
                  size="sm"
                  type="button"
                  variant="outline"
                >
                  <UserPlus />
                  {selected ? 'Seleccionada' : 'Añadir'}
                </Button>
              </li>
            );
          })}
        </ul>
      ) : null}
      {hasSearch && !pending && !results.length && !error ? (
        <p className="text-sm text-muted-foreground">Sin coincidencias.</p>
      ) : null}
      {hasSearch && (hasNext || hasPrevious) ? (
        <div className="flex justify-end gap-2">
          <Button
            aria-label="Página anterior de personas"
            disabled={!hasPrevious || pending}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            size="icon"
            type="button"
            variant="outline"
          >
            <ChevronLeft />
          </Button>
          <Button
            aria-label="Página siguiente de personas"
            disabled={!hasNext || pending}
            onClick={() => setPage((current) => current + 1)}
            size="icon"
            type="button"
            variant="outline"
          >
            <ChevronRight />
          </Button>
        </div>
      ) : null}
    </div>
  );
}
