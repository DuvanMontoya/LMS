import {
  ArrowRight,
  BookOpenCheck,
  CirclePause,
  GraduationCap,
} from 'lucide-react';
import Link from 'next/link';

import { LearningProgress } from '@/components/learning/learning-progress';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { accessStateLabel } from '@/lib/learning/labels';
import { getMyLearning } from '@/lib/learning/server';

export default async function MyLearningPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const data = await getMyLearning(slug);
  return (
    <main className="academic-page" id="contenido-principal">
      <PageHeader
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { label: 'Mi aprendizaje' },
        ]}
        description="Cursos vinculados a tus matrículas institucionales y al release que te fue asignado."
        eyebrow="Experiencia del estudiante"
        title="Mi aprendizaje"
      />
      {data.enrollments.length ? (
        <ul className="mt-6 grid gap-4 lg:grid-cols-2">
          {data.enrollments.map((enrollment) => {
            const available = enrollment.access_state === 'available';
            return (
              <li
                className="flex min-w-0 flex-col border p-5"
                key={enrollment.enrollment_id}
              >
                <div className="flex items-start gap-3">
                  <span className="grid size-10 shrink-0 place-items-center border bg-muted/30">
                    {available ? (
                      <GraduationCap className="size-5 text-primary" />
                    ) : (
                      <CirclePause className="size-5 text-muted-foreground" />
                    )}
                  </span>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <h2 className="font-semibold">
                        {enrollment.course.title}
                      </h2>
                      <Badge variant={available ? 'secondary' : 'outline'}>
                        {accessStateLabel(enrollment.access_state)}
                      </Badge>
                    </div>
                    <p className="mt-2 line-clamp-3 text-sm text-muted-foreground">
                      {enrollment.course.summary}
                    </p>
                    <p className="mt-2 text-xs text-muted-foreground">
                      Release {enrollment.release_number}
                      {enrollment.cohort ? ` · ${enrollment.cohort.name}` : ''}
                    </p>
                  </div>
                </div>
                <div className="mt-5 border-y py-4">
                  <LearningProgress progress={enrollment.progress} />
                </div>
                {available && enrollment.resume.href ? (
                  <Button asChild className="mt-4" size="sm">
                    <Link href={enrollment.resume.href}>
                      {enrollment.progress.status === 'not_started'
                        ? 'Comenzar'
                        : 'Continuar'}
                      <ArrowRight data-icon="inline-end" />
                    </Link>
                  </Button>
                ) : (
                  <p className="mt-4 text-sm text-muted-foreground">
                    El contenido no puede abrirse mientras este estado esté
                    vigente.
                  </p>
                )}
              </li>
            );
          })}
        </ul>
      ) : (
        <section className="mt-6 border border-dashed px-6 py-12 text-center">
          <BookOpenCheck className="mx-auto size-7 text-muted-foreground" />
          <h2 className="mt-3 font-semibold">Aún no tienes matrículas</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Los cursos aparecerán aquí cuando una institución te matricule.
          </p>
        </section>
      )}
    </main>
  );
}
