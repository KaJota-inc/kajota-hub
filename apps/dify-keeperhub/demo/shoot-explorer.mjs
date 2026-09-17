// Capture the block-explorer frame (e1-explorer) for the demo cut.
//
//   node shoot-explorer.mjs [outdir]
//
// Split out of shoot-dify.mjs because it needs no Dify instance: the
// transaction is permanent on chain, so this frame is reproducible long
// after the local Dify install is gone. That matters — the instance that
// produced the Dify frames was destroyed by macOS's /private/tmp reaper,
// and this was the one capture that survived being re-runnable.
//
// Note it regenerates *an* explorer frame, not a byte-identical copy of
// the committed one: confirmation counts and page chrome move. The
// committed frames-dify/e1-explorer.png stays canonical for the cut.
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";

const OUT = process.argv[2] || "./frames-dify";
const TX = "0x4c316e389ad51ca7e8bf88e1d0f656215164b8ec1a11f8d21c00239ae7eb0335";
const URL = `https://eth-sepolia.blockscout.com/tx/${TX}`;
const PORT = 9339;
mkdirSync(OUT, { recursive: true });

// Same geometry as shoot-dify.mjs: 1600x1000 at dSF 2 -> 3200x2000, which
// is what build-dify.sh's crop=2800:1575:100:425 is calibrated against.
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new",`--remote-debugging-port=${PORT}`,"--window-size=1600,1000",
   "--force-device-scale-factor=2","--hide-scrollbars","--disable-gpu","--no-first-run",
   "--user-data-dir=/tmp/kh-explorer-shoot"],{stdio:"ignore"});
process.on("exit",()=>chrome.kill());

let wsUrl;
for (let i=0;i<60;i++){ try{ wsUrl=(await(await fetch(`http://127.0.0.1:${PORT}/json/version`)).json()).webSocketDebuggerUrl; if(wsUrl)break; }catch{} await sleep(250); }
const ws=new WebSocket(wsUrl); await new Promise(r=>{ws.onopen=r;});
let id=0; const pend=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pend.has(m.id)){const{res,rej}=pend.get(m.id);pend.delete(m.id);m.error?rej(new Error(JSON.stringify(m.error))):res(m.result);}};
const send=(m,p={},s)=>new Promise((res,rej)=>{const n=++id;pend.set(n,{res,rej});ws.send(JSON.stringify({id:n,method:m,params:p,sessionId:s}));});
const {targetInfos}=await send("Target.getTargets");
const tgt=targetInfos.find(x=>x.type==="page");
const {sessionId}=await send("Target.attachToTarget",{targetId:tgt.targetId,flatten:true});
const cmd=(m,p)=>send(m,p,sessionId);
await cmd("Page.enable"); await cmd("Runtime.enable");
await cmd("Emulation.setDeviceMetricsOverride",{width:1600,height:1000,deviceScaleFactor:2,mobile:false});
const ev=async x=>(await cmd("Runtime.evaluate",{expression:x,awaitPromise:true,returnByValue:true})).result?.value;

await cmd("Page.navigate",{url:URL});

// Poll the DOM for the tx hash actually rendering, rather than sleeping a
// guessed interval — blockscout hydrates client-side and a fixed wait
// either races it or wastes time.
let ready=false;
for (let i=0;i<40;i++){
  await sleep(1500);
  if (await ev(`/${TX.slice(2,14)}/i.test(document.body.innerText)`)) { ready=true; console.log(`  tx rendered after ~${((i+1)*1.5).toFixed(1)}s`); break; }
}
if (!ready) { console.error("  tx never rendered — not writing a blank frame"); ws.close(); chrome.kill(); process.exit(1); }

// Assert the page says success before capturing: a frame claiming a
// successful release must not be captured from a page showing a revert.
const ok = await ev(`/success|confirmed/i.test(document.body.innerText)`);
console.log("  page reports success:", ok);
if (!ok) { console.error("  explorer does not show success — refusing to capture"); ws.close(); chrome.kill(); process.exit(1); }

const {data}=await cmd("Page.captureScreenshot",{format:"png"});
writeFileSync(`${OUT}/e1-explorer.png`,Buffer.from(data,"base64"));
console.log("  ✓ e1-explorer ->",`${OUT}/e1-explorer.png`);
ws.close(); chrome.kill(); console.log("\ndone"); process.exit(0);
