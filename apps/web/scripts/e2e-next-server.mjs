import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const webRoot = dirname(dirname(fileURLToPath(import.meta.url)));
const nextCli = join(webRoot, 'node_modules', 'next', 'dist', 'bin', 'next');
const port = process.env.E2E_WEB_PORT ?? '3000';
const child = spawn(
  process.execPath,
  [nextCli, 'dev', '--hostname', '127.0.0.1', '--port', port],
  {
    cwd: webRoot,
    env: process.env,
    stdio: 'inherit',
  },
);

for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal));
}
child.once('exit', (code) => process.exit(code ?? 1));
