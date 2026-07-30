import { ArrowRight, CheckCircle2, Circle, CircleDot } from 'lucide-react';
import Link from 'next/link';

import { LearningProgress } from '@/components/learning/learning-progress';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  getEnrollmentForCourse,
  getLearningOutline,
} from '@/lib/learning/server';

export default async function LearningOutlinePage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const { enrollment } = await getEnrollmentForCourse(slug, courseSlug);
  const data = await getLearningOutline(slug, enrollment.enrollment_id);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        actions={
          data.outline.resume.href ? (
            <Button asChild size="sm">
              <Link href={data.outline.resume.href}>
                Continuar
                <ArrowRight data-icon="inline-end" />
              </Link>
            </Button>
          ) : null
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          {
            href: `/organizaciones/${slug}/aprendizaje`,
            label: 'Mi aprendizaje',
          },
          { label: data.outline.course.title },
        ]}
        description={data.outline.course.summary}
        eyebrow={`Release asignado ${data.outline.release_number}`}
        title={data.outline.course.title}
      />
      <section className="mt-5 border p-5" aria-label="Progreso del curso">
        <LearningProgress progress={data.outline.progress} />
      </section>
      {data.outline.cohort ? (
        <p className="mt-3 text-sm text-muted-foreground">
          Cohorte: {data.outline.cohort.name}
        </p>
      ) : null}
      <section className="mt-6 border">
        <header className="border-b px-5 py-4">
          <h2 className="font-semibold">Ruta de aprendizaje</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            El orden y las unidades pertenecen al release fijado en tu
            matrícula.
          </p>
        </header>
        <ol className="divide-y">
          {data.outline.modules.map((module) => (
            <li
              className="grid lg:grid-cols-[16rem_minmax(0,1fr)]"
              key={module.id}
            >
              <div className="border-b bg-muted/15 px-5 py-4 lg:border-r lg:border-b-0">
                <span className="text-xs text-muted-foreground">
                  Módulo {module.position}
                </span>
                <h3 className="mt-1 text-sm font-semibold">{module.title}</h3>
                {module.description ? (
                  <p className="mt-2 text-xs text-muted-foreground">
                    {module.description}
                  </p>
                ) : null}
              </div>
              <ol className="divide-y">
                {module.units.map((unit) => (
                  <li key={unit.id}>
                    <Link
                      aria-current={unit.is_current ? 'step' : undefined}
                      className="flex min-h-14 items-center gap-3 px-5 py-3 text-sm hover:bg-muted/30 focus-visible:outline-2 focus-visible:outline-offset-[-2px]"
                      href={unit.href}
                    >
                      <UnitState status={unit.status} />
                      <span className="min-w-0 flex-1">
                        <span className="block font-medium">{unit.title}</span>
                        <span className="text-xs text-muted-foreground">
                          {unit.status === 'completed'
                            ? 'Completada'
                            : unit.status === 'in_progress'
                              ? 'En progreso'
                              : 'No iniciada'}
                        </span>
                      </span>
                      {unit.is_current ? (
                        <Badge variant="outline">Actual</Badge>
                      ) : null}
                      <ArrowRight className="size-4" aria-hidden="true" />
                    </Link>
                  </li>
                ))}
              </ol>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}

function UnitState({ status }: Readonly<{ status: string }>) {
  if (status === 'completed')
    return (
      <CheckCircle2 aria-label="Completada" className="size-4 text-primary" />
    );
  if (status === 'in_progress')
    return (
      <CircleDot aria-label="En progreso" className="size-4 text-primary" />
    );
  return (
    <Circle aria-label="No iniciada" className="size-4 text-muted-foreground" />
  );
}
