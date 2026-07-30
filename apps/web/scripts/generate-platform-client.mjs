#!/usr/bin/env node

import { createHash, randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const action = process.argv[2];
if (!['generate', 'check'].includes(action) || process.argv.length !== 3) {
  throw new Error(
    'Uso: node scripts/generate-platform-client.mjs <generate|check>',
  );
}

const require = createRequire(import.meta.url);
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const snapshotPath = join(root, 'openapi', 'platform.openapi.json');
const typesPath = join(root, 'src', 'lib', 'api', 'generated', 'platform.ts');
const generatorPath = require.resolve('openapi-typescript/bin/cli.js');

function requireOrigin(value) {
  if (!value) throw new Error('DJANGO_INTERNAL_ORIGIN es obligatorio.');
  const origin = new URL(value);
  if (
    !['http:', 'https:'].includes(origin.protocol) ||
    origin.username ||
    origin.password ||
    origin.pathname !== '/' ||
    origin.search ||
    origin.hash
  ) {
    throw new Error(
      'DJANGO_INTERNAL_ORIGIN debe ser un origen HTTP(S) seguro.',
    );
  }
  return origin.origin;
}

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, sortValue(value[key])]),
    );
  }
  return value;
}

function validateSchema(schema) {
  if (
    !schema ||
    typeof schema !== 'object' ||
    !String(schema.openapi).startsWith('3.')
  ) {
    throw new Error('El schema de plataforma debe ser OpenAPI 3.');
  }
  const requiredPaths = [
    '/api/v1/access/context/',
    '/api/v1/organizations/',
    '/api/v1/organizations/{slug}/',
    '/api/v1/organizations/{slug}/memberships/',
  ];
  if (
    !schema.paths ||
    typeof schema.paths !== 'object' ||
    requiredPaths.some((path) => !(path in schema.paths))
  ) {
    throw new Error(
      'El schema no contiene las rutas institucionales requeridas.',
    );
  }
}

function runGenerator(inputPath) {
  return new Promise((resolve, reject) => {
    const child = spawn(process.execPath, [generatorPath, inputPath], {
      cwd: root,
      stdio: ['ignore', 'pipe', 'inherit'],
      windowsHide: true,
    });
    let output = '';
    child.stdout.setEncoding('utf8');
    child.stdout.on('data', (chunk) => {
      output += chunk;
    });
    child.once('error', reject);
    child.once('exit', (code) => {
      if (code === 0) resolve(output);
      else
        reject(
          new Error(
            `openapi-typescript terminó con código ${code ?? 'desconocido'}.`,
          ),
        );
    });
  });
}

async function atomicWrite(path, content) {
  await mkdir(dirname(path), { recursive: true });
  const temporaryPath = `${path}.${randomUUID()}.tmp`;
  await writeFile(temporaryPath, content, 'utf8');
  await rename(temporaryPath, path);
}

const localSchemaPath = process.env.PLATFORM_OPENAPI_FILE;
let schema;
if (localSchemaPath) {
  schema = JSON.parse(await readFile(localSchemaPath, 'utf8'));
} else {
  const origin = requireOrigin(process.env.DJANGO_INTERNAL_ORIGIN);
  const response = await fetch(`${origin}/api/v1/schema/`, {
    headers: { Accept: 'application/json' },
    cache: 'no-store',
  });
  if (!response.ok)
    throw new Error(`No se pudo obtener el schema (HTTP ${response.status}).`);
  schema = JSON.parse(await response.text());
}
validateSchema(schema);
const prettier = await import('prettier');
const snapshot = await prettier.format(JSON.stringify(sortValue(schema)), {
  parser: 'json',
  filepath: snapshotPath,
});
const temporaryDirectoryName = `.platform-client-${randomUUID()}`;
const temporaryDirectory = join(root, temporaryDirectoryName);
const temporarySchema = join(temporaryDirectory, 'schema.json');

try {
  await mkdir(temporaryDirectory, { recursive: true });
  await writeFile(temporarySchema, snapshot, 'utf8');
  const types = await runGenerator(`./${temporaryDirectoryName}/schema.json`);
  const generated = await prettier.format(
    `// GENERATED — DO NOT EDIT. Source: openapi/platform.openapi.json\n${types}`,
    { parser: 'typescript', singleQuote: true, trailingComma: 'all' },
  );
  if (action === 'check') {
    const [existingSnapshot, existingTypes] = await Promise.all([
      readFile(snapshotPath, 'utf8'),
      readFile(typesPath, 'utf8'),
    ]);
    if (existingSnapshot !== snapshot || existingTypes !== generated) {
      const fingerprint = createHash('sha256')
        .update(snapshot + generated)
        .digest('hex')
        .slice(0, 12);
      throw new Error(
        `El cliente de plataforma tiene drift (${fingerprint}). Ejecuta GenerateClient.`,
      );
    }
    process.stdout.write(
      'Platform OpenAPI snapshot and client are synchronized.\n',
    );
  } else {
    await atomicWrite(snapshotPath, snapshot);
    await atomicWrite(typesPath, generated);
    process.stdout.write(
      'Platform OpenAPI snapshot and TypeScript client generated.\n',
    );
  }
} finally {
  await rm(temporaryDirectory, { recursive: true, force: true });
}
