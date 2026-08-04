import {
  cp,
  mkdir,
  readFile,
  readdir,
  realpath,
  writeFile,
} from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const source = join(root, 'node_modules', 'mathjax');
const target = join(root, 'public', 'vendor', 'mathjax');
const files = [
  'tex-svg.js',
  join('sre', 'speech-worker.js'),
  join('ui', 'safe.js'),
];
const check = process.argv.includes('--check');

const sreMathmapsSource = join(source, 'sre', 'mathmaps');
const sreMathmaps = (
  await readdir(sreMathmapsSource, { recursive: true, withFileTypes: true })
)
  .filter((entry) => entry.isFile())
  .map((entry) => join(entry.parentPath, entry.name).slice(source.length + 1));

const newCmSource = join(
  await realpath(source),
  '..',
  '@mathjax',
  'mathjax-newcm-font',
  'svg',
  'dynamic',
);
const newCmDynamicFiles = (
  await readdir(newCmSource, { recursive: true, withFileTypes: true })
)
  .filter((entry) => entry.isFile())
  .map((entry) => ({
    from: join(entry.parentPath, entry.name),
    to: join(
      target,
      'fonts',
      'mathjax-newcm',
      'svg',
      'dynamic',
      join(entry.parentPath, entry.name).slice(newCmSource.length + 1),
    ),
  }));

const assets = [
  ...files.map((asset) => ({
    from: join(source, asset),
    label: asset,
    to: join(target, asset),
  })),
  ...sreMathmaps.map((asset) => ({
    from: join(source, asset),
    label: asset,
    to: join(target, asset),
  })),
  ...newCmDynamicFiles.map((asset) => ({
    ...asset,
    label: asset.to.slice(target.length + 1),
  })),
];

for (const { from, label, to } of assets) {
  if (check) {
    const [expected, actual] = await Promise.all([
      readFile(from),
      readFile(to).catch(() => null),
    ]);
    if (!actual || !expected.equals(actual)) {
      throw new Error(`MathJax asset is missing or stale: ${label}`);
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

const pdfWorkerSource = join(
  root,
  'node_modules',
  'pdfjs-dist',
  'build',
  'pdf.worker.min.mjs',
);
const pdfWorkerTarget = join(
  root,
  'public',
  'vendor',
  'pdfjs',
  'pdf.worker.min.mjs',
);
if (check) {
  const [expected, actual] = await Promise.all([
    readFile(pdfWorkerSource),
    readFile(pdfWorkerTarget).catch(() => null),
  ]);
  if (!actual || !expected.equals(actual)) {
    throw new Error('PDF.js worker is missing or stale.');
  }
} else {
  await mkdir(dirname(pdfWorkerTarget), { recursive: true });
  await cp(pdfWorkerSource, pdfWorkerTarget);
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
  await writeFile(
    join(root, 'public', 'vendor', 'pdfjs', 'NOTICE.txt'),
    'Generated from pdfjs-dist@6.2.108 (Apache-2.0) by scripts/copy-mathjax-assets.mjs. Do not edit.\n',
  );
}
