import { ArrowLeft, ArrowRight, BookOpenText } from 'lucide-react';
import Link from 'next/link';

import { AcademicDocument } from '@/components/content/academic-document';
import { PageHeader } from '@/components/platform/page-header';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { getLibraryUnit } from '@/lib/publishing/server';

export default async function LibraryUnitPage({
  params,
}: Readonly<{
  params: Promise<{ courseSlug: string; slug: string; unitId: string }>;
}>) {
  const { courseSlug, slug, unitId } = await params;
  const data = await getLibraryUnit(slug, courseSlug, unitId);
  const { navigation } = data.payload;
  const base = `/organizaciones/${slug}/biblioteca/${courseSlug}`;
  return (
    <main
      aria-live="polite"
      className="academic-page"
      data-release-number={data.payload.release_number}
    >
      <PageHeader
        actions={
          <Badge variant="outline">
            Unidad {navigation.position} de {navigation.total}
          </Badge>
        }
        breadcrumbs={[
          { href: `/organizaciones/${slug}`, label: data.organization.name },
          { href: `/organizaciones/${slug}/biblioteca`, label: 'Biblioteca' },
          { href: base, label: data.course.title },
          { label: data.unit.title },
        ]}
        description={data.unit.summary}
        eyebrow={`Módulo ${data.unit.module.position} · ${data.unit.module.title}`}
        title={data.unit.title}
      />
      <div className="mt-5 grid gap-6 xl:grid-cols-[minmax(0,1fr)_18rem]">
        <article className="min-w-0 border">
          <header className="flex flex-wrap gap-2 border-b bg-muted/15 px-5 py-3">
            {data.unit.topics.map((topic) => (
              <Badge key={topic.id} variant="outline">
                {topic.title}
              </Badge>
            ))}
          </header>
          <div className="px-5 py-6 sm:px-8 lg:px-12">
            <AcademicDocument document={data.unit.content.document} />
          </div>
        </article>
        <aside className="grid content-start gap-4">
          <section className="border p-5">
            <div className="flex items-center gap-2">
              <BookOpenText className="size-4 text-primary" />
              <h2 className="font-semibold">Objetivos</h2>
            </div>
            <ul className="mt-3 space-y-3 text-sm">
              {data.unit.learning_objectives.map((objective) => (
                <li
                  className="border-l-2 border-primary pl-3"
                  key={objective.id}
                >
                  {objective.statement}
                </li>
              ))}
            </ul>
          </section>
          <Button asChild variant="outline">
            <Link href={base}>Volver al contenido del curso</Link>
          </Button>
        </aside>
      </div>
      <nav
        aria-label="Navegación entre unidades"
        className="mt-6 grid gap-3 border-t pt-5 sm:grid-cols-2"
      >
        {navigation.previous ? (
          <Button
            asChild
            className="h-auto justify-start py-3"
            variant="outline"
          >
            <Link href={`${base}/unidades/${navigation.previous.id}`}>
              <ArrowLeft data-icon="inline-start" />
              <span className="min-w-0 text-left">
                <span className="block text-xs text-muted-foreground">
                  Anterior · {navigation.previous.module_title}
                </span>
                <span className="block truncate">
                  {navigation.previous.title}
                </span>
              </span>
            </Link>
          </Button>
        ) : (
          <span />
        )}
        {navigation.next ? (
          <Button asChild className="h-auto justify-end py-3" variant="outline">
            <Link href={`${base}/unidades/${navigation.next.id}`}>
              <span className="min-w-0 text-right">
                <span className="block text-xs text-muted-foreground">
                  Siguiente · {navigation.next.module_title}
                </span>
                <span className="block truncate">{navigation.next.title}</span>
              </span>
              <ArrowRight data-icon="inline-end" />
            </Link>
          </Button>
        ) : null}
      </nav>
      <p className="mt-4 text-center text-xs text-muted-foreground">
        Lectura del release {data.payload.release_number}; no se guarda
        progreso.
      </p>
    </main>
  );
}
