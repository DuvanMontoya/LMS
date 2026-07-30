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
   * @minItems 1
   * @maxItems 100
   */
  sections: [
    {
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
    },
    ...{
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
    }[],
  ];
}
export interface Objective {
  id: string;
  code: string;
  statement: string;
}
