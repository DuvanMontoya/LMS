import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import type { AssetAccessDescriptor } from '@/lib/assets/api';

import { SourceLessonRenderer } from './source-lesson-renderer';

vi.mock('@/components/content/mathjax-formula', () => ({
  MathJaxFormula: ({
    display,
    latex,
  }: {
    display?: boolean;
    latex: string;
  }) => (
    <span data-display={display ? 'true' : 'false'} data-testid="math">
      {latex}
    </span>
  ),
}));

function descriptor(sizeBytes = 100) {
  return {
    source: {
      expires_at: '2026-08-04T12:00:00Z',
      mime_type: 'text/plain',
      size_bytes: sizeBytes,
      url: 'http://assets.invalid/private-source',
    },
  } as unknown as AssetAccessDescriptor;
}

afterEach(() => vi.unstubAllGlobals());

describe('SourceLessonRenderer', () => {
  it('renders Markdown, GFM and math while omitting raw HTML', async () => {
    vi.stubGlobal(
      'fetch',
      vi
        .fn()
        .mockResolvedValue(
          new Response(
            '# Lección\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n$x^2$\n\n<script>inseguro</script>',
          ),
        ),
    );

    render(
      <SourceLessonRenderer
        descriptor={descriptor()}
        lessonKind="markdown_source"
        title="Lección Markdown"
      />,
    );

    expect(
      await screen.findByRole('heading', { name: 'Lección' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('table')).toBeInTheDocument();
    expect(screen.getByTestId('math')).toHaveTextContent('x^2');
    expect(screen.queryByText('inseguro')).not.toBeInTheDocument();
  });

  it('shows a complete LaTeX lesson without compiling TikZ', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(String.raw`\title{Lección fuente}
\begin{document}
\section{Inicio}
Contenido con $R_p$.
\begin{tikzpicture}
\draw (0,0) -- (1,1);
\end{tikzpicture}
\end{document}`),
      ),
    );

    render(
      <SourceLessonRenderer
        descriptor={descriptor()}
        lessonKind="latex_source"
        title="Archivo LaTeX"
      />,
    );

    expect(
      await screen.findByRole('heading', { name: 'Lección fuente' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Inicio' })).toBeInTheDocument();
    expect(
      screen.getByRole('img', {
        name: 'Contenido gráfico definido en el archivo LaTeX.',
      }),
    ).toBeInTheDocument();
    expect(screen.getByText('1 trazos interpretados')).toBeInTheDocument();
  });

  it('rejects a source descriptor above the 10 MiB reading limit', async () => {
    const fetch = vi.fn();
    vi.stubGlobal('fetch', fetch);

    render(
      <SourceLessonRenderer
        descriptor={descriptor(10 * 1024 * 1024 + 1)}
        lessonKind="markdown_source"
        title="Archivo grande"
      />,
    );

    expect(
      await screen.findByText(/no cumple el límite de lectura de 10 MiB/i),
    ).toBeInTheDocument();
    expect(fetch).not.toHaveBeenCalled();
  });
});
