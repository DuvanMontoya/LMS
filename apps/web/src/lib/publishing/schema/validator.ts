import Ajv2020, { type ErrorObject } from 'ajv/dist/2020';

import type { CourseReleaseSnapshotV1 } from '../generated/course-release-v1';
import releaseSchema from '../generated/course-release-v1.schema.json';
import contentSchema from '../generated/unit-document-v1.schema.json';

const ajv = new Ajv2020({
  allErrors: true,
  strict: true,
  coerceTypes: false,
  removeAdditional: false,
  useDefaults: false,
});
ajv.addFormat(
  'uuid',
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
);
ajv.addSchema(contentSchema);
const validateRelease = ajv.compile<CourseReleaseSnapshotV1>(releaseSchema);

export type ReleaseValidation =
  | { valid: true; snapshot: CourseReleaseSnapshotV1 }
  | { valid: false; errors: readonly ErrorObject[] };

export function validateReleaseSnapshot(value: unknown): ReleaseValidation {
  if (validateRelease(value)) return { valid: true, snapshot: value };
  return { valid: false, errors: validateRelease.errors ?? [] };
}

export function assertReleaseSnapshot(
  value: unknown,
): asserts value is CourseReleaseSnapshotV1 {
  const result = validateReleaseSnapshot(value);
  if (!result.valid) {
    throw new Error(
      `Invalid release snapshot: ${result.errors
        .slice(0, 3)
        .map((error) => `${error.instancePath || '/'} ${error.message ?? ''}`)
        .join('; ')}`,
    );
  }
}
