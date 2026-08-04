import { copyFile, mkdir, readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import path from "node:path";

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(scriptDirectory, "..");
const workspacePackagePath = path.join(repositoryRoot, "package.json");
const dependencyPath = path.join(repositoryRoot, "node_modules", "mermaid");
const dependencyPackagePath = path.join(dependencyPath, "package.json");
const sourcePath = path.join(dependencyPath, "dist", "mermaid.min.js");
const destinationDirectory = path.join(
  repositoryRoot,
  "documentation",
  "docs",
  "javascripts",
);
const destinationPath = path.join(destinationDirectory, "mermaid.min.js");

const workspacePackage = JSON.parse(await readFile(workspacePackagePath, "utf8"));
const declaredVersion = workspacePackage.devDependencies?.mermaid;

if (!/^\d+\.\d+\.\d+$/.test(declaredVersion ?? "")) {
  throw new Error("Mermaid must be declared with an exact workspace version.");
}

const installedPackage = JSON.parse(await readFile(dependencyPackagePath, "utf8"));
if (installedPackage.version !== declaredVersion) {
  throw new Error(
    `Installed Mermaid ${installedPackage.version} does not match ${declaredVersion}. Run pnpm install --frozen-lockfile.`,
  );
}

await mkdir(destinationDirectory, { recursive: true });
await copyFile(sourcePath, destinationPath);
console.log(`Synchronized Mermaid ${declaredVersion} for the documentation portal.`);
