'use client';

import { ReactNodeViewRenderer } from '@tiptap/react';

import {
  AcademicCodeNodeView,
  DisplayMathNodeView,
  InlineMathNodeView,
} from '@/components/content/editor-node-views';

import {
  AcademicCodeBlock,
  contentEditorExtensions,
  DisplayMath,
  InlineMath,
} from './extensions';

const interactiveNames = new Set(['codeBlock', 'displayMath', 'inlineMath']);

export const interactiveContentEditorExtensions = [
  ...contentEditorExtensions.filter(
    (extension) => !interactiveNames.has(extension.name),
  ),
  AcademicCodeBlock.extend({
    addNodeView() {
      return ReactNodeViewRenderer(AcademicCodeNodeView);
    },
  }),
  DisplayMath.extend({
    addNodeView() {
      return ReactNodeViewRenderer(DisplayMathNodeView);
    },
  }),
  InlineMath.extend({
    addNodeView() {
      return ReactNodeViewRenderer(InlineMathNodeView);
    },
  }),
];
