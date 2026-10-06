// Capture the demo frames at video resolution.
//
// The Chrome MCP returns 1372x873 JPEG, which is fine for me to look at and
// too soft to put in front of judges. This drives the same page over CDP at
// 1600x1000 @2x and writes PNGs, so the frames are actually 3200x2000.
//
// Node 25 ships WebSocket, so this needs no dependencies.

import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";

const OUT = process.argv[2] || "./frames";
const URL_ = "https://kajota-hub.onrender.com/keeperhub/";
const PORT = 9333;
mkdirSync(OUT, { recursive: true });

const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", [
  "--headless=new",
  `--remote-debugging-port=${PORT}`,
  "--window-size=1600,1000",
  "--force-device-scale-factor=2",
  "--hide-scrollbars",
  "--disable-gpu",
  "--no-first-run",
  "--user-data-dir=/tmp/kh-shoot-profile",
], { stdio: "ignore" });

process.on("exit", () => chrome.kill());

// wait for the debugger to come up
let wsUrl;
for (let i = 0; i < 60; i++) {
  try {
    const r = await fetch(`http://127.0.0.1:${PORT}/json/version`);
    wsUrl = (await r.json()).webSocketDebuggerUrl;
    if (wsUrl) break;
  } catch {}
  await sleep(250);
}
if (!wsUrl) { console.error("chrome never came up"); process.exit(1); }

const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = rej; });

let id = 0;
const pending = new Map();
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) {
    const { res, rej } = pending.get(m.id); pending.delete(m.id);
    m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result);
  }
};
const send = (method, params = {}, sessionId) =>
  new Promise((res, rej) => {
    const n = ++id;
    pending.set(n, { res, rej });
    ws.send(JSON.stringify({ id: n, method, params, sessionId }));
  });

// attach to a page target
const { targetInfos } = await send("Target.getTargets");
let target = targetInfos.find(t => t.type === "page");
if (!target) {
  const t = await send("Target.createTarget", { url: "about:blank" });
  target = { targetId: t.targetId };
}
const { sessionId } = await send("Target.attachToTarget", { targetId: target.targetId, flatten: true });
const cmd = (m, p) => send(m, p, sessionId);

await cmd("Page.enable");
await cmd("Runtime.enable");
await cmd("Emulation.setDeviceMetricsOverride", {
  width: 1600, height: 1000, deviceScaleFactor: 2, mobile: false,
});

const evalJs = async (expression) => {
  const r = await cmd("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  return r.result?.value;
};

const shot = async (name) => {
  const { data } = await cmd("Page.captureScreenshot", { format: "png", captureBeyondViewport: false });
  writeFileSync(`${OUT}/${name}.png`, Buffer.from(data, "base64"));
  console.log("  ✓", name);
};

console.log("loading…");
await cmd("Page.navigate", { url: URL_ });
await sleep(6000);
// let the live panels finish their first fetch
await evalJs("document.readyState");
await sleep(4000);

const scrollTo = (sel, off = -60) =>
  evalJs(`(()=>{const e=document.querySelector(${JSON.stringify(sel)});
    if(!e) return 'MISSING ' + ${JSON.stringify(sel)};
    window.scrollTo({top:e.getBoundingClientRect().top+window.scrollY+(${off}),behavior:'instant'});
    return window.scrollY;})()`);

const clickText = (re) =>
  evalJs(`(()=>{const b=[...document.querySelectorAll('button,[role=tab],.tab,a')]
    .find(x=>/${re}/i.test(x.textContent));
    if(!b) return 'NOTFOUND';
    b.click(); return 'clicked: '+b.textContent.trim().slice(0,40);})()`);

console.log("shooting…");

// §2 / §7 — hero
await evalJs("window.scrollTo({top:0,behavior:'instant'})"); await sleep(900);
await shot("s2-hero");

// §3 — the end-to-end panel + real runs table (tx hashes, guarded reverts)
console.log(" ", await scrollTo("#runs-wrap", -190)); await sleep(1200);
await shot("s3-runs");

// §6 — autonomous watcher
console.log(" ", await scrollTo("#auto-card", -60)); await sleep(1200);
await shot("s6-autonomous");

// §1 / §3 — the CFO verdict flip. HOLD is the hook frame.
console.log(" ", await scrollTo("#cfo-report", -150)); await sleep(800);
console.log(" ", await clickText("not shipped")); await sleep(2500);
await shot("s1-hold");
console.log(" ", await clickText("active dispute")); await sleep(2500);
await shot("s4-reject");
console.log(" ", await clickText("happy path")); await sleep(2500);
await shot("s3-release");

// §5 — the auditor report on the deliberately broken workflow
console.log(" ", await clickText("broken workflow")); await sleep(1200);
console.log(" ", await clickText("^\\s*audit workflow")); await sleep(3000);
console.log(" ", await scrollTo("#aud-report", -120)); await sleep(1200);
await shot("s5-audit");

// §5 — the trap catalogue (web3Connection vs integrationId)
console.log(" ", await evalJs(`(()=>{const h=[...document.querySelectorAll('h2')]
  .find(x=>/auditor is checking/i.test(x.textContent));
  window.scrollTo({top:h.getBoundingClientRect().top+window.scrollY-80,behavior:'instant'});
  return window.scrollY;})()`)); await sleep(1200);
await shot("s5-traps");

ws.close();
chrome.kill();
console.log("\ndone →", OUT);
process.exit(0);
