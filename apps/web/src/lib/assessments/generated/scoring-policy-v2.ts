/* Generated from schemas/assessment/scoring-policy-v2.schema.json. Do not edit. */
/* eslint-disable @typescript-eslint/no-explicit-any */

export interface AssessmentScoringPolicyV2 {
  question_type:
    | 'single_choice'
    | 'multiple_choice'
    | 'true_false'
    | 'numeric'
    | 'short_text'
    | 'long_text'
    | 'ordering'
    | 'matching'
    | 'mathematical_expression';
  scoring_policy:
    | 'all_or_nothing'
    | 'manual'
    | 'exact_set'
    | 'proportional_with_penalty'
    | 'exact'
    | 'position_fraction'
    | 'adjacent_pair_fraction'
    | 'per_pair'
    | 'binary_tolerance'
    | 'banded_tolerance'
    | 'structural'
    | 'symbolic_common_domain';
  grading_payload: {
    [k: string]: any;
  };
  maximum_score: string;
  feedback_payload: {
    [k: string]: any;
  };
  scoring_engine_version: 2;
}
