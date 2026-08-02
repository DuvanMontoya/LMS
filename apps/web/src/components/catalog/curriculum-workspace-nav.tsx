import { BookOpen, GitBranch, Network, Target } from 'lucide-react';
import Link from 'next/link';

const sections = [
  { icon: BookOpen, label: 'Estructura', route: '' },
  { icon: Target, label: 'Objetivos', route: 'objetivos' },
  { icon: Network, label: 'Conceptos', route: 'conceptos' },
  { icon: GitBranch, label: 'Prerrequisitos', route: 'prerrequisitos' },
] as const;

export function CurriculumWorkspaceNav({
  current,
  slug,
}: Readonly<{
  current: (typeof sections)[number]['route'];
  slug: string;
}>) {
  return (
    <nav
      aria-label="Secciones del currículo"
      className="mt-5 flex gap-1 overflow-x-auto rounded-lg border bg-muted/20 p-1"
    >
      {sections.map(({ icon: Icon, label, route }) => {
        const active = route === current;
        return (
          <Link
            aria-current={active ? 'page' : undefined}
            className={`inline-flex min-h-9 shrink-0 items-center gap-2 rounded-md px-3 text-sm font-medium transition-colors ${
              active
                ? 'bg-background text-foreground shadow-xs'
                : 'text-muted-foreground hover:bg-background/70 hover:text-foreground'
            }`}
            href={`/organizaciones/${slug}/curriculo${route ? `/${route}` : ''}`}
            key={route}
          >
            <Icon className="size-4" />
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
