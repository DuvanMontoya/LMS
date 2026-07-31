'use client';

import { ReactNodeViewRenderer } from '@tiptap/react';

import {
  AcademicCodeNodeView,
  AssetNodeView,
  DisplayMathNodeView,
  InlineMathNodeView,
} from '@/components/content/editor-node-views';

import {
  AcademicCodeBlock,
  AudioAsset,
  contentEditorExtensions,
  DisplayMath,
  DocumentAsset,
  DatasetAsset,
  ImageAsset,
  InlineMath,
  VideoAsset,
} from './extensions';

const interactiveNames = new Set([
  'audioAsset',
  'codeBlock',
  'datasetAsset',
  'displayMath',
  'documentAsset',
  'imageAsset',
  'inlineMath',
  'videoAsset',
]);

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
  ...[ImageAsset, AudioAsset, VideoAsset, DocumentAsset, DatasetAsset].map(
    (extension) =>
      extension.extend({
        addNodeView() {
          return ReactNodeViewRenderer(AssetNodeView);
        },
      }),
  ),
];
