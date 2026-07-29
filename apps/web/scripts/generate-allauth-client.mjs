#!/usr/bin/env node

import { createHash, randomUUID } from 'node:crypto';
import { spawn } from 'node:child_process';
import { mkdir, readFile, rename, rm, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createRequire } from 'node:module';

const action = process.argv[2];
if (!['generate', 'check'].includes(action) || process.argv.length !== 3) {
  throw new Error(
    'Uso: node scripts/generate-allauth-client.mjs <generate|check>',
  );
}

const require = createRequire(import.meta.url);
const root = dirname(dirname(fileURLToPath(import.meta.url)));
const snapshotPath = join(root, 'openapi', 'allauth.openapi.json');
const typesPath = join(root, 'src', 'lib', 'api', 'generated', 'allauth.ts');
const generatorPath = require.resolve('openapi-typescript/bin/cli.js');

function requireOrigin(value) {
  if (!value) {
    throw new Error(
      'DJANGO_INTERNAL_ORIGIN es obligatorio para generar el cliente.',
    );
  }
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
      'DJANGO_INTERNAL_ORIGIN debe ser un origen HTTP(S) sin ruta ni credenciales.',
    );
  }
  return origin.origin;
}

function sortValue(value) {
  if (Array.isArray(value)) return value.map(sortValue);
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.keys(value)
        .sort()
        .map((key) => [key, sortValue(value[key])]),
    );
  }
  return value;
}

function validateSchema(schema) {
  if (schema === null || typeof schema !== 'object') {
    throw new Error('El OpenAPI de allauth no es un objeto JSON.');
  }
  if (typeof schema.openapi !== 'string' || !schema.openapi.startsWith('3.')) {
    throw new Error('El OpenAPI de allauth debe declarar OpenAPI 3.');
  }
  if (schema.paths === null || typeof schema.paths !== 'object') {
    throw new Error('El OpenAPI de allauth no declara rutas.');
  }
  const paths = Object.keys(schema.paths);
  if (
    paths.length !== 12 ||
    paths.some((path) => !path.startsWith('/_allauth/browser/v1/'))
  ) {
    throw new Error(
      'El OpenAPI no coincide con las 12 rutas browser autorizadas.',
    );
  }
  if (paths.some((path) => /(\/app\/|phone|social|mfa)/.test(path))) {
    throw new Error(
      'El OpenAPI expone una capacidad de autenticación fuera de alcance.',
    );
  }
  const user = schema.components?.schemas?.User;
  const properties = user?.properties;
  if (
    properties === null ||
    typeof properties !== 'object' ||
    ['id', 'email', 'display', 'has_usable_password'].some(
      (key) => !(key in properties),
    )
  ) {
    throw new Error(
      'El OpenAPI no contiene el payload mínimo de usuario esperado.',
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

const origin = requireOrigin(process.env.DJANGO_INTERNAL_ORIGIN);
const response = await fetch(`${origin}/_allauth/openapi.json`, {
  headers: { Accept: 'application/json' },
  cache: 'no-store',
});
if (!response.ok) {
  throw new Error(
    `No se pudo obtener el OpenAPI de allauth (HTTP ${response.status}).`,
  );
}
let schema;
try {
  schema = JSON.parse(await response.text());
} catch {
  throw new Error('El OpenAPI de allauth no devolvió JSON válido.');
}
validateSchema(schema);
const snapshot = `${JSON.stringify(sortValue(schema), null, 2)}\n`;
const temporaryDirectoryName = `.allauth-client-${randomUUID()}`;
const temporaryDirectory = join(root, temporaryDirectoryName);
const temporarySchema = join(temporaryDirectory, 'schema.json');

try {
  await mkdir(temporaryDirectory, { recursive: true });
  await writeFile(temporarySchema, snapshot, 'utf8');
  const types = await runGenerator(`./${temporaryDirectoryName}/schema.json`);
  const prettier = await import('prettier');
  const formattedTypes = await prettier.format(types, { parser: 'typescript' });
  const generatedTypes = `// GENERATED — DO NOT EDIT. Source: openapi/allauth.openapi.json\n${formattedTypes}`;

  if (action === 'check') {
    const [existingSnapshot, existingTypes] = await Promise.all([
      readFile(snapshotPath, 'utf8'),
      readFile(typesPath, 'utf8'),
    ]);
    if (existingSnapshot !== snapshot || existingTypes !== generatedTypes) {
      const expected = createHash('sha256')
        .update(snapshot + generatedTypes)
        .digest('hex')
        .slice(0, 12);
      throw new Error(
        `El cliente OpenAPI está desactualizado (huella esperada ${expected}). Ejecuta GenerateClient.`,
      );
    }
    process.stdout.write(
      'OpenAPI snapshot and generated client are synchronized.\n',
    );
  } else {
    await atomicWrite(snapshotPath, snapshot);
    await atomicWrite(typesPath, generatedTypes);
    process.stdout.write('OpenAPI snapshot and TypeScript client generated.\n');
  }
} finally {
  await rm(temporaryDirectory, { recursive: true, force: true });
}
