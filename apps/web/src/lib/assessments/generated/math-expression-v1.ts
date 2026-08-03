/* Generated from schemas/assessment/math-expression-v1.schema.json. Do not edit. */
/* eslint-disable @typescript-eslint/no-explicit-any */

export type Node =
  ImageAsset | AudioAsset | VideoAsset | DownloadAsset | LegacyNode;
export type NodeId = string;
export type AssetVersionId = string;
export type PlainText = string;
/**
 * @maxItems 10
 */
export type Symbols =
  | []
  | [SymbolName]
  | [SymbolName, SymbolName]
  | [SymbolName, SymbolName, SymbolName]
  | [SymbolName, SymbolName, SymbolName, SymbolName]
  | [SymbolName, SymbolName, SymbolName, SymbolName, SymbolName]
  | [SymbolName, SymbolName, SymbolName, SymbolName, SymbolName, SymbolName]
  | [
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
    ]
  | [
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
    ]
  | [
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
    ]
  | [
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
      SymbolName,
    ];
export type SymbolName = string;
/**
 * @maxItems 7
 */
export type Functions =
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

export interface MathematicalExpressionQuestionDefinitionV1 {
  schema_version: 1;
  type: 'mathematical_expression';
  public: {
    schema_version: 1;
    type: 'mathematical_expression';
    prompt: LMSUnitAcademicDocumentVersion2;
    allowed_symbols: Symbols;
    allowed_functions: Functions;
    response_guidance: string;
    maximum_latex_length: number;
  };
  grading: {
    expected_mathjson: any;
    equivalence_strategy: 'structural' | 'symbolic_common_domain';
    symbol_assumptions: {
      /**
       * @maxItems 4
       */
      [k: string]:
        | []
        | ['real' | 'positive' | 'nonnegative' | 'integer']
        | [
            'real' | 'positive' | 'nonnegative' | 'integer',
            'real' | 'positive' | 'nonnegative' | 'integer',
          ]
        | [
            'real' | 'positive' | 'nonnegative' | 'integer',
            'real' | 'positive' | 'nonnegative' | 'integer',
            'real' | 'positive' | 'nonnegative' | 'integer',
          ]
        | [
            'real' | 'positive' | 'nonnegative' | 'integer',
            'real' | 'positive' | 'nonnegative' | 'integer',
            'real' | 'positive' | 'nonnegative' | 'integer',
            'real' | 'positive' | 'nonnegative' | 'integer',
          ];
    };
    allowed_symbols: Symbols;
    allowed_functions: Functions;
  };
  feedback: {
    general?: string;
    correct?: string;
    incorrect?: string;
  };
}
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
