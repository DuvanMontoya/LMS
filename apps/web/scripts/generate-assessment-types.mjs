import { mkdir, readFile, rename, unlink, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import Ajv2020 from 'ajv/dist/2020.js';
import { compile } from 'json-schema-to-typescript';
import prettier from 'prettier';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDirectory, '..', '..', '..');
const sourceDirectory = path.join(repositoryRoot, 'schemas', 'assessment');
const outputDirectory = path.join(
  repositoryRoot,
  'apps',
  'web',
  'src',
  'lib',
  'assessments',
  'generated',
);
const contentPath = path.join(
  repositoryRoot,
  'schemas',
  'content',
  'unit-document-v1.schema.json',
);
const contracts = [
  ['question-definition-v1', 'QuestionDefinitionV1'],
  ['question-public-v1', 'QuestionPublicV1'],
  ['response-v1', 'AssessmentResponseV1'],
  ['assessment-version-v1', 'AssessmentVersionSnapshotV1'],
];
const checkOnly = process.argv.slice(2).includes('--check');

if (process.argv.slice(2).some((argument) => argument !== '--check')) {
  throw new Error(
    'Only --check is supported; output paths are fixed by the repository.',
  );
}

const contentSchema = JSON.parse(await readFile(contentPath, 'utf8'));
const schemas = new Map();
for (const [name] of contracts) {
  schemas.set(
    name,
    JSON.parse(
      await readFile(path.join(sourceDirectory, `${name}.schema.json`), 'utf8'),
    ),
  );
}

const ajv = new Ajv2020({
  allErrors: true,
  coerceTypes: false,
  loadSchema: undefined,
  removeAdditional: false,
  strict: false,
  useDefaults: false,
});
ajv.addFormat('uuid', true);
ajv.addSchema(contentSchema);
for (const schema of schemas.values()) ajv.addSchema(schema);
for (const schema of schemas.values()) ajv.getSchema(schema.$id);

function inlineReferences(value) {
  if (Array.isArray(value)) return value.map(inlineReferences);
  if (!value || typeof value !== 'object') return value;
  if (value.$ref === contentSchema.$id) {
    const embedded = structuredClone(contentSchema);
    delete embedded.$defs;
    delete embedded.$id;
    delete embedded.$schema;
    return embedded;
  }
  for (const schema of schemas.values()) {
    if (value.$ref === schema.$id) {
      const embedded = structuredClone(schema);
      delete embedded.$defs;
      delete embedded.$id;
      delete embedded.$schema;
      return inlineReferences(embedded);
    }
  }
  return Object.fromEntries(
    Object.entries(value).map(([key, item]) => [key, inlineReferences(item)]),
  );
}

const outputs = [];
for (const [name, typeName] of contracts) {
  const schema = schemas.get(name);
  const typeSchema = inlineReferences(schema);
  typeSchema.$defs = Object.assign(
    {},
    ...[contentSchema, ...schemas.values()].map((item) =>
      structuredClone(item.$defs ?? {}),
    ),
  );
  const generatedType = await prettier.format(
    await compile(typeSchema, typeName, {
      bannerComment: `/* Generated from schemas/assessment/${name}.schema.json. Do not edit. */\n/* eslint-disable @typescript-eslint/no-explicit-any */`,
      format: false,
      unknownAny: false,
    }),
    {
      parser: 'typescript',
      singleQuote: true,
      trailingComma: 'all',
    },
  );
  const generatedSchema = await prettier.format(JSON.stringify(schema), {
    parser: 'json',
  });
  outputs.push(
    [path.join(outputDirectory, `${name}.ts`), generatedType],
    [path.join(outputDirectory, `${name}.schema.json`), generatedSchema],
  );
}
outputs.push([
  path.join(outputDirectory, 'unit-document-v1.schema.json'),
  await prettier.format(JSON.stringify(contentSchema), { parser: 'json' }),
]);

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
  if (drift.length) {
    throw new Error(`Generated assessment contract drift: ${drift.join(', ')}`);
  }
  console.log(
    'Generated assessment schemas and TypeScript types are synchronized.',
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
  console.log('Generated assessment schemas and TypeScript types.');
}
