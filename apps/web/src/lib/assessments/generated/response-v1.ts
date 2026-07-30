/* Generated from schemas/assessment/response-v1.schema.json. Do not edit. */
/* eslint-disable @typescript-eslint/no-explicit-any */

export type AssessmentResponseV1 = {
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
    | 'matching';
  value: any;
};
