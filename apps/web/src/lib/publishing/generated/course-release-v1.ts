/* Generated from schemas/publication/course-release-v1.schema.json. Do not edit. */

export type Uuid = string;
export type Slug = string;
export type Position = number;
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

export interface LMSImmutableCourseReleaseVersion1 {
  schema_version: 1;
  release_number: number;
  previous_release_digest: null | string;
  organization: Organization;
  course: Course;
  curriculum: Curriculum;
  /**
   * @minItems 1
   * @maxItems 100
   */
  modules: [Module, ...Module[]];
}
export interface Organization {
  id: Uuid;
  slug: Slug;
}
export interface Course {
  id: Uuid;
  slug: Slug;
  source_revision_id: Uuid;
  source_revision_number: number;
  title: string;
  subtitle: null | string;
  summary: string;
  description: string;
  language_code: string;
  estimated_duration_minutes: null | number;
}
export interface Curriculum {
  /**
   * @minItems 1
   */
  subjects: [Subject, ...Subject[]];
  /**
   * @minItems 1
   * @maxItems 5000
   */
  learning_objectives: [LearningObjective, ...LearningObjective[]];
}
export interface Subject {
  id: Uuid;
  slug: Slug;
  name: string;
  alignment_type: 'primary' | 'supporting';
  position: Position;
}
export interface LearningObjective {
  id: Uuid;
  code: string;
  statement: string;
  description: string;
  cognitive_level: string;
  subject_id: Uuid;
  position: Position;
}
export interface Module {
  id: Uuid;
  title: string;
  description: string;
  position: Position;
  /**
   * @minItems 1
   */
  units: [Unit, ...Unit[]];
}
export interface Unit {
  id: Uuid;
  title: string;
  summary: string;
  estimated_duration_minutes: null | number;
  position: Position;
  topics: Topic[];
  /**
   * @minItems 1
   */
  learning_objectives: [UnitLearningObjective, ...UnitLearningObjective[]];
  content: UnitContent;
}
export interface Topic {
  id: Uuid;
  slug: Slug;
  title: string;
  subject_id: Uuid;
  subject_slug: Slug;
  position: Position;
}
export interface UnitLearningObjective {
  id: Uuid;
  code: string;
  statement: string;
  position: Position;
}
export interface UnitContent {
  schema_version: 1;
  document_version: number;
  digest: string;
  character_count: number;
  word_count: number;
  node_count: number;
  document: LMSUnitAcademicDocumentVersion1;
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

export type CourseReleaseSnapshotV1 = LMSImmutableCourseReleaseVersion1;
