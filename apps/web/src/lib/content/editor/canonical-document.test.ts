import { describe, expect, it } from 'vitest';

import { validateContentDocument } from '../schema/validator';
import { canonicalEditorDocument } from './canonical-document';

describe('canonicalEditorDocument', () => {
  it('omits Tiptap null defaults for optional academic attributes', () => {
    const document = canonicalEditorDocument({
      type: 'doc',
      content: [
        {
          type: 'displayMath',
          attrs: {
            label: null,
            latex: String.raw`R_p=\sqrt{\frac{\Delta f}{f}R_e^2}`,
            nodeId: '00000000-0000-4000-8000-000000000001',
          },
        },
      ],
    });

    expect(document.content?.[0]?.attrs).not.toHaveProperty('label');
    const validation = validateContentDocument(document);
    if (!validation.valid) throw new Error(validation.message);
    expect(validation.valid).toBe(true);
  });

  it('preserves required null values such as table column widths', () => {
    const document = canonicalEditorDocument({
      type: 'tableCell',
      attrs: { colwidth: null, colspan: 1, nodeId: 'node', rowspan: 1 },
    });

    expect(document.attrs).toHaveProperty('colwidth', null);
  });
});
