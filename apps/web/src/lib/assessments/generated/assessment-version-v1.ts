/* Generated from schemas/assessment/assessment-version-v1.schema.json. Do not edit. */
/* eslint-disable @typescript-eslint/no-explicit-any */

export type QuestionPublicPayloadV1 = {
  [k: string]: any;
} & {
  [k: string]: any;
} & {
  [k: string]: any;
} & {
  [k: string]: any;
} & {
  [k: string]: any;
};
export type QuestionPublicPayloadV11 = {
  [k: string]: any;
} & {
  [k: string]: any;
} & {
  [k: string]: any;
} & {
  [k: string]: any;
} & {
  [k: string]: any;
};

export interface AssessmentVersionPublicSnapshotV1 {
  schema_version: 1;
  assessment: {
    id: string;
    slug: string;
    title: string;
    description: string;
  };
  settings: {
    time_limit_minutes: number | null;
    attempt_limit: number | null;
    pass_basis_points: number;
    shuffle_sections: boolean;
    shuffle_items: boolean;
    feedback_mode: 'none' | 'score_only' | 'full_after_grading';
  };
  /**
   * @maxItems 500
   */
  objectives: Objective[];
  /**
   * @minItems 0
   * @maxItems 100
   */
  sections: {
    id: string;
    title: string;
    instructions: string;
    position: number;
    /**
     * @minItems 1
     * @maxItems 500
     */
    items: [
      {
        id: string;
        question_version_id: string;
        position: number;
        points: string;
        required: boolean;
        question: QuestionPublicPayloadV1;
        /**
         * @maxItems 100
         */
        objectives: Objective[];
      },
      ...{
        id: string;
        question_version_id: string;
        position: number;
        points: string;
        required: boolean;
        question: QuestionPublicPayloadV1;
        /**
         * @maxItems 100
         */
        objectives: Objective[];
      }[],
    ];
  }[];
  /**
   * @maxItems 100
   */
  pools?: {
    id: string;
    title: string;
    instructions: string;
    position: number;
    selection_count: number;
    points_per_item: string;
    selection_strategy: 'random_without_replacement';
    shuffle_selected: boolean;
    /**
     * @minItems 2
     * @maxItems 200
     */
    candidates: [
      {
        id: string;
        question_version_id: string;
        position: number;
        question: QuestionPublicPayloadV11;
      },
      {
        id: string;
        question_version_id: string;
        position: number;
        question: QuestionPublicPayloadV11;
      },
      ...{
        id: string;
        question_version_id: string;
        position: number;
        question: QuestionPublicPayloadV11;
      }[],
    ];
  }[];
}
export interface Objective {
  id: string;
  code: string;
  statement: string;
}
