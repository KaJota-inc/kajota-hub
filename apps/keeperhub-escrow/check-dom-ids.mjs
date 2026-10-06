/**
 * Guard: every element id the client scripts reach for must exist in the
 * HTML they run against.
 *
 * This exists because a stale `#arch-wf` — left behind when a diagram was
 * removed in a redesign — threw inside loadConfig() before the RPC client
 * was assigned, so every wallet action failed with a null-deref that
 * pointed nowhere near the cause. Markup validation and endpoint probes
 * both passed; nothing caught it but actually clicking the button.
 *
 * Run: node check-dom-ids.mjs
 */
import { readFileSync } from "node:fs";

const html = readFileSync(new URL("./index.html", import.meta.url), "utf8");
const present = new Set([...html.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]));

let bad = 0;
for (const file of ["app.js", "auditor.js", "cfo.js"]) {
  let src;
  try { src = readFileSync(new URL(`./${file}`, import.meta.url), "utf8"); }
  catch { continue; }
  // $("#foo") and document.getElementById("foo")
  const refs = new Set([
    ...[...src.matchAll(/\$\(\s*["'`]#([A-Za-z0-9_-]+)["'`]\s*\)/g)].map((m) => m[1]),
    ...[...src.matchAll(/getElementById\(\s*["'`]([A-Za-z0-9_-]+)["'`]\s*\)/g)].map((m) => m[1]),
  ]);
  for (const id of [...refs].sort()) {
    if (!present.has(id)) { console.error(`  MISSING  #${id}  (referenced in ${file})`); bad++; }
  }
}

if (bad) {
  console.error(`\n${bad} dangling element reference(s). These throw at runtime and can abort init.`);
  process.exit(1);
}
console.log("dom-ids: all client element references resolve against index.html");
