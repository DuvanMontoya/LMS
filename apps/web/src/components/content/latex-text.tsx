'use client';

import { Fragment } from 'react';

import { MathJaxFormula } from '@/components/content/mathjax-formula';
import { cn } from '@/lib/utils';

const LATEX_SEGMENT = /(\$\$[\s\S]+?\$\$|\$[^$\n]+?\$)/g;

export function LatexText({
  className,
  value,
}: Readonly<{ className?: string; value: string }>) {
  const parts = value.split(LATEX_SEGMENT).filter(Boolean);
  return (
    <span className={cn('latex-text', className)}>
      {parts.map((part, index) => {
        const display = part.startsWith('$$') && part.endsWith('$$');
        const inline = !display && part.startsWith('$') && part.endsWith('$');
        if (!display && !inline)
          return <Fragment key={`${index}-${part}`}>{part}</Fragment>;
        const latex = part.slice(display ? 2 : 1, display ? -2 : -1).trim();
        return latex ? (
          <MathJaxFormula
            display={display}
            key={`${index}-${part}`}
            latex={latex}
          />
        ) : null;
      })}
    </span>
  );
}
