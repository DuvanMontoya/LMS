import { describe, expect, it } from 'vitest';

import { parseTikzPreview } from './tikz-preview';

describe('parseTikzPreview', () => {
  it('interprets safe geometric primitives without executing TeX', () => {
    const result = parseTikzPreview(String.raw`
      \begin{tikzpicture}
      \draw[blue,thick] (0,0) -- (2,1) -- (3,0);
      \fill[red] (1,1) circle (0.2);
      \node at (2,1.4) {Vértice};
      \end{tikzpicture}
    `);

    expect(result.supportedStatements).toBe(3);
    expect(result.primitives).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ color: '#2563eb', kind: 'path' }),
        expect.objectContaining({ fill: '#dc2626', kind: 'circle' }),
        expect.objectContaining({ kind: 'label', text: 'Vértice' }),
      ]),
    );
  });

  it('does not claim unsupported PGFPlots instructions were rendered', () => {
    const result = parseTikzPreview(
      String.raw`\begin{axis}\addplot {x^2};\end{axis}`,
    );
    expect(result.supportedStatements).toBe(0);
    expect(result.primitives).toHaveLength(0);
  });
});
