import { readFile, mkdir, rename, unlink, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import Ajv2020 from 'ajv/dist/2020.js';
import { compile } from 'json-schema-to-typescript';
import prettier from 'prettier';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDirectory, '..', '..', '..');
const releaseSourcePath = path.join(
  repositoryRoot,
  'schemas',
  'publication',
  'course-release-v1.schema.json',
);
const contentSourcePath = path.join(
  repositoryRoot,
  'schemas',
  'content',
  'unit-document-v1.schema.json',
);
const outputDirectory = path.join(
  repositoryRoot,
  'apps',
  'web',
  'src',
  'lib',
  'publishing',
  'generated',
);
const typePath = path.join(outputDirectory, 'course-release-v1.ts');
const releaseSchemaPath = path.join(
  outputDirectory,
  'course-release-v1.schema.json',
);
const contentSchemaPath = path.join(
  outputDirectory,
  'unit-document-v1.schema.json',
);
const checkOnly = process.argv.slice(2).includes('--check');
const contentReference = 'urn:lms:content:unit-document:1';

if (process.argv.slice(2).some((argument) => argument !== '--check')) {
  throw new Error(
    'Only --check is supported; output paths are fixed by the repository.',
  );
}

const [releaseSource, contentSource] = await Promise.all([
  readFile(releaseSourcePath, 'utf8'),
  readFile(contentSourcePath, 'utf8'),
]);
const releaseSchema = JSON.parse(releaseSource);
const contentSchema = JSON.parse(contentSource);
const ajv = new Ajv2020({
  allErrors: true,
  strict: true,
  coerceTypes: false,
  removeAdditional: false,
  useDefaults: false,
  loadSchema: undefined,
});
ajv.addFormat(
  'uuid',
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
);
ajv.addSchema(contentSchema);
ajv.compile(releaseSchema);

function resolveContentReference(value) {
  if (Array.isArray(value)) return value.map(resolveContentReference);
  if (value && typeof value === 'object') {
    if (value.$ref === contentReference) {
      const contentContract = structuredClone(contentSchema);
      delete contentContract.$defs;
      delete contentContract.$id;
      delete contentContract.$schema;
      return contentContract;
    }
    return Object.fromEntries(
      Object.entries(value).map(([key, item]) => [
        key,
        resolveContentReference(item),
      ]),
    );
  }
  return value;
}

const typeSchema = resolveContentReference(releaseSchema);
typeSchema.$defs = {
  ...typeSchema.$defs,
  ...structuredClone(contentSchema.$defs),
};
const generatedType = await prettier.format(
  `${await compile(typeSchema, 'CourseReleaseSnapshotV1', {
    bannerComment:
      '/* Generated from schemas/publication/course-release-v1.schema.json. Do not edit. */',
    format: false,
    unknownAny: false,
  })}
export type CourseReleaseSnapshotV1 = LMSImmutableCourseReleaseVersion1;
`,
  {
    parser: 'typescript',
    singleQuote: true,
    trailingComma: 'all',
  },
);
const generatedReleaseSchema = await prettier.format(
  JSON.stringify(releaseSchema),
  { parser: 'json' },
);
const generatedContentSchema = await prettier.format(
  JSON.stringify(contentSchema),
  { parser: 'json' },
);
const outputs = [
  [typePath, generatedType],
  [releaseSchemaPath, generatedReleaseSchema],
  [contentSchemaPath, generatedContentSchema],
];

if (checkOnly) {
  const drift = [];
  for (const [destination, expected] of outputs) {
    let actual = '';
    try {
      actual = await readFile(destination, 'utf8');
    } catch {
      drift.push(path.relative(repositoryRoot, destination));
      continue;
    }
    if (actual !== expected)
      drift.push(path.relative(repositoryRoot, destination));
  }
  if (drift.length > 0) {
    throw new Error(
      `Generated publication contract drift: ${drift.join(', ')}`,
    );
  }
  console.log(
    'Generated publication schemas and TypeScript types are synchronized.',
  );
} else {
  await mkdir(outputDirectory, { recursive: true });
  for (const [destination, value] of outputs) {
    const temporary = `${destination}.tmp-${process.pid}`;
    try {
      await writeFile(temporary, value, { encoding: 'utf8', flag: 'wx' });
      await rename(temporary, destination);
    } finally {
      await unlink(temporary).catch(() => undefined);
    }
  }
  console.log('Generated publication schemas and TypeScript types.');
}
