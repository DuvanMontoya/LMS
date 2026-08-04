import type { JSONContent } from '@tiptap/core';

const OPTIONAL_ATTRIBUTES: Readonly<Record<string, readonly string[]>> = {
  codeBlock: ['caption'],
  displayMath: ['label'],
  pedagogicalBlock: ['title'],
};

/**
 * Tiptap materializes optional attributes with a null default. The canonical
 * schema represents those values by omitting the property, so normalize only
 * those known optional attributes before validating or saving.
 */
export function canonicalEditorDocument(document: JSONContent): JSONContent {
  const normalized = structuredClone(document);

  function visit(node: JSONContent) {
    const optional = OPTIONAL_ATTRIBUTES[node.type ?? ''];
    if (optional && node.attrs) {
      for (const attribute of optional) {
        if (node.attrs[attribute] == null) delete node.attrs[attribute];
      }
    }
    node.content?.forEach(visit);
  }

  visit(normalized);
  return normalized;
}
