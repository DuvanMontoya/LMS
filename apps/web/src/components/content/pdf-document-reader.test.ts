import { describe, expect, it } from 'vitest';

import {
  isExpectedPdfCancellation,
  pdfRenderScale,
} from './pdf-document-reader';

describe('isExpectedPdfCancellation', () => {
  it.each(['AbortError', 'RenderingCancelledException'])(
    'recognizes %s as a normal PDF.js teardown',
    (name) => {
      const error = new Error('PDF reader stopped');
      error.name = name;

      expect(isExpectedPdfCancellation(error)).toBe(true);
    },
  );

  it('does not suppress an unexpected rendering failure', () => {
    expect(isExpectedPdfCancellation(new Error('Canvas failed'))).toBe(false);
  });
});

describe('pdfRenderScale', () => {
  it('fits a wide page to the available reader width at 100 percent zoom', () => {
    expect(pdfRenderScale(596, 351, 1)).toBeCloseTo(351 / 596);
  });

  it('keeps a small page at its natural size', () => {
    expect(pdfRenderScale(320, 900, 1)).toBe(1);
  });

  it('applies user zoom relative to the fitted width', () => {
    expect(pdfRenderScale(600, 300, 1.5)).toBe(0.75);
  });
});
