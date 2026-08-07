import Ajv2020, { type ErrorObject } from 'ajv/dist/2020';

import type { CourseReleaseSnapshotV1 } from '../generated/course-release-v1';
import releaseSchemaV1 from '../generated/course-release-v1.schema.json';
import type { CourseReleaseSnapshotV2 } from '../generated/course-release-v2';
import releaseSchemaV2 from '../generated/course-release-v2.schema.json';
import type { CourseReleaseSnapshotV4 } from '../generated/course-release-v4';
import releaseSchemaV4 from '../generated/course-release-v4.schema.json';
import type { CourseReleaseSnapshotV5 } from '../generated/course-release-v5';
import releaseSchemaV5 from '../generated/course-release-v5.schema.json';
import type { CourseReleaseSnapshotV6 } from '../generated/course-release-v6';
import releaseSchemaV6 from '../generated/course-release-v6.schema.json';
import contentSchemaV1 from '../generated/unit-document-v1.schema.json';
import contentSchemaV2 from '../generated/unit-document-v2.schema.json';

type CourseReleaseSnapshot =
  | CourseReleaseSnapshotV1
  | CourseReleaseSnapshotV2
  | CourseReleaseSnapshotV4
  | CourseReleaseSnapshotV5
  | CourseReleaseSnapshotV6;

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
ajv.addSchema(contentSchemaV1);
ajv.addSchema(contentSchemaV2);
const validators = new Map<number, ReturnType<typeof ajv.compile>>([
  [1, ajv.compile<CourseReleaseSnapshotV1>(releaseSchemaV1)],
  [2, ajv.compile<CourseReleaseSnapshotV2>(releaseSchemaV2)],
  [4, ajv.compile<CourseReleaseSnapshotV4>(releaseSchemaV4)],
  [5, ajv.compile<CourseReleaseSnapshotV5>(releaseSchemaV5)],
  [6, ajv.compile<CourseReleaseSnapshotV6>(releaseSchemaV6)],
]);

export type ReleaseValidation =
  | { valid: true; snapshot: CourseReleaseSnapshot }
  | { valid: false; errors: readonly ErrorObject[] };

export function validateReleaseSnapshot(value: unknown): ReleaseValidation {
  const version =
    typeof value === 'object' && value !== null && 'schema_version' in value
      ? value.schema_version
      : null;
  const validate =
    typeof version === 'number' ? validators.get(version) : undefined;
  if (!validate) {
    return {
      valid: false,
      errors: [
        {
          instancePath: '/schema_version',
          keyword: 'enum',
          message: 'must identify a supported release schema',
          params: {},
          schemaPath: '#/properties/schema_version',
        },
      ],
    };
  }
  if (validate(value)) {
    return { valid: true, snapshot: value as CourseReleaseSnapshot };
  }
  return { valid: false, errors: validate.errors ?? [] };
}
