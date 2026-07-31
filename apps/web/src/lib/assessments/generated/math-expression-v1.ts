/* Generated from schemas/assessment/math-expression-v1.schema.json. Do not edit. */
/* eslint-disable @typescript-eslint/no-explicit-any */

export type BlockNode =
  | Paragraph
  | Heading
  | BulletList
  | OrderedList
  | Blockquote
  | HorizontalRule
  | PedagogicalBlock
  | DisplayMath
  | CodeBlock
  | Table;
export type NodeId = string;
export type InlineNode = Text | InlineMath | HardBreak;
export type Mark =
  | {
      type: 'bold';
    }
  | {
      type: 'italic';
    }
  | {
      type: 'code';
    }
  | {
      type: 'link';
      attrs: {
        href: string;
        title?: string;
      };
    };
/**
 * @maxItems 5000
 */
export type InlineContent = InlineNode[];
export type BlockquoteChildNode =
  | Paragraph
  | Heading
  | BulletList
  | OrderedList
  | HorizontalRule
  | PedagogicalBlock
  | DisplayMath
  | CodeBlock
  | Table;
export type PedagogicalChildNode =
  | Paragraph
  | Heading
  | BulletList
  | OrderedList
  | Blockquote
  | HorizontalRule
  | DisplayMath
  | CodeBlock
  | Table;
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
    prompt: LMSUnitAcademicDocumentVersion1;
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
 * Portable canonical contract for one course unit academic document.
 */
export interface LMSUnitAcademicDocumentVersion1 {
  type: 'doc';
  /**
   * @minItems 1
   * @maxItems 1000
   */
  content: [BlockNode, ...BlockNode[]];
}
export interface Paragraph {
  type: 'paragraph';
  attrs: BlockAttrs;
  content?: InlineContent;
}
export interface BlockAttrs {
  nodeId: NodeId;
}
export interface Text {
  type: 'text';
  text: string;
  /**
   * @maxItems 4
   */
  marks?:
    [] | [Mark] | [Mark, Mark] | [Mark, Mark, Mark] | [Mark, Mark, Mark, Mark];
}
export interface InlineMath {
  type: 'inlineMath';
  attrs: {
    nodeId: NodeId;
    latex: string;
  };
}
export interface HardBreak {
  type: 'hardBreak';
}
export interface Heading {
  type: 'heading';
  attrs: {
    nodeId: NodeId;
    level: 2 | 3 | 4;
  };
  content?: InlineContent;
}
export interface BulletList {
  type: 'bulletList';
  attrs: BlockAttrs;
  /**
   * @minItems 1
   * @maxItems 500
   */
  content: [ListItem, ...ListItem[]];
}
export interface ListItem {
  type: 'listItem';
  attrs: BlockAttrs;
  /**
   * @minItems 1
   * @maxItems 100
   */
  content: [
    Paragraph | Heading | BulletList | OrderedList,
    ...(Paragraph | Heading | BulletList | OrderedList)[],
  ];
}
export interface OrderedList {
  type: 'orderedList';
  attrs: {
    nodeId: NodeId;
    start: number;
  };
  /**
   * @minItems 1
   * @maxItems 500
   */
  content: [ListItem, ...ListItem[]];
}
export interface Blockquote {
  type: 'blockquote';
  attrs: BlockAttrs;
  /**
   * @minItems 1
   * @maxItems 250
   */
  content: [BlockquoteChildNode, ...BlockquoteChildNode[]];
}
export interface HorizontalRule {
  type: 'horizontalRule';
  attrs: BlockAttrs;
}
export interface PedagogicalBlock {
  type: 'pedagogicalBlock';
  attrs: {
    nodeId: NodeId;
    kind:
      | 'definition'
      | 'theorem'
      | 'lemma'
      | 'proposition'
      | 'corollary'
      | 'proof'
      | 'example'
      | 'counterexample'
      | 'remark'
      | 'warning'
      | 'summary';
    title?: string;
  };
  /**
   * @minItems 1
   * @maxItems 250
   */
  content: [PedagogicalChildNode, ...PedagogicalChildNode[]];
}
export interface DisplayMath {
  type: 'displayMath';
  attrs: {
    nodeId: NodeId;
    latex: string;
    label?: string;
  };
}
export interface CodeBlock {
  type: 'codeBlock';
  attrs: {
    nodeId: NodeId;
    language:
      | 'plaintext'
      | 'python'
      | 'javascript'
      | 'typescript'
      | 'json'
      | 'sql'
      | 'latex';
    code: string;
    caption?: string;
  };
}
export interface Table {
  type: 'table';
  attrs: {
    nodeId: NodeId;
    caption: string;
  };
  /**
   * @minItems 1
   * @maxItems 100
   */
  content: [HeaderRow | BodyRow, ...(HeaderRow | BodyRow)[]];
}
export interface HeaderRow {
  type: 'tableRow';
  attrs: BlockAttrs;
  /**
   * @minItems 1
   * @maxItems 20
   */
  content:
    | [TableHeader]
    | [TableHeader, TableHeader]
    | [TableHeader, TableHeader, TableHeader]
    | [TableHeader, TableHeader, TableHeader, TableHeader]
    | [TableHeader, TableHeader, TableHeader, TableHeader, TableHeader]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ]
    | [
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
        TableHeader,
      ];
}
export interface TableHeader {
  type: 'tableHeader';
  attrs: {
    nodeId: NodeId;
    colspan: 1;
    rowspan: 1;
    colwidth: null;
  };
  /**
   * @minItems 1
   * @maxItems 20
   */
  content:
    | [Paragraph]
    | [Paragraph, Paragraph]
    | [Paragraph, Paragraph, Paragraph]
    | [Paragraph, Paragraph, Paragraph, Paragraph]
    | [Paragraph, Paragraph, Paragraph, Paragraph, Paragraph]
    | [Paragraph, Paragraph, Paragraph, Paragraph, Paragraph, Paragraph]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ];
}
export interface BodyRow {
  type: 'tableRow';
  attrs: BlockAttrs;
  /**
   * @minItems 1
   * @maxItems 20
   */
  content:
    | [TableCell]
    | [TableCell, TableCell]
    | [TableCell, TableCell, TableCell]
    | [TableCell, TableCell, TableCell, TableCell]
    | [TableCell, TableCell, TableCell, TableCell, TableCell]
    | [TableCell, TableCell, TableCell, TableCell, TableCell, TableCell]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ]
    | [
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
        TableCell,
      ];
}
export interface TableCell {
  type: 'tableCell';
  attrs: {
    nodeId: NodeId;
    colspan: 1;
    rowspan: 1;
    colwidth: null;
  };
  /**
   * @minItems 1
   * @maxItems 20
   */
  content:
    | [Paragraph]
    | [Paragraph, Paragraph]
    | [Paragraph, Paragraph, Paragraph]
    | [Paragraph, Paragraph, Paragraph, Paragraph]
    | [Paragraph, Paragraph, Paragraph, Paragraph, Paragraph]
    | [Paragraph, Paragraph, Paragraph, Paragraph, Paragraph, Paragraph]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ]
    | [
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
        Paragraph,
      ];
}
