import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const apiRoot = join(webRoot, '..', 'api');
const python =
  process.platform === 'win32'
    ? join(apiRoot, '.venv', 'Scripts', 'python.exe')
    : join(apiRoot, '.venv', 'bin', 'python');

if (!existsSync(python))
  throw new Error('Python virtualenv is missing for E2E.');
const port = process.env.E2E_API_PORT ?? '8000';

const child = spawn(
  python,
  ['manage.py', 'runserver', `127.0.0.1:${port}`, '--noreload'],
  {
    cwd: apiRoot,
    env: process.env,
    stdio: 'inherit',
  },
);

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal));
}
child.once('exit', (code) => process.exit(code ?? 1));
