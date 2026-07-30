import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { completeContentFixture } from '@/lib/content/test-fixtures';

import { AcademicDocument } from './academic-document';

describe('AcademicDocument', () => {
  it('uses explicit semantic mappings without stored HTML', () => {
    render(<AcademicDocument document={completeContentFixture()} />);
    expect(
      screen.getByRole('heading', { name: 'Funciones', level: 2 }),
    ).toBeInTheDocument();
    expect(screen.getByText('Definición')).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByText('Tabla de valores')).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: 'Copiar código' }),
    ).toBeInTheDocument();
    expect(
      document.querySelector<HTMLScriptElement>('script[data-lms-mathjax]')
        ?.src,
    ).toBe('http://localhost:3000/vendor/mathjax/tex-svg.js');
    expect(document.querySelector('script[src^="http"]')).toBeNull();
    const semanticNode = document.querySelector<HTMLElement>('[data-node-id]');
    expect(semanticNode).not.toBeNull();
    expect(semanticNode?.id).toBe(`node-${semanticNode?.dataset.nodeId}`);
  });
});
