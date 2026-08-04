import { describe, expect, it } from 'vitest';

import { parseLatexLesson } from './source-document';

describe('parseLatexLesson', () => {
  it('turns a complete LaTeX source into readable lesson blocks without compiling it', () => {
    const document = parseLatexLesson(String.raw`
      \documentclass{article}
      \title{Geometría proyectiva}
      \author{Robert Duan}
      \begin{document}
      \section{Introducción}
      La relación \(x^2+y^2=1\) describe el objeto.

      \begin{theorem}[Rigidez]
      Toda solución conserva su espectro.
      \end{theorem}

      \begin{equation}
      \lambda^2-2\lambda+1=0
      \end{equation}
      \end{document}
    `);

    expect(document.title).toBe('Geometría proyectiva');
    expect(document.author).toBe('Robert Duan');
    expect(document.blocks).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ text: 'Introducción', type: 'heading' }),
        expect.objectContaining({
          text: expect.stringContaining('$x^2+y^2=1$'),
          type: 'paragraph',
        }),
        expect.objectContaining({ text: 'Teorema — Rigidez', type: 'heading' }),
        expect.objectContaining({
          latex: expect.stringContaining('lambda'),
          type: 'math',
        }),
      ]),
    );
  });

  it('keeps real lesson tables and source listings readable', () => {
    const document = parseLatexLesson(String.raw`
      \begin{document}
      \begin{tabular}{ll}
      Concepto & Valor \\
      \midrule
      Radio & \(R_p\) \\
      \end{tabular}
      \begin{lstlisting}[language=Python,caption={Cálculo reproducible}]
      print("espectro")
      \end{lstlisting}
      \end{document}
    `);

    expect(document.blocks).toContainEqual({
      rows: [
        ['Concepto', 'Valor'],
        ['Radio', '$R_p$'],
      ],
      type: 'table',
    });
    expect(document.blocks).toContainEqual({
      caption: 'Cálculo reproducible',
      code: '      print("espectro")',
      language: 'Python',
      type: 'code',
    });
  });

  it('replaces TikZ with a visible non-compilation notice', () => {
    const document = parseLatexLesson(String.raw`
      \begin{document}
      \begin{tikzpicture}
      \draw (0,0) -- (1,1);
      \end{tikzpicture}
      \end{document}
    `);
    expect(document.blocks).toContainEqual({
      caption: 'Contenido gráfico definido en el archivo LaTeX.',
      type: 'visual',
    });
  });
});
