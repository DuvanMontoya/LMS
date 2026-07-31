/* eslint-disable @typescript-eslint/no-explicit-any */
/* Generated from schemas/publication/course-release-v2.schema.json. Do not edit. */

export type Node =
  ImageAsset | AudioAsset | VideoAsset | DownloadAsset | LegacyNode;
export type NodeId = string;
export type AssetVersionId = string;
export type PlainText = string;

export interface LMSImmutableCourseReleaseVersion2 {
  schema_version: 2;
  release_number: number;
  previous_release_digest: null | string;
  organization: {
    id: string;
    slug: string;
  };
  course: {
    id: string;
    slug: string;
    source_revision_id: string;
    source_revision_number: number;
    title: string;
    subtitle?: string | null;
    summary: string;
    description: string;
    language_code: string;
    estimated_duration_minutes: number | null;
    [k: string]: any;
  };
  curriculum: {
    subjects: {
      [k: string]: any;
    }[];
    learning_objectives: {
      [k: string]: any;
    }[];
    [k: string]: any;
  };
  /**
   * @maxItems 500
   */
  modules: {
    id: string;
    title: string;
    description: string;
    position: number;
    /**
     * @maxItems 5000
     */
    units: {
      id: string;
      title: string;
      summary: string;
      estimated_duration_minutes: number | null;
      position: number;
      topics: {
        [k: string]: any;
      }[];
      learning_objectives: {
        [k: string]: any;
      }[];
      content: {
        schema_version: 2;
        document_version: number;
        digest: string;
        character_count: number;
        word_count: number;
        node_count: number;
        document: LMSUnitAcademicDocumentVersion2;
        [k: string]: any;
      };
      [k: string]: any;
    }[];
    [k: string]: any;
  }[];
  assets: {
    asset_version_id: string;
    asset_id: string;
    kind: 'image' | 'document' | 'audio' | 'video' | 'dataset' | 'caption';
    sha256: string;
    detected_mime_type: string;
    size_bytes: number;
    metadata: {
      [k: string]: any;
    };
    variants: {
      role: string;
      mime_type: string;
      sha256: string;
      width: number | null;
      height: number | null;
      duration_milliseconds: number | null;
    }[];
  }[];
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

export type CourseReleaseSnapshotV2 = LMSImmutableCourseReleaseVersion2;
