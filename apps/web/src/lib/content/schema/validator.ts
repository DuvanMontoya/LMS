import Ajv2020, { type ErrorObject } from 'ajv/dist/2020';

import type { LMSUnitAcademicDocumentVersion1 } from '../generated/unit-document-v1';
import schema from '../generated/unit-document-v1.schema.json';

const ajv = new Ajv2020({
  allErrors: true,
  allowUnionTypes: false,
  strict: true,
  validateFormats: false,
});
const validateDocument = ajv.compile<LMSUnitAcademicDocumentVersion1>(schema);

export type ContentValidationResult =
  | { valid: true; document: LMSUnitAcademicDocumentVersion1 }
  | { valid: false; errors: readonly ErrorObject[]; message: string };

export function validateContentDocument(
  value: unknown,
): ContentValidationResult {
  if (validateDocument(value)) return { document: value, valid: true };
  const errors = validateDocument.errors ?? [];
  const message = validationMessage(errors);
  return {
    errors,
    message: message || 'El documento no cumple el contrato semántico.',
    valid: false,
  };
}

function validationMessage(errors: readonly ErrorObject[]): string {
  const useful = errors.filter((error) => error.keyword !== 'oneOf');
  const source = useful.length ? useful : errors;
  const messages = source.map((error) => {
    const path = error.instancePath || 'Documento';
    if (error.keyword === 'additionalProperties') {
      const property = String(error.params.additionalProperty ?? '');
      return `${path}: contiene una propiedad no admitida${property ? ` (${property})` : ''}`;
    }
    if (error.keyword === 'required') {
      const property = String(error.params.missingProperty ?? '');
      return `${path}: falta el dato obligatorio${property ? ` «${property}»` : ''}`;
    }
    if (error.keyword === 'const')
      return `${path}: usa un tipo de contenido no admitido`;
    if (error.keyword === 'type')
      return `${path}: tiene un formato incompatible`;
    if (error.keyword === 'maxLength')
      return `${path}: supera la longitud permitida`;
    return `${path}: ${error.message ?? 'valor inválido'}`;
  });
  return (
    [...new Set(messages)].slice(0, 3).join(' · ') ||
    'El documento no cumple el contrato semántico.'
  );
}

export function assertContentDocument(
  value: unknown,
): asserts value is LMSUnitAcademicDocumentVersion1 {
  const result = validateContentDocument(value);
  if (!result.valid) throw new Error(result.message);
}

export function safeContentHref(value: unknown): value is string {
  if (typeof value !== 'string' || !value || value.length > 2048) return false;
  if (/[\u0000-\u001f\u007f\\]/.test(value) || value.startsWith('//'))
    return false;
  if (value.startsWith('#')) return value.length > 1 && !/\s/.test(value);
  if (value.startsWith('/')) return true;
  try {
    const parsed = new URL(value);
    return (
      ['http:', 'https:'].includes(parsed.protocol) &&
      Boolean(parsed.hostname) &&
      !parsed.username &&
      !parsed.password
    );
  } catch {
    return false;
  }
}

const unsafeMath =
  /(?:\\(?:require|style|class|cssId|htmlClass|htmlId|htmlStyle|href)\b|<\s*\/?\s*tex-html\b|javascript\s*:|data\s*:)/i;

export function contentSafetyError(value: unknown): string | undefined {
  const stack: unknown[] = [value];
  while (stack.length) {
    const current = stack.pop();
    if (!current || typeof current !== 'object' || Array.isArray(current))
      continue;
    const node = current as Record<string, unknown>;
    const attrs =
      node.attrs && typeof node.attrs === 'object' && !Array.isArray(node.attrs)
        ? (node.attrs as Record<string, unknown>)
        : undefined;
    if (
      ['inlineMath', 'displayMath'].includes(String(node.type)) &&
      typeof attrs?.latex === 'string' &&
      (/[\u0000-\u001f\u007f]/.test(attrs.latex) ||
        unsafeMath.test(attrs.latex))
    )
      return 'La fórmula contiene una capacidad no permitida.';
    if (Array.isArray(node.marks)) {
      for (const mark of node.marks) {
        if (!mark || typeof mark !== 'object' || Array.isArray(mark)) continue;
        const record = mark as Record<string, unknown>;
        const markAttrs =
          record.attrs &&
          typeof record.attrs === 'object' &&
          !Array.isArray(record.attrs)
            ? (record.attrs as Record<string, unknown>)
            : undefined;
        if (record.type === 'link' && !safeContentHref(markAttrs?.href))
          return 'El documento contiene un enlace no permitido.';
      }
    }
    if (Array.isArray(node.content)) stack.push(...node.content);
  }
  return undefined;
}
