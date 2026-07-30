import { mergeAttributes, Node, type Extensions } from '@tiptap/core';
import {
  Table,
  TableCell,
  TableHeader,
  TableRow,
} from '@tiptap/extension-table';
import { UniqueID } from '@tiptap/extension-unique-id';
import StarterKit from '@tiptap/starter-kit';

import { safeContentHref } from '../schema/validator';

const idAttribute = {
  default: null,
  parseHTML: (element: HTMLElement) => element.dataset.nodeId ?? null,
  renderHTML: (attributes: Record<string, unknown>) =>
    attributes.nodeId ? { 'data-node-id': attributes.nodeId } : {},
};

export const PedagogicalBlock = Node.create({
  name: 'pedagogicalBlock',
  group: 'block',
  content: 'block+',
  defining: true,
  addAttributes() {
    return {
      kind: { default: 'definition' },
      nodeId: idAttribute,
      title: { default: null },
    };
  },
  parseHTML() {
    return [{ tag: 'aside[data-pedagogical-kind]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'aside',
      mergeAttributes(HTMLAttributes, {
        'data-pedagogical-kind': HTMLAttributes.kind,
      }),
      0,
    ];
  },
});

export const InlineMath = Node.create({
  name: 'inlineMath',
  group: 'inline',
  inline: true,
  atom: true,
  addAttributes() {
    return { latex: { default: '' }, nodeId: idAttribute };
  },
  parseHTML() {
    return [{ tag: 'span[data-inline-math]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'span',
      mergeAttributes(HTMLAttributes, { 'data-inline-math': '' }),
      HTMLAttributes.latex,
    ];
  },
});

export const DisplayMath = Node.create({
  name: 'displayMath',
  group: 'block',
  atom: true,
  addAttributes() {
    return {
      label: { default: null },
      latex: { default: '' },
      nodeId: idAttribute,
    };
  },
  parseHTML() {
    return [{ tag: 'div[data-display-math]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, { 'data-display-math': '' }),
      HTMLAttributes.latex,
    ];
  },
});

export const AcademicCodeBlock = Node.create({
  name: 'codeBlock',
  group: 'block',
  atom: true,
  addAttributes() {
    return {
      caption: { default: null },
      code: { default: '' },
      language: { default: 'plaintext' },
      nodeId: idAttribute,
    };
  },
  parseHTML() {
    return [{ tag: 'pre[data-academic-code]' }];
  },
  renderHTML({ HTMLAttributes }) {
    return [
      'pre',
      mergeAttributes(HTMLAttributes, { 'data-academic-code': '' }),
      ['code', {}, HTMLAttributes.code],
    ];
  },
});

const AcademicTable = Table.extend({
  addAttributes() {
    return {
      ...this.parent?.(),
      caption: { default: '' },
      nodeId: idAttribute,
    };
  },
});
const AcademicTableRow = TableRow.extend({
  addAttributes() {
    return { ...this.parent?.(), nodeId: idAttribute };
  },
});
const AcademicTableCell = TableCell.extend({
  addAttributes() {
    const attributes = { ...this.parent?.() };
    Reflect.deleteProperty(attributes, 'align');
    return { ...attributes, nodeId: idAttribute };
  },
});
const AcademicTableHeader = TableHeader.extend({
  addAttributes() {
    const attributes = { ...this.parent?.() };
    Reflect.deleteProperty(attributes, 'align');
    return { ...attributes, nodeId: idAttribute };
  },
});

const stableNodeTypes = [
  'paragraph',
  'heading',
  'bulletList',
  'orderedList',
  'listItem',
  'blockquote',
  'horizontalRule',
  'pedagogicalBlock',
  'inlineMath',
  'displayMath',
  'codeBlock',
  'table',
  'tableRow',
  'tableCell',
  'tableHeader',
];

export const contentEditorExtensions: Extensions = [
  StarterKit.configure({
    codeBlock: false,
    heading: { levels: [2, 3, 4] },
    link: {
      HTMLAttributes: {
        rel: 'noopener noreferrer',
        target: null,
      },
      autolink: false,
      defaultProtocol: 'https',
      isAllowedUri: safeContentHref,
      openOnClick: false,
      protocols: ['http', 'https'],
    },
    strike: false,
  }),
  PedagogicalBlock,
  InlineMath,
  DisplayMath,
  AcademicCodeBlock,
  AcademicTable.configure({ resizable: false }),
  AcademicTableRow,
  AcademicTableCell,
  AcademicTableHeader,
  UniqueID.configure({
    attributeName: 'nodeId',
    generateID: () => crypto.randomUUID(),
    types: stableNodeTypes,
  }),
];

export const emptyContentDocument = (): {
  content: Array<Record<string, unknown>>;
  type: 'doc';
} => ({
  content: [
    {
      attrs: { nodeId: crypto.randomUUID() },
      content: [],
      type: 'paragraph',
    },
  ],
  type: 'doc',
});

export function findDuplicateNodeIds(document: unknown): string[] {
  const seen = new Set<string>();
  const duplicates = new Set<string>();
  const stack: unknown[] = [document];
  while (stack.length) {
    const current = stack.pop();
    if (!current || typeof current !== 'object' || Array.isArray(current))
      continue;
    const record = current as Record<string, unknown>;
    const attrs = record.attrs;
    if (attrs && typeof attrs === 'object' && !Array.isArray(attrs)) {
      const nodeId = (attrs as Record<string, unknown>).nodeId;
      if (typeof nodeId === 'string') {
        if (seen.has(nodeId)) duplicates.add(nodeId);
        seen.add(nodeId);
      }
    }
    if (Array.isArray(record.content)) stack.push(...record.content);
  }
  return [...duplicates];
}
