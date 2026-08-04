/* Generated from schemas/publication/course-release-v5.schema.json. Do not edit. */

export type Unit = {
  [k: string]: any;
} & {
  id: string;
  title: string;
  summary: string;
  estimated_duration_minutes: number | null;
  lesson_kind:
    | 'document'
    | 'mediacms_video'
    | 'latex_source'
    | 'markdown_source'
    | 'pdf'
    | 'slides'
    | 'audio';
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
  };
  media: null | {
    provider: 'mediacms_lti';
    media_friendly_token: string;
  };
};
export type Node =
  ImageAsset | AudioAsset | VideoAsset | DownloadAsset | LegacyNode;
export type NodeId = string;
export type AssetVersionId = string;
export type PlainText = string;

export interface LMSImmutableCourseReleaseVersion5 {
  schema_version: 5;
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
    subtitle: string | null;
    summary: string;
    description: string;
    language_code: string;
    estimated_duration_minutes: number | null;
  };
  curriculum: {
    subjects: Reference[];
    topics: Reference[];
    concepts: Reference[];
    learning_objectives: Reference[];
    topic_concepts: {
      [k: string]: any;
    }[];
    objective_concepts: {
      [k: string]: any;
    }[];
    subject_prerequisites: {
      [k: string]: any;
    }[];
    concept_prerequisites: {
      [k: string]: any;
    }[];
  };
  completion_policy: {
    version: number;
    require_required_activities: boolean;
    minimum_grade_basis_points: number | null;
    minimum_attendance_basis_points: number | null;
  };
  grading_scheme: {
    categories: {
      id: string;
      code: string;
      title: string;
      position: number;
      weight_basis_points: number;
      activities: {
        activity_id: string;
        weight_basis_points: number;
        required: boolean;
      }[];
    }[];
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
    activities: Activity[];
    /**
     * @maxItems 5000
     */
    units: Unit[];
  }[];
  assets: {
    [k: string]: any;
  }[];
}
export interface Reference {
  [k: string]: any;
}
export interface Activity {
  id: string;
  type: 'lesson' | 'live_class' | 'assessment';
  title: string;
  summary: string;
  estimated_duration_minutes: number | null;
  position: number;
  required: boolean;
  completion_policy: {
    method: 'view' | 'manual' | 'attendance' | 'submission' | 'grade' | 'pass';
    minimum_attendance_basis_points: number | null;
    minimum_grade_basis_points: number | null;
  };
  availability_rules: {
    [k: string]: any;
  }[];
  learning_objectives: Reference[];
  binding: {
    [k: string]: any;
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

export type CourseReleaseSnapshotV5 = LMSImmutableCourseReleaseVersion5;
