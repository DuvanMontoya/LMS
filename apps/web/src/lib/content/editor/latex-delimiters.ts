import type { Editor } from '@tiptap/core';

import { contentSafetyError } from '@/lib/content/schema/validator';

type LatexReplacement = {
  display: boolean;
  from: number;
  latex: string;
  to: number;
};

const inlineLatex = /(?<![\\$])\$(?!\$)([^$\n]+?)(?<!\\)\$(?!\$)/g;
const displayLatex = /^\s*\$\$([\s\S]+?)\$\$\s*$/;

function isSafeLatex(latex: string, display: boolean) {
  const maximum = display ? 12_000 : 2_048;
  return (
    latex.length > 0 &&
    latex.length <= maximum &&
    !contentSafetyError({
      attrs: { latex },
      type: display ? 'displayMath' : 'inlineMath',
    })
  );
}

/**
 * Converts author-written $...$ and $$...$$ delimiters into the canonical
 * semantic math nodes. The conversion is intentionally editor-side: Django
 * still accepts only the validated JSON schema and never parses LaTeX.
 */
export function normalizeLatexDelimiters(editor: Editor): boolean {
  const replacements: LatexReplacement[] = [];
  const { doc, schema } = editor.state;
  const displayType = schema.nodes.displayMath;
  const inlineType = schema.nodes.inlineMath;
  if (!displayType || !inlineType) return false;

  doc.descendants((node, position, parent, index) => {
    if (
      node.type.name === 'paragraph' &&
      parent?.canReplaceWith(index, index + 1, displayType)
    ) {
      const match = displayLatex.exec(node.textContent);
      const latex = match?.[1]?.trim() ?? '';
      if (match && isSafeLatex(latex, true)) {
        replacements.push({
          display: true,
          from: position,
          latex,
          to: position + node.nodeSize,
        });
        return false;
      }
    }

    if (
      !node.isText ||
      !node.text ||
      node.marks.some((mark) => mark.type.spec.code)
    )
      return true;

    for (const match of node.text.matchAll(inlineLatex)) {
      const latex = match[1]?.trim() ?? '';
      if (match.index === undefined || !isSafeLatex(latex, false)) continue;
      replacements.push({
        display: false,
        from: position + match.index,
        latex,
        to: position + match.index + match[0].length,
      });
    }
    return true;
  });

  if (!replacements.length) return false;

  const transaction = editor.state.tr;
  for (const replacement of replacements.sort(
    (left, right) => right.from - left.from,
  )) {
    const type = replacement.display ? displayType : inlineType;
    transaction.replaceWith(
      replacement.from,
      replacement.to,
      type.create({ latex: replacement.latex, nodeId: crypto.randomUUID() }),
    );
  }
  transaction.setMeta('latexDelimiterNormalization', true);
  editor.view.dispatch(transaction.scrollIntoView());
  return true;
}
