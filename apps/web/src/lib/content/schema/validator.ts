import Ajv2020, { type ErrorObject } from 'ajv/dist/2020';

import type { LMSUnitAcademicDocumentVersion2 } from '../generated/unit-document-v2';
import schemaV1 from '../generated/unit-document-v1.schema.json';
import schemaV2 from '../generated/unit-document-v2.schema.json';

const ajv = new Ajv2020({
  allErrors: true,
  allowUnionTypes: false,
  strict: true,
  validateFormats: false,
});
const validateV1 = ajv.compile(schemaV1);
const validateDocument = ajv.compile<LMSUnitAcademicDocumentVersion2>(schemaV2);
const ASSET_NODES = new Set([
  'audioAsset',
  'datasetAsset',
  'documentAsset',
  'imageAsset',
  'videoAsset',
]);

function legacyProjection(value: unknown): unknown {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return value;
  const document = structuredClone(value) as Record<string, unknown>;
  if (!Array.isArray(document.content)) return document;
  document.content = document.content.map((node) => {
    if (
      node &&
      typeof node === 'object' &&
      !Array.isArray(node) &&
      ASSET_NODES.has(String((node as Record<string, unknown>).type))
    ) {
      const attrs = (node as Record<string, unknown>).attrs;
      const nodeId =
        attrs && typeof attrs === 'object' && !Array.isArray(attrs)
          ? (attrs as Record<string, unknown>).nodeId
          : undefined;
      return { attrs: { nodeId }, type: 'paragraph' };
    }
    return node;
  });
  return document;
}

export type ContentValidationResult =
  | { valid: true; document: LMSUnitAcademicDocumentVersion2 }
  | { valid: false; errors: readonly ErrorObject[]; message: string };

export function validateContentDocument(
  value: unknown,
): ContentValidationResult {
  if (validateDocument(value) && validateV1(legacyProjection(value)))
    return { document: value, valid: true };
  const errors = validateDocument.errors ?? validateV1.errors ?? [];
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
): asserts value is LMSUnitAcademicDocumentVersion2 {
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
