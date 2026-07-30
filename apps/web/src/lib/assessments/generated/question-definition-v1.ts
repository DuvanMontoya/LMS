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
      | 'matching';
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
    | 'matching';
  public: QuestionPublicPayloadV1;
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
export type Identifier = string;
export type Decimal = string;
export type NonNegativeDecimal = string;
