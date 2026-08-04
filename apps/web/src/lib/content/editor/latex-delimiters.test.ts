import { Editor } from '@tiptap/core';
import { describe, expect, it } from 'vitest';

import { contentEditorExtensions } from './extensions';
import { normalizeLatexDelimiters } from './latex-delimiters';

describe('normalizeLatexDelimiters', () => {
  it('converts inline and display delimiters into canonical math nodes', () => {
    const editor = new Editor({
      content: {
        content: [
          {
            content: [{ type: 'text', text: 'Radio $R_p^2$ observado.' }],
            type: 'paragraph',
          },
          {
            content: [
              {
                type: 'text',
                text: String.raw`$$R_p=\sqrt{\frac{\Delta f}{f}R_e^2}$$`,
              },
            ],
            type: 'paragraph',
          },
        ],
        type: 'doc',
      },
      extensions: contentEditorExtensions,
    });

    expect(normalizeLatexDelimiters(editor)).toBe(true);
    const document = editor.getJSON();
    expect(document.content?.[0]?.content?.map((node) => node.type)).toEqual([
      'text',
      'inlineMath',
      'text',
    ]);
    expect(
      (document.content?.[0]?.content?.[1] as { attrs?: { latex?: string } })
        .attrs?.latex,
    ).toBe('R_p^2');
    expect(document.content?.[1]?.type).toBe('displayMath');
    expect(
      (document.content?.[1] as { attrs?: { latex?: string } }).attrs?.latex,
    ).toBe(String.raw`R_p=\sqrt{\frac{\Delta f}{f}R_e^2}`);
    editor.destroy();
  });

  it('leaves unsafe LaTeX as inert text', () => {
    const editor = new Editor({
      content: {
        content: [
          {
            content: [
              { type: 'text', text: String.raw`$\href{javascript:x}{y}$` },
            ],
            type: 'paragraph',
          },
        ],
        type: 'doc',
      },
      extensions: contentEditorExtensions,
    });

    expect(normalizeLatexDelimiters(editor)).toBe(false);
    expect(editor.getText()).toBe(String.raw`$\href{javascript:x}{y}$`);
    editor.destroy();
  });
});
