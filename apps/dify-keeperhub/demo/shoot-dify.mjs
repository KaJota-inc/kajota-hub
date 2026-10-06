// Capture the Dify integration. Uses Input.dispatchMouseEvent rather than
// element.click(): React's handlers do not fire for a synthetic .click() on
// this control, which is why an earlier pass produced four byte-identical
// frames while reporting a successful click.
import { spawn } from "node:child_process";
import { writeFileSync, mkdirSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";

const OUT = process.argv[2] || "./frames-dify";
const APP = "bae3d110-2308-40c0-b3d0-9788dcd2024f";
const PORT = 9338;
mkdirSync(OUT, { recursive: true });

const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new",`--remote-debugging-port=${PORT}`,"--window-size=1600,1000",
   "--force-device-scale-factor=2","--hide-scrollbars","--disable-gpu","--no-first-run",
   "--user-data-dir=/tmp/kh-dify-shoot"],{stdio:"ignore"});
process.on("exit",()=>chrome.kill());
let wsUrl; for(let i=0;i<60;i++){try{wsUrl=(await(await fetch(`http://127.0.0.1:${PORT}/json/version`)).json()).webSocketDebuggerUrl;if(wsUrl)break;}catch{}await sleep(250);}
const ws=new WebSocket(wsUrl); await new Promise(r=>{ws.onopen=r;});
let id=0;const pend=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data);if(m.id&&pend.has(m.id)){const{res,rej}=pend.get(m.id);pend.delete(m.id);m.error?rej(new Error(JSON.stringify(m.error))):res(m.result);}};
const send=(m,p={},s)=>new Promise((res,rej)=>{const n=++id;pend.set(n,{res,rej});ws.send(JSON.stringify({id:n,method:m,params:p,sessionId:s}));});
const {targetInfos}=await send("Target.getTargets");
const tgt=targetInfos.find(x=>x.type==="page");
const {sessionId}=await send("Target.attachToTarget",{targetId:tgt.targetId,flatten:true});
const cmd=(m,p)=>send(m,p,sessionId);
await cmd("Page.enable");await cmd("Runtime.enable");await cmd("Input.enable").catch(()=>{});
await cmd("Emulation.setDeviceMetricsOverride",{width:1600,height:1000,deviceScaleFactor:2,mobile:false});
const ev=async x=>(await cmd("Runtime.evaluate",{expression:x,awaitPromise:true,returnByValue:true})).result?.value;
const shot=async n=>{const{data}=await cmd("Page.captureScreenshot",{format:"png"});writeFileSync(`${OUT}/${n}.png`,Buffer.from(data,"base64"));console.log("  ✓",n);};
const click=async(x,y)=>{await cmd("Input.dispatchMouseEvent",{type:"mouseMoved",x,y});
  await cmd("Input.dispatchMouseEvent",{type:"mousePressed",x,y,button:"left",clickCount:1});
  await cmd("Input.dispatchMouseEvent",{type:"mouseReleased",x,y,button:"left",clickCount:1});};
const centreOf = async (re) => JSON.parse(await ev(`(()=>{
  const all=[...document.querySelectorAll('button,div,span,a')].filter(x=>${re}.test(x.textContent||'')&&x.offsetParent);
  if(!all.length) return 'null';
  all.sort((a,b)=>(a.textContent||'').length-(b.textContent||'').length);
  const r=all[0].getBoundingClientRect();
  return JSON.stringify({x:Math.round(r.left+r.width/2),y:Math.round(r.top+r.height/2)});})()`));

await cmd("Page.navigate",{url:`http://localhost/app/${APP}/workflow`}); await sleep(13000);
await ev(`(()=>{const t=[...document.querySelectorAll('div')].find(d=>/Syncing data/i.test(d.textContent)&&d.children.length===0);if(t&&t.parentElement)t.parentElement.style.display='none';return 1;})()`);
await sleep(2000);
await shot("d1-canvas");

const tr = await centreOf("/Test\\s*Run/i");
if (!tr) { console.log("  Test Run not found"); } else {
  console.log("  clicking Test Run at", tr.x, tr.y);
  await click(tr.x, tr.y);
  // poll for completion instead of guessing a wait
  let state = "";
  for (let i = 0; i < 40; i++) {
    await sleep(2000);
    state = await ev(`JSON.stringify({succeeded:/succeeded/i.test(document.body.innerText),failed:/failed|error/i.test(document.body.innerText),len:document.body.innerText.length})`);
    if (/"succeeded":true/.test(state)) { console.log("  run succeeded after ~"+((i+1)*2)+"s"); break; }
  }
  console.log("  final state:", state);
  await shot("d2-run");
  // open the result/detail tab if one is offered
  // RESULT is already the default tab and carries the output; capture it,
  // then TRACING, which shows the tool invocation node by node.
  await shot("d3-result");
  const tr2 = await centreOf("/^TRACING$/");
  if (tr2) { await click(tr2.x, tr2.y); await sleep(4000); await shot("d4-tracing"); }
  else console.log("  no TRACING tab found");
  const det2 = await centreOf("/^DETAIL$/");
  if (det2) { await click(det2.x, det2.y); await sleep(4000); await shot("d5-detail"); }
}
ws.close();chrome.kill();console.log("\ndone");process.exit(0);
