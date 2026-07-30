import { Editor } from '@tiptap/core';
import { describe, expect, it, vi } from 'vitest';

import { validateContentDocument } from '../schema/validator';
import { completeContentFixture } from '../test-fixtures';
import { contentEditorExtensions } from './extensions';

describe('Tiptap and canonical schema compatibility', () => {
  it('loads a valid document and produces a valid JSON round trip', () => {
    const contentError = vi.fn();
    const editor = new Editor({
      content: completeContentFixture(),
      enableContentCheck: true,
      extensions: contentEditorExtensions,
      onContentError: contentError,
    });
    expect(contentError).not.toHaveBeenCalled();
    const result = validateContentDocument(editor.getJSON());
    if (!result.valid)
      throw new Error(`${result.message}\n${JSON.stringify(editor.getJSON())}`);
    expect(result.valid).toBe(true);
    editor.destroy();
  });

  it('reports unsupported content instead of silently treating it as valid', () => {
    const contentError = vi.fn();
    const editor = new Editor({
      content: {
        type: 'doc',
        content: [{ type: 'unsupported-node', attrs: { secret: true } }],
      },
      enableContentCheck: true,
      extensions: contentEditorExtensions,
      onContentError: contentError,
    });
    expect(contentError).toHaveBeenCalled();
    editor.destroy();
  });

  it('serializes links with canonical attributes only', () => {
    const editor = new Editor({
      content: {
        type: 'doc',
        content: [
          {
            type: 'paragraph',
            attrs: { nodeId: '00000000-0000-4000-8000-000000000020' },
            content: [{ type: 'text', text: 'Fuente académica' }],
          },
        ],
      },
      enableContentCheck: true,
      extensions: contentEditorExtensions,
    });

    editor.commands.setTextSelection({ from: 1, to: 18 });
    expect(
      editor.commands.setLink({ href: 'https://example.test/fuente' }),
    ).toBe(true);

    const document = editor.getJSON();
    expect(document.content?.[0]?.content?.[0]?.marks).toEqual([
      {
        attrs: { href: 'https://example.test/fuente' },
        type: 'link',
      },
    ]);
    const result = validateContentDocument(document);
    if (!result.valid) throw new Error(result.message);
    expect(result.valid).toBe(true);
    editor.destroy();
  });
});
