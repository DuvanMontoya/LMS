import { readFile, mkdir, rename, unlink, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import Ajv2020 from 'ajv/dist/2020.js';
import { compile } from 'json-schema-to-typescript';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDirectory, '..', '..', '..');
const sourcePath = path.join(
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
  'content',
  'generated',
);
const typePath = path.join(outputDirectory, 'unit-document-v1.ts');
const schemaPath = path.join(outputDirectory, 'unit-document-v1.schema.json');
const checkOnly = process.argv.slice(2).includes('--check');

if (process.argv.slice(2).some((argument) => argument !== '--check')) {
  throw new Error(
    'Only --check is supported; output paths are fixed by the repository.',
  );
}

const source = await readFile(sourcePath, 'utf8');
const schema = JSON.parse(source);
const ajv = new Ajv2020({
  allErrors: true,
  strict: true,
  coerceTypes: false,
  removeAdditional: false,
  useDefaults: false,
  loadSchema: undefined,
});
ajv.compile(schema);

const generatedType = await compile(schema, 'UnitDocumentV1', {
  bannerComment:
    '/* Generated from schemas/content/unit-document-v1.schema.json. Do not edit. */',
  format: false,
  unknownAny: false,
});
const generatedSchema = `${JSON.stringify(schema, null, 2)}\n`;
const outputs = [
  [typePath, generatedType],
  [schemaPath, generatedSchema],
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
    if (actual !== expected) {
      drift.push(path.relative(repositoryRoot, destination));
    }
  }
  if (drift.length > 0) {
    throw new Error(`Generated content contract drift: ${drift.join(', ')}`);
  }
  console.log(
    'Generated content schema and TypeScript types are synchronized.',
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
  console.log('Generated content schema and TypeScript types.');
}
