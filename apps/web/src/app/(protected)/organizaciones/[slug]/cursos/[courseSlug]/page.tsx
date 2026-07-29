import Link from 'next/link';

import { AlignmentEditor } from '@/components/courses/alignment-editor';
import { CourseMetadataForm } from '@/components/courses/course-metadata-form';
import { ReviewPanel } from '@/components/courses/review-panel';
import { getCourseWorkspace } from '@/lib/courses/server';

export default async function CourseWorkspacePage({
  params,
}: Readonly<{ params: Promise<{ courseSlug: string; slug: string }> }>) {
  const { courseSlug, slug } = await params;
  const data = await getCourseWorkspace(slug, courseSlug);
  const capabilities = data.access.capabilities;
  const canManage = capabilities.includes('course.authoring.manage');
  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <nav aria-label="Migas de pan" className="text-sm text-slate-600">
        <Link href={`/organizaciones/${slug}`}>{data.organization.name}</Link>
        {' / '}
        <Link href={`/organizaciones/${slug}/cursos`}>Cursos</Link>
        {' / '}
        {data.revision.title}
      </nav>
      <header className="mt-5 rounded-2xl bg-slate-950 p-7 text-white">
        <p className="text-sm text-slate-300">Workspace del curso</p>
        <h1 className="mt-2 text-3xl font-semibold">{data.revision.title}</h1>
        <p className="mt-3 max-w-3xl text-slate-200">{data.revision.summary}</p>
        <dl className="mt-5 flex flex-wrap gap-6 text-sm">
          <div>
            <dt className="text-slate-400">Estado del curso</dt>
            <dd>{data.course.status}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Estado de autoría</dt>
            <dd>{data.revision.authoring_status}</dd>
          </div>
          <div>
            <dt className="text-slate-400">Revisión estructural</dt>
            <dd>Número {data.revision.number}</dd>
          </div>
        </dl>
      </header>
      <nav
        aria-label="Secciones del curso"
        className="mt-5 flex flex-wrap gap-3"
      >
        <Link
          className="rounded-lg border px-4 py-2 font-medium"
          href={`/organizaciones/${slug}/cursos/${courseSlug}/estructura`}
        >
          Editar estructura
        </Link>
        <Link
          className="rounded-lg border px-4 py-2 font-medium"
          href={`/organizaciones/${slug}/cursos/${courseSlug}/revision`}
        >
          Abrir revisión
        </Link>
      </nav>
      <CourseMetadataForm
        canManage={canManage}
        courseSlug={courseSlug}
        key={data.revision.lock_version}
        revision={data.revision}
        slug={slug}
      />
      <div className="mt-7 grid gap-6 lg:grid-cols-2">
        <AlignmentEditor
          canManage={canManage}
          courseSlug={courseSlug}
          objectives={data.objectives}
          outline={data.outline}
          slug={slug}
          subjects={data.subjects}
        />
        <ReviewPanel
          canApprove={capabilities.includes('course.authoring.approve')}
          canReview={capabilities.includes('course.authoring.review')}
          canSubmit={capabilities.includes('course.authoring.submit')}
          courseSlug={courseSlug}
          readiness={data.readiness}
          revision={data.revision}
          slug={slug}
        />
      </div>
      <section className="mt-7 rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-xl font-semibold">Outline</h2>
        <p className="mt-2 text-slate-600">
          {data.outline.modules.length} módulos en la revisión actual.
        </p>
        <ol className="mt-4 space-y-3">
          {data.outline.modules.map((module) => (
            <li className="rounded-lg bg-slate-50 p-4" key={module.id}>
              <strong>{module.title}</strong>
              <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
                {module.units.map((unit) => (
                  <li key={unit.id}>
                    {unit.title} — Contenido académico pendiente
                  </li>
                ))}
              </ul>
            </li>
          ))}
        </ol>
      </section>
      <section className="mt-7 rounded-xl border border-slate-200 bg-white p-6">
        <h2 className="text-xl font-semibold">Historial de transiciones</h2>
        <ol className="mt-4 space-y-3">
          {data.transitions.map((transition) => (
            <li
              className="border-l-2 border-slate-300 pl-4"
              key={transition.id}
            >
              <strong>{transition.to_status}</strong> por{' '}
              {transition.actor_display}
              {transition.note ? (
                <p className="text-slate-700">{transition.note}</p>
              ) : null}
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
