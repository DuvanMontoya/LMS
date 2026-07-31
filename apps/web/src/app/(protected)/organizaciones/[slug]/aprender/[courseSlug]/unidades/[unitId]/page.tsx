import {
  ArrowLeft,
  ArrowRight,
  BookOpenText,
  ChevronLeft,
  ListTree,
  PanelLeftClose,
} from 'lucide-react';
import Link from 'next/link';

import { AcademicDocument } from '@/components/content/academic-document';
import { CourseCurriculum } from '@/components/learning/course-curriculum';
import { LearningPositionTracker } from '@/components/learning/learning-position-tracker';
import { LearningProgress } from '@/components/learning/learning-progress';
import { LearningUnitControls } from '@/components/learning/learning-unit-controls';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  getEnrollmentForCourse,
  getLearningOutline,
  getLearningUnit,
} from '@/lib/learning/server';
import { requirePublishedUnit } from '@/lib/publishing/snapshot';

function record(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === 'object' && !Array.isArray(value);
}

export default async function LearningUnitPage({
  params,
}: Readonly<{
  params: Promise<{ courseSlug: string; slug: string; unitId: string }>;
}>) {
  const { courseSlug, slug, unitId } = await params;
  const { enrollment } = await getEnrollmentForCourse(slug, courseSlug);
  const [data, outlineData] = await Promise.all([
    getLearningUnit(slug, enrollment.enrollment_id, unitId),
    getLearningOutline(slug, enrollment.enrollment_id),
  ]);
  const publishedUnit = requirePublishedUnit({
    ...data.payload.unit,
    content: { document: data.payload.content },
    learning_objectives: data.payload.learning_objectives,
    module: data.payload.module,
    topics: data.payload.topics,
  });
  const navigation = data.payload.navigation;
  const previous = record(navigation.previous) ? navigation.previous : null;
  const next = record(navigation.next) ? navigation.next : null;
  const outlineHref =
    typeof navigation.outline === 'string'
      ? navigation.outline
      : `/organizaciones/${slug}/aprender/${courseSlug}`;
  const unitStatus =
    record(data.payload.unit) && typeof data.payload.unit.status === 'string'
      ? data.payload.unit.status
      : 'not_started';
  const unitNumber = outlineData.outline.modules
    .flatMap((module) => module.units)
    .findIndex((unit) => unit.id === unitId);
  const totalUnits = outlineData.outline.progress.total_units;

  return (
    <main
      className="learning-player"
      data-release-number={data.payload.release_number}
      id="contenido-principal"
    >
      <header className="learning-player__topbar">
        <Link
          aria-label={`Volver a ${enrollment.course.title}`}
          className="learning-player__brand"
          href={outlineHref}
        >
          <span>
            <BookOpenText />
          </span>
          <span>
            <small>Curso</small>
            <strong>{enrollment.course.title}</strong>
          </span>
        </Link>
        <div className="learning-player__position">
          <span>
            Lección {Math.max(1, unitNumber + 1)} de {totalUnits}
          </span>
          <p>{publishedUnit.title}</p>
        </div>
        <Badge className="learning-player__release" variant="outline">
          Release {data.payload.release_number}
        </Badge>
        <Button asChild size="sm" variant="ghost">
          <Link
            aria-label={`Salir del aula y volver a ${enrollment.course.title}`}
            href={outlineHref}
          >
            <PanelLeftClose />
            <span className="hidden sm:inline">Salir del aula</span>
          </Link>
        </Button>
      </header>

      <details className="learning-player__mobile-outline">
        <summary>
          <ListTree />
          Contenido del curso
          <progress
            aria-label={`${outlineData.outline.progress.completed_units} de ${totalUnits} unidades completadas, ${(
              outlineData.outline.progress.percent_basis_points / 100
            ).toFixed(0)} %`}
            max={totalUnits}
            value={outlineData.outline.progress.completed_units}
          />
          <span>
            {outlineData.outline.progress.completed_units}/{totalUnits}
          </span>
        </summary>
        <div>
          <LearningProgress progress={outlineData.outline.progress} />
          <CourseCurriculum
            currentUnitId={unitId}
            modules={outlineData.outline.modules}
            variant="player"
          />
        </div>
      </details>

      <div className="learning-player__layout">
        <aside className="learning-player__sidebar">
          <header>
            <div>
              <span>Contenido del curso</span>
              <small>
                {outlineData.outline.progress.completed_units}/{totalUnits}{' '}
                completadas
              </small>
            </div>
            <LearningProgress progress={outlineData.outline.progress} />
          </header>
          <div className="learning-player__curriculum-scroll">
            <CourseCurriculum
              currentUnitId={unitId}
              modules={outlineData.outline.modules}
              variant="player"
            />
          </div>
          <footer>
            <Button asChild size="sm" variant="ghost">
              <Link href={outlineHref}>
                <ChevronLeft />
                Vista general del curso
              </Link>
            </Button>
          </footer>
        </aside>

        <div className="learning-player__stage">
          <article className="learning-player__lesson">
            <header className="learning-player__lesson-heading">
              <p>
                Módulo {publishedUnit.module.position} ·{' '}
                {publishedUnit.module.title}
              </p>
              <h1>{publishedUnit.title}</h1>
              {publishedUnit.summary ? (
                <div>{publishedUnit.summary}</div>
              ) : null}
              {publishedUnit.topics.length ? (
                <div className="learning-player__topics">
                  {publishedUnit.topics.map((topic) => (
                    <Badge key={topic.id} variant="outline">
                      {topic.title}
                    </Badge>
                  ))}
                </div>
              ) : null}
            </header>

            <div className="learning-player__document">
              <AcademicDocument document={publishedUnit.content.document} />
            </div>

            {publishedUnit.learning_objectives.length ? (
              <details className="learning-player__objectives">
                <summary>
                  <BookOpenText />
                  <div>
                    <strong>Objetivos de esta lección</strong>
                    <small>Información académica complementaria</small>
                  </div>
                </summary>
                <ul>
                  {publishedUnit.learning_objectives.map((objective) => (
                    <li key={objective.id}>{objective.statement}</li>
                  ))}
                </ul>
              </details>
            ) : null}
          </article>

          <div className="learning-player__completion">
            <div>
              <p className="academic-kicker">Tu progreso</p>
              <h2>¿Terminaste esta lección?</h2>
              <p>
                Registra el avance para mantener sincronizada tu ruta de
                aprendizaje.
              </p>
            </div>
            <LearningUnitControls
              enrollmentId={enrollment.enrollment_id}
              progress={data.payload.progress}
              slug={slug}
              unitId={unitId}
              unitStatus={unitStatus}
            />
          </div>

          <nav
            aria-label="Navegación entre lecciones"
            className="learning-player__navigation"
          >
            {previous && typeof previous.href === 'string' ? (
              <Button
                asChild
                className="h-auto justify-start py-3"
                variant="outline"
              >
                <Link href={previous.href}>
                  <ArrowLeft data-icon="inline-start" />
                  <span>
                    <small>Anterior</small>
                    {String(previous.title ?? 'Unidad anterior')}
                  </span>
                </Link>
              </Button>
            ) : (
              <span />
            )}
            {next && typeof next.href === 'string' ? (
              <Button asChild className="h-auto justify-end py-3">
                <Link href={next.href}>
                  <span>
                    <small>Siguiente</small>
                    {String(next.title ?? 'Unidad siguiente')}
                  </span>
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            ) : null}
          </nav>
        </div>
      </div>

      <LearningPositionTracker
        enrollmentId={enrollment.enrollment_id}
        slug={slug}
        unitId={unitId}
      />
    </main>
  );
}
