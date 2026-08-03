import Ajv2020, { type ErrorObject } from 'ajv/dist/2020';

import contentSchema from '../generated/unit-document-v2.schema.json';
import mathExpressionResponseSchema from '../generated/math-expression-response-v1.schema.json';
import type { AssessmentResponseV1 } from '../generated/response-v1';
import responseSchema from '../generated/response-v1.schema.json';
import type { QuestionPublicPayloadV1 } from '../generated/question-public-v1';
import questionPublicSchema from '../generated/question-public-v1.schema.json';

const ajv = new Ajv2020({
  allErrors: true,
  coerceTypes: false,
  strict: false,
  validateFormats: false,
});
ajv.addSchema(contentSchema);
ajv.addSchema(mathExpressionResponseSchema);
const validatePublic =
  ajv.compile<QuestionPublicPayloadV1>(questionPublicSchema);
const validateResponse = ajv.compile<AssessmentResponseV1>(responseSchema);

export type AssessmentValidationResult<T> =
  | { valid: true; value: T }
  | { errors: readonly ErrorObject[]; message: string; valid: false };

function result<T>(
  validator: {
    (value: unknown): value is T;
    errors?: ErrorObject[] | null;
  },
  value: unknown,
): AssessmentValidationResult<T> {
  if (validator(value)) return { valid: true, value };
  const errors = validator.errors ?? [];
  return {
    errors,
    message:
      errors
        .filter((error) => error.keyword !== 'if')
        .slice(0, 3)
        .map(
          (error) =>
            `${error.instancePath || 'Respuesta'}: ${error.message ?? 'valor inválido'}`,
        )
        .join(' · ') || 'El dato no cumple el contrato de evaluación.',
    valid: false,
  };
}

export function validateQuestionPublic(
  value: unknown,
): AssessmentValidationResult<QuestionPublicPayloadV1> {
  return result(validatePublic, value);
}

export function validateAssessmentResponse(
  value: unknown,
): AssessmentValidationResult<AssessmentResponseV1> {
  return result(validateResponse, value);
}
