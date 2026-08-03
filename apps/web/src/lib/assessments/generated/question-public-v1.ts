/* Generated from schemas/assessment/question-public-v1.schema.json. Do not edit. */
/* eslint-disable @typescript-eslint/no-explicit-any */

export type QuestionPublicPayloadV1 = {
  [k: string]: any;
} & {
  schema_version: 1;
  type:
    | 'single_choice'
    | 'multiple_choice'
    | 'true_false'
    | 'numeric'
    | 'short_text'
    | 'long_text'
    | 'ordering'
    | 'matching'
    | 'mathematical_expression';
  prompt: LMSUnitAcademicDocumentVersion2;
  /**
   * @minItems 2
   * @maxItems 100
   */
  options?: [Option, Option, ...Option[]];
  /**
   * @minItems 1
   * @maxItems 100
   */
  left?: [Option, ...Option[]];
  /**
   * @minItems 1
   * @maxItems 100
   */
  right?: [Option, ...Option[]];
  true_label?: string;
  false_label?: string;
  response_placeholder?: string;
  unit?: string;
  /**
   * @maxItems 10
   */
  allowed_symbols?:
    | []
    | [string]
    | [string, string]
    | [string, string, string]
    | [string, string, string, string]
    | [string, string, string, string, string]
    | [string, string, string, string, string, string]
    | [string, string, string, string, string, string, string]
    | [string, string, string, string, string, string, string, string]
    | [string, string, string, string, string, string, string, string, string]
    | [
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
      ];
  /**
   * @maxItems 7
   */
  allowed_functions?:
    | []
    | ['Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs']
    | [
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
      ]
    | [
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
      ]
    | [
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
      ]
    | [
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
      ]
    | [
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
      ]
    | [
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
        'Sin' | 'Cos' | 'Tan' | 'Exp' | 'Ln' | 'Log' | 'Abs',
      ];
  response_guidance?: string;
  maximum_latex_length?: number;
};
export type Node =
  ImageAsset | AudioAsset | VideoAsset | DownloadAsset | LegacyNode;
export type NodeId = string;
export type AssetVersionId = string;
export type PlainText = string;

/**
 * Canonical semantic unit content with immutable academic asset references.
 */
export interface LMSUnitAcademicDocumentVersion2 {
  type: 'doc';
  /**
   * @minItems 1
   * @maxItems 1000
   */
  content: [Node, ...Node[]];
}
export interface ImageAsset {
  type: 'imageAsset';
  attrs: {
    [k: string]: any;
  };
}
export interface AudioAsset {
  type: 'audioAsset';
  attrs: {
    nodeId: NodeId;
    assetVersionId: AssetVersionId;
    title: string;
    transcript: string;
    caption: PlainText;
  };
}
export interface VideoAsset {
  type: 'videoAsset';
  attrs: {
    [k: string]: any;
  };
}
export interface DownloadAsset {
  type: 'documentAsset' | 'datasetAsset';
  attrs: {
    nodeId: NodeId;
    assetVersionId: AssetVersionId;
    label: string;
    description: PlainText;
  };
}
export interface LegacyNode {
  type: string;
  attrs?: {
    [k: string]: any;
  };
  /**
   * @maxItems 5000
   */
  content?: Node[];
  text?: string;
  /**
   * @maxItems 4
   */
  marks?:
    | []
    | [
        {
          [k: string]: any;
        },
      ]
    | [
        {
          [k: string]: any;
        },
        {
          [k: string]: any;
        },
      ]
    | [
        {
          [k: string]: any;
        },
        {
          [k: string]: any;
        },
        {
          [k: string]: any;
        },
      ]
    | [
        {
          [k: string]: any;
        },
        {
          [k: string]: any;
        },
        {
          [k: string]: any;
        },
        {
          [k: string]: any;
        },
      ];
  [k: string]: any;
}
export interface Option {
  id: string;
  label: string;
  math_latex?: string;
  media?: ChoiceMedia;
}
export interface ChoiceMedia {
  asset_version_id: string;
  kind: 'image';
  alt_text: string;
  caption?: string;
  long_description?: string;
}
