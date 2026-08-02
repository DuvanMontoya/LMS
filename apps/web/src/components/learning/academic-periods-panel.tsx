'use client';

import { CalendarRange, LoaderCircle, Plus } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useState } from 'react';

import type { components } from '@/lib/api/generated/platform';
import { createAcademicPeriod } from '@/lib/learning/api';

import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';

type AcademicPeriod = components['schemas']['AcademicPeriodRead'];

const periodLabels: Record<components['schemas']['PeriodTypeEnum'], string> = {
  grading_period: 'Periodo de calificación',
  quarter: 'Cuatrimestre',
  school_year: 'Año escolar',
  semester: 'Semestre',
  term: 'Periodo',
  trimester: 'Trimestre',
};

export function AcademicPeriodsPanel({
  canManage,
  periods,
  slug,
}: Readonly<{
  canManage: boolean;
  periods: AcademicPeriod[];
  slug: string;
}>) {
  const router = useRouter();
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  return (
    <div className="mt-6 grid gap-5 xl:grid-cols-[22rem_minmax(0,1fr)]">
      {canManage ? (
        <form
          className="academic-panel h-fit space-y-4 p-5"
          onSubmit={(event) => {
            event.preventDefault();
            const form = event.currentTarget;
            const values = new FormData(form);
            setPending(true);
            setError('');
            void createAcademicPeriod(slug, {
              ends_on: String(values.get('ends_on')),
              name: String(values.get('name')),
              period_type: String(
                values.get('period_type'),
              ) as components['schemas']['PeriodTypeEnum'],
              slug: String(values.get('slug')),
              starts_on: String(values.get('starts_on')),
            })
              .then(() => {
                form.reset();
                router.refresh();
              })
              .catch((reason: unknown) =>
                setError(
                  reason instanceof Error
                    ? reason.message
                    : 'No fue posible crear el periodo.',
                ),
              )
              .finally(() => setPending(false));
          }}
        >
          <div>
            <p className="text-xs font-semibold tracking-wider text-primary uppercase">
              Gobierno temporal
            </p>
            <h2 className="mt-1 text-lg font-semibold">Nuevo periodo</h2>
            <p className="mt-1 text-sm text-muted-foreground">
              Los grupos de curso nuevos deben quedar fijados a uno.
            </p>
          </div>
          <PeriodField label="Nombre" name="name" />
          <PeriodField
            label="Slug"
            name="slug"
            pattern="[a-z0-9]+(?:-[a-z0-9]+)*"
          />
          <div className="space-y-2">
            <Label htmlFor="period-type">Tipo</Label>
            <select
              className="academic-control"
              id="period-type"
              name="period_type"
            >
              {Object.entries(periodLabels).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          <PeriodField label="Inicio" name="starts_on" type="date" />
          <PeriodField label="Fin" name="ends_on" type="date" />
          {error ? (
            <p className="text-sm text-destructive" role="alert">
              {error}
            </p>
          ) : null}
          <Button className="w-full" disabled={pending} type="submit">
            {pending ? <LoaderCircle className="animate-spin" /> : <Plus />}
            Crear periodo
          </Button>
        </form>
      ) : null}
      <section className="space-y-3" aria-labelledby="period-list-title">
        <header className="flex items-end justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold" id="period-list-title">
              Calendario institucional
            </h2>
            <p className="text-sm text-muted-foreground">
              {periods.length} {periods.length === 1 ? 'periodo' : 'periodos'}{' '}
              registrados
            </p>
          </div>
        </header>
        {periods.map((period) => (
          <article className="academic-panel flex gap-4 p-5" key={period.id}>
            <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
              <CalendarRange />
            </span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold">{period.name}</h3>
                <Badge
                  variant={period.status === 'active' ? 'secondary' : 'outline'}
                >
                  {period.status === 'active' ? 'Activo' : 'Archivado'}
                </Badge>
              </div>
              <p className="mt-1 text-sm text-muted-foreground">
                {periodLabels[period.period_type]} ·{' '}
                {formatDate(period.starts_on)} a {formatDate(period.ends_on)}
              </p>
              <p className="mt-2 text-xs text-muted-foreground">
                Código: {period.slug}
              </p>
            </div>
          </article>
        ))}
        {!periods.length ? (
          <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
            No hay periodos académicos registrados.
          </div>
        ) : null}
      </section>
    </div>
  );
}

function PeriodField({
  label,
  name,
  pattern,
  type = 'text',
}: Readonly<{
  label: string;
  name: string;
  pattern?: string;
  type?: 'date' | 'text';
}>) {
  return (
    <div className="space-y-2">
      <Label htmlFor={`period-${name}`}>{label}</Label>
      <Input
        id={`period-${name}`}
        name={name}
        pattern={pattern}
        required
        type={type}
      />
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat('es-CO', { dateStyle: 'medium' }).format(
    new Date(`${value}T12:00:00`),
  );
}
