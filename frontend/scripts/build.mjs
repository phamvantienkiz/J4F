import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const vite = resolve(root, "node_modules/vite/bin/vite.js");

const result = spawnSync(process.execPath, [vite, "build"], {
  cwd: root,
  encoding: "utf8",
});

if (result.stdout) {
  process.stdout.write(result.stdout);
}
if (result.stderr) {
  process.stderr.write(result.stderr);
}
if (result.error) {
  console.error(result.error.message);
}

process.exit(result.status ?? 1);
