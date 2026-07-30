import { cp, mkdir, readFile, readdir, writeFile } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = join(root, 'node_modules', 'mathjax');
const target = join(root, 'public', 'vendor', 'mathjax');
const assets = [
  'tex-svg.js',
  join('sre', 'speech-worker.js'),
  join('ui', 'safe.js'),
];
const check = process.argv.includes('--check');

for (const asset of assets) {
  const from = join(source, asset);
  const to = join(target, asset);
  if (check) {
    const [expected, actual] = await Promise.all([
      readFile(from),
      readFile(to).catch(() => null),
    ]);
    if (!actual || !expected.equals(actual)) {
      throw new Error(`MathJax asset is missing or stale: ${asset}`);
    }
    continue;
  }
  await mkdir(dirname(to), { recursive: true });
  await cp(from, to);
}

const mathLiveSource = join(root, 'node_modules', 'mathlive', 'fonts');
const mathLiveTarget = join(root, 'public', 'vendor', 'mathlive', 'fonts');
const mathLiveFiles = (
  await readdir(mathLiveSource, { recursive: true, withFileTypes: true })
)
  .filter((entry) => entry.isFile())
  .map((entry) =>
    join(entry.parentPath, entry.name).slice(mathLiveSource.length + 1),
  );

for (const asset of mathLiveFiles) {
  const from = join(mathLiveSource, asset);
  const to = join(mathLiveTarget, asset);
  if (check) {
    const [expected, actual] = await Promise.all([
      readFile(from),
      readFile(to).catch(() => null),
    ]);
    if (!actual || !expected.equals(actual))
      throw new Error(`MathLive font is missing or stale: ${asset}`);
    continue;
  }
  await mkdir(dirname(to), { recursive: true });
  await cp(from, to);
}

if (!check) {
  await writeFile(
    join(target, 'NOTICE.txt'),
    'Generated from mathjax@4.1.3 (Apache-2.0) by scripts/copy-mathjax-assets.mjs. Do not edit.\n',
  );
  await writeFile(
    join(root, 'public', 'vendor', 'mathlive', 'NOTICE.txt'),
    'Generated from mathlive@0.110.0 (MIT) by scripts/copy-mathjax-assets.mjs. Do not edit.\n',
  );
}
