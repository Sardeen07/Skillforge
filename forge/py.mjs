#!/usr/bin/env node
// Runs a Python script with whichever interpreter this machine actually has.
//
// `python3` is not portable: on Windows it is usually a Microsoft Store alias that
// prints "Python was not found" and still exits 0, so a failure looks like success.
// `python` is not portable either: on many Linux distros it does not exist. So probe.
import { spawnSync } from "node:child_process";

const candidates = process.platform === "win32" ? ["python", "py", "python3"]
                                                : ["python3", "python"];

function works(exe) {
  const r = spawnSync(exe, ["-c", "import sys; print('supported' if sys.version_info >= (3, 10) else 'unsupported')"],
                      { encoding: "utf8" });
  return r.status === 0 && r.stdout.trim() === "supported";
}

const python = candidates.find(works);
if (!python) {
  console.error(`no Python 3.10+ found (tried: ${candidates.join(", ")})`);
  process.exit(1);
}

const r = spawnSync(python, process.argv.slice(2), { stdio: "inherit" });
process.exit(r.status === null ? 1 : r.status);
