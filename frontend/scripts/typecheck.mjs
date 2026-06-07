import { spawnSync } from "node:child_process";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const tsc = resolve(root, "node_modules/typescript/bin/tsc");

const result = spawnSync(process.execPath, [tsc, "-b", "--pretty", "false"], {
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
if (result.status !== 0) {
  console.error(`typecheck exited with status ${result.status ?? "null"}${result.signal ? ` and signal ${result.signal}` : ""}`);
}

process.exit(result.status ?? 1);
