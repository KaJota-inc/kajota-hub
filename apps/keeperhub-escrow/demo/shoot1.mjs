import { spawn } from "node:child_process";
import { writeFileSync } from "node:fs";
import { setTimeout as sleep } from "node:timers/promises";
const [,, URL_, OUTFILE, SCROLL="0"] = process.argv;
const PORT = 9334;
const chrome = spawn("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  ["--headless=new",`--remote-debugging-port=${PORT}`,"--window-size=1600,1000",
   "--force-device-scale-factor=2","--hide-scrollbars","--disable-gpu","--no-first-run",
   "--user-data-dir=/tmp/kh-shoot2"],{stdio:"ignore"});
process.on("exit",()=>chrome.kill());
let wsUrl;
for (let i=0;i<60;i++){ try{ const r=await fetch(`http://127.0.0.1:${PORT}/json/version`);
  wsUrl=(await r.json()).webSocketDebuggerUrl; if(wsUrl)break;}catch{} await sleep(250);}
const ws=new WebSocket(wsUrl); await new Promise(r=>{ws.onopen=r;});
let id=0; const p=new Map();
ws.onmessage=e=>{const m=JSON.parse(e.data); if(m.id&&p.has(m.id)){const{res,rej}=p.get(m.id);p.delete(m.id);m.error?rej(new Error(JSON.stringify(m.error))):res(m.result);}};
const send=(method,params={},sessionId)=>new Promise((res,rej)=>{const n=++id;p.set(n,{res,rej});ws.send(JSON.stringify({id:n,method,params,sessionId}));});
const {targetInfos}=await send("Target.getTargets");
const t=targetInfos.find(x=>x.type==="page");
const {sessionId}=await send("Target.attachToTarget",{targetId:t.targetId,flatten:true});
const cmd=(m,pp)=>send(m,pp,sessionId);
await cmd("Page.enable"); await cmd("Runtime.enable");
await cmd("Emulation.setDeviceMetricsOverride",{width:1600,height:1000,deviceScaleFactor:2,mobile:false});
await cmd("Page.navigate",{url:URL_}); await sleep(8000);
if(SCROLL!=="0"){ await cmd("Runtime.evaluate",{expression:`window.scrollTo({top:${SCROLL},behavior:'instant'})`}); await sleep(1500);}
const {data}=await cmd("Page.captureScreenshot",{format:"png"});
writeFileSync(OUTFILE,Buffer.from(data,"base64"));
console.log("wrote",OUTFILE); ws.close(); chrome.kill(); process.exit(0);
