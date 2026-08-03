/* Generated from schemas/assessment/question-definition-v1.schema.json. Do not edit. */
/* eslint-disable @typescript-eslint/no-explicit-any */

export type QuestionDefinitionV1 = {
  public?: {
    type?:
      | 'single_choice'
      | 'multiple_choice'
      | 'true_false'
      | 'numeric'
      | 'short_text'
      | 'long_text'
      | 'ordering'
      | 'matching'
      | 'mathematical_expression';
    [k: string]: any;
  };
  [k: string]: any;
} & {
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
  public: QuestionPublicPayloadV1;
  authoring?: Authoring;
  worked_solution?: LMSUnitAcademicDocumentVersion2;
  grading: {
    /**
     * @minItems 1
     * @maxItems 100
     */
    correct_option_ids?: [Identifier, ...Identifier[]];
    correct_value?: Decimal;
    tolerance?: NonNegativeDecimal;
    /**
     * @minItems 1
     * @maxItems 100
     */
    accepted_answers?: [string, ...string[]];
    case_sensitive?: boolean;
    /**
     * @minItems 2
     * @maxItems 100
     */
    correct_order?: [Identifier, Identifier, ...Identifier[]];
    correct_pairs?: {
      [k: string]: Identifier;
    };
    correct_boolean?: boolean;
    manual_required?: true;
    rubric?: string;
    expected_mathjson?: any;
    equivalence_strategy?: 'structural' | 'symbolic_common_domain';
    symbol_assumptions?: {
      [k: string]: any;
    };
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
  };
  feedback: {
    general?: string;
    correct?: string;
    incorrect?: string;
  };
};
export type QuestionPublicPayloadV1 = {
  [k: string]: any;
};
export type Node =
  ImageAsset | AudioAsset | VideoAsset | DownloadAsset | LegacyNode;
export type NodeId = string;
export type AssetVersionId = string;
export type PlainText = string;
export type Identifier = string;
export type Decimal = string;
export type NonNegativeDecimal = string;

export interface Authoring {
  framework?: 'icfes' | 'higher_education' | 'research' | 'other';
  difficulty?: 'foundational' | 'intermediate' | 'advanced' | 'expert';
  cognitive_process?:
    'understand' | 'apply' | 'analyze' | 'evaluate' | 'create';
  estimated_minutes?: number;
  /**
   * @maxItems 20
   */
  tags?:
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
      ]
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
        string,
      ]
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
        string,
        string,
      ]
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
        string,
        string,
        string,
      ]
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
        string,
        string,
        string,
        string,
      ]
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
        string,
        string,
        string,
        string,
        string,
      ]
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
        string,
        string,
        string,
        string,
        string,
        string,
      ]
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
        string,
        string,
        string,
        string,
        string,
        string,
        string,
      ]
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
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
      ]
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
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
        string,
      ]
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
  source_note?: string;
  choice_rationales?: {
    [k: string]: string;
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
