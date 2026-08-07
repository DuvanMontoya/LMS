import {
  Mark,
  mergeAttributes,
  Node,
  nodeInputRule,
  type Extensions,
} from '@tiptap/core';
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

export const CanonicalLink = Mark.create({
  name: 'link',
  priority: 1000,
  inclusive: false,
  keepOnSplit: false,
  exitable: true,
  addAttributes() {
    return {
      href: {
        default: null,
        parseHTML: (element: HTMLElement) => element.getAttribute('href'),
      },
      title: {
        default: undefined,
        parseHTML: (element: HTMLElement) =>
          element.getAttribute('title') ?? undefined,
      },
    };
  },
  parseHTML() {
    return [
      {
        tag: 'a[href]',
        getAttrs: (element: HTMLElement) => {
          const href = element.getAttribute('href');
          if (!safeContentHref(href)) return false;
          const title = element.getAttribute('title');
          return { href, ...(title ? { title } : {}) };
        },
      },
    ];
  },
  renderHTML({ HTMLAttributes }) {
    const href = HTMLAttributes.href;
    if (!safeContentHref(href)) return ['span', {}, 0];
    const title =
      typeof HTMLAttributes.title === 'string' && HTMLAttributes.title
        ? HTMLAttributes.title
        : undefined;
    return [
      'a',
      mergeAttributes(
        { rel: 'noopener noreferrer' },
        { href, ...(title ? { title } : {}) },
      ),
      0,
    ];
  },
  addCommands() {
    return {
      setLink:
        (attributes) =>
        ({ commands }) => {
          if (!safeContentHref(attributes.href)) return false;
          const title =
            typeof attributes.title === 'string' && attributes.title
              ? attributes.title
              : undefined;
          return commands.setMark(this.name, {
            href: attributes.href,
            ...(title ? { title } : {}),
          });
        },
      toggleLink:
        (attributes) =>
        ({ commands }) => {
          if (!attributes) return commands.unsetMark(this.name);
          if (!safeContentHref(attributes.href)) return false;
          const title =
            typeof attributes.title === 'string' && attributes.title
              ? attributes.title
              : undefined;
          return commands.toggleMark(this.name, {
            href: attributes.href,
            ...(title ? { title } : {}),
          });
        },
      unsetLink:
        () =>
        ({ commands }) =>
          commands.unsetMark(this.name),
    };
  },
});

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
  addInputRules() {
    return [
      nodeInputRule({
        find: /(?<![\\$])\$(?!\$)[^$\n]+\$$/,
        getAttributes: (match) => ({
          latex: match[0].slice(1, -1),
          nodeId: crypto.randomUUID(),
        }),
        type: this.type,
      }),
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
  addInputRules() {
    return [
      nodeInputRule({
        find: /^\$\$(?!\$).+\$\$$/,
        getAttributes: (match) => ({
          latex: match[0].slice(2, -2),
          nodeId: crypto.randomUUID(),
        }),
        type: this.type,
      }),
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

function assetNode(
  name:
    | 'audioAsset'
    | 'datasetAsset'
    | 'documentAsset'
    | 'imageAsset'
    | 'videoAsset',
  attributes: Record<string, { default: unknown }>,
) {
  return Node.create({
    name,
    group: 'block',
    atom: true,
    isolating: true,
    addAttributes() {
      return {
        assetVersionId: { default: '' },
        nodeId: idAttribute,
        ...attributes,
      };
    },
    parseHTML() {
      return [{ tag: `figure[data-asset-node="${name}"]` }];
    },
    renderHTML({ HTMLAttributes }) {
      return [
        'figure',
        mergeAttributes(HTMLAttributes, {
          'data-asset-node': name,
          'data-asset-version-id': HTMLAttributes.assetVersionId,
        }),
        [
          'figcaption',
          {},
          String(
            HTMLAttributes.caption ??
              HTMLAttributes.title ??
              HTMLAttributes.label ??
              name,
          ),
        ],
      ];
    },
  });
}

export const ImageAsset = assetNode('imageAsset', {
  altText: { default: '' },
  caption: { default: '' },
  decorative: { default: false },
  displaySize: { default: 'large' },
});
export const AudioAsset = assetNode('audioAsset', {
  caption: { default: '' },
  title: { default: '' },
  transcript: { default: '' },
});
export const VideoAsset = assetNode('videoAsset', {
  caption: { default: '' },
  captionsAssetVersionId: { default: null },
  silent: { default: false },
  title: { default: '' },
  transcript: { default: '' },
});
export const DocumentAsset = assetNode('documentAsset', {
  description: { default: '' },
  label: { default: '' },
});
export const DatasetAsset = assetNode('datasetAsset', {
  description: { default: '' },
  label: { default: '' },
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
  'imageAsset',
  'audioAsset',
  'videoAsset',
  'documentAsset',
  'datasetAsset',
];

export const contentEditorExtensions: Extensions = [
  StarterKit.configure({
    codeBlock: false,
    heading: { levels: [2, 3, 4] },
    link: false,
    strike: false,
  }),
  CanonicalLink,
  PedagogicalBlock,
  InlineMath,
  DisplayMath,
  AcademicCodeBlock,
  AcademicTable.configure({ resizable: false }),
  AcademicTableRow,
  AcademicTableCell,
  AcademicTableHeader,
  ImageAsset,
  AudioAsset,
  VideoAsset,
  DocumentAsset,
  DatasetAsset,
  UniqueID.configure({
    attributeName: 'nodeId',
    generateID: () => crypto.randomUUID(),
    types: stableNodeTypes,
  }),
];

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
