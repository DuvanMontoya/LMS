/* Generated from schemas/assessment/math-expression-response-v1.schema.json. Do not edit. */

export type Mathjson = number | string | [Mathjson, Mathjson, ...Mathjson[]];

export interface MathematicalExpressionResponseV1 {
  latex: string;
  mathjson: Mathjson;
}
