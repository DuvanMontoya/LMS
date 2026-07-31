import { readFile, mkdir, rename, unlink, writeFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

import Ajv2020 from 'ajv/dist/2020.js';
import { compile } from 'json-schema-to-typescript';

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDirectory, '..', '..', '..');
const outputDirectory = path.join(
  repositoryRoot,
  'apps',
  'web',
  'src',
  'lib',
  'content',
  'generated',
);
const checkOnly = process.argv.slice(2).includes('--check');

if (process.argv.slice(2).some((argument) => argument !== '--check')) {
  throw new Error(
    'Only --check is supported; output paths are fixed by the repository.',
  );
}

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

const outputs = [];
for (const version of [1, 2]) {
  const sourcePath = path.join(
    repositoryRoot,
    'schemas',
    'content',
    `unit-document-v${version}.schema.json`,
  );
  const source = await readFile(sourcePath, 'utf8');
  const schema = JSON.parse(source);
  ajv.compile(schema);
  const generatedType = await compile(schema, `UnitDocumentV${version}`, {
    bannerComment: `${version === 2 ? '/* eslint-disable @typescript-eslint/no-explicit-any */\n' : ''}/* Generated from schemas/content/unit-document-v${version}.schema.json. Do not edit. */`,
    format: false,
    unknownAny: false,
  });
  outputs.push(
    [path.join(outputDirectory, `unit-document-v${version}.ts`), generatedType],
    [
      path.join(outputDirectory, `unit-document-v${version}.schema.json`),
      `${JSON.stringify(schema, null, 2)}\n`,
    ],
  );
}

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
    throw new Error(`Generated content contract drift: ${drift.join(', ')}`);
  }
  console.log(
    'Generated content schemas and TypeScript types are synchronized.',
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
  console.log('Generated content schemas and TypeScript types.');
}
