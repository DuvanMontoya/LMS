import { Award, ClipboardCheck } from 'lucide-react';
import Link from 'next/link';

import { cn } from '@/lib/utils';

export function LearnerAssessmentNavigation({
  active,
  slug,
}: Readonly<{ active: 'assessments' | 'grades'; slug: string }>) {
  const items = [
    {
      href: `/organizaciones/${slug}/evaluaciones/asignadas`,
      icon: ClipboardCheck,
      id: 'assessments',
      label: 'Evaluaciones',
    },
    {
      href: `/organizaciones/${slug}/evaluaciones/calificaciones`,
      icon: Award,
      id: 'grades',
      label: 'Calificaciones',
    },
  ] as const;

  return (
    <nav
      aria-label="Evaluaciones y calificaciones"
      className="learner-record-nav"
    >
      {items.map(({ href, icon: Icon, id, label }) => (
        <Link
          aria-current={active === id ? 'page' : undefined}
          className={cn(active === id && 'is-active')}
          href={href}
          key={id}
        >
          <Icon />
          {label}
        </Link>
      ))}
    </nav>
  );
}
