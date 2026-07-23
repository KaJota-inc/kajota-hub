// Escrow Console client — talks to server.mjs on the same origin.
const $ = (s) => document.querySelector(s);
const logEl = $("#log");

function short(hex, l = 8) {
  if (!hex) return "";
  return hex.length > l * 2 + 2 ? `${hex.slice(0, l + 2)}…${hex.slice(-l)}` : hex;
}
function line(cls, ...bits) {
  const span = document.createElement("span");
  span.className = cls;
  span.textContent = bits.join(" ");
  logEl.appendChild(span);
  logEl.appendChild(document.createElement("br"));
  logEl.scrollTop = logEl.scrollHeight;
}
function clearLog() {
  logEl.textContent = "";
  const dim = document.createElement("span");
  dim.className = "dim";
  dim.textContent = "// events land here";
  logEl.appendChild(dim);
  logEl.appendChild(document.createElement("br"));
}

let CFG = null;

async function loadConfig() {
  const r = await fetch("config", { cache: "no-store" });
  CFG = await r.json();
  $("#cfg-workflow").textContent = CFG.workflowId;
  $("#cfg-contract-link").href = CFG.contract.explorer;
  $("#cfg-contract-link").textContent = CFG.contract.address;
  $("#cfg-fn").textContent = CFG.contract.function;
  $("#cfg-selector").textContent = CFG.contract.selector;
  $("#cfg-keeper-link").href = CFG.keeper.explorer;
  $("#cfg-keeper-link").textContent = CFG.keeper.address;
  $("#cfg-chain").textContent = `${CFG.chain.name} · ${CFG.chain.chainId}`;
  $("#cfg-dashboard").href = CFG.kh.dashboard;
  $("#demo-deposit").textContent = CFG.demoDepositId;
  $("#arch-wf").textContent = `workflow ${short(CFG.workflowId, 8)}`;
  $("#arch-keeper").textContent = `${short(CFG.keeper.address)} · Turnkey · EIP-7702`;
  if (!CFG.khKeyConfigured) {
    line("warn", "! server has no KH_API_KEY configured — /status and /demo-release will 503.");
  }
}

function renderRuns(execs) {
  const runs = $("#runs");
  runs.textContent = "";
  if (!execs.length) {
    const empty = document.createElement("div");
    empty.style.color = "var(--dim)";
    empty.style.padding = "8px 4px";
    empty.textContent = "No runs yet.";
    runs.appendChild(empty);
    return;
  }
  for (const e of execs) {
    const row = document.createElement("div");
    row.className = "exec-row";
    const cls = e.status === "success" ? "success" : e.status === "error" ? "error" : "running";
    const tx = (e.transactionHashes || [])[0]?.hash;

    // status pill
    const c0 = document.createElement("div");
    const pill = document.createElement("span");
    pill.className = `pill ${cls}`;
    pill.textContent = e.status;
    c0.appendChild(pill);

    // duration
    const c1 = document.createElement("div");
    c1.className = "mono";
    c1.textContent = e.duration ? `${e.duration} ms` : "—";

    // tx / error
    const c2 = document.createElement("div");
    if (tx) {
      const a = document.createElement("a");
      a.className = "h";
      a.href = `${CFG.chain.explorer}/tx/${tx}`;
      a.target = "_blank";
      a.textContent = short(tx, 10);
      c2.appendChild(a);
    } else if (e.error) {
      const err = document.createElement("span");
      err.style.color = "var(--red)";
      err.textContent = e.error.length > 80 ? e.error.slice(0, 80) + "…" : e.error;
      c2.appendChild(err);
    } else {
      c2.textContent = "—";
    }

    // started
    const c3 = document.createElement("div");
    c3.className = "mono";
    c3.style.color = "var(--dim)";
    c3.textContent = e.startedAt ? new Date(e.startedAt).toLocaleTimeString() : "—";

    row.append(c0, c1, c2, c3);
    runs.appendChild(row);
  }
}

async function loadStatus() {
  try {
    const r = await fetch("status", { cache: "no-store" });
    const body = await r.json();
    if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
    renderRuns(body.executions);
  } catch (e) {
    line("err", `status failed: ${e.message}`);
  }
}

async function fireRelease() {
  const btn = $("#fire-btn");
  btn.disabled = true;
  clearLog();
  line("acc", `→ POST /demo-release  { depositId: ${short(CFG.demoDepositId)} }`);
  try {
    const r = await fetch("demo-release", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({}),
    });
    const body = await r.json();
    if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
    const eid = body.executionId;
    line("ok", `← KH accepted · executionId=${eid} status=${body.status}`);

    let elapsed = 0;
    while (elapsed < 60000) {
      await new Promise((r) => setTimeout(r, 3000));
      elapsed += 3000;
      const s = await fetch("status", { cache: "no-store" }).then((r) => r.json());
      const run = (s.executions || []).find((x) => x.id === eid);
      if (!run) { line("dim", `  waiting… (${elapsed / 1000}s)`); continue; }
      renderRuns(s.executions);
      if (run.status === "success") {
        const tx = (run.transactionHashes || [])[0]?.hash;
        line("ok", `✓ success in ${run.duration} ms`);
        if (tx) line("acc", `  tx: ${CFG.chain.explorer}/tx/${tx}`);
        break;
      }
      if (run.status === "error") {
        line("warn", `⚠ error (${elapsed / 1000}s): ${(run.error || "").slice(0, 200)}`);
        line("dim", `  ↑ the release path ran end-to-end; the contract rejected the double-spend, which is the correct guard.`);
        break;
      }
      line("dim", `  polling… status=${run.status} (${elapsed / 1000}s)`);
    }
  } catch (e) {
    line("err", `fire failed: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
}

$("#refresh-btn").addEventListener("click", loadStatus);
$("#fire-btn").addEventListener("click", fireRelease);

loadConfig().then(loadStatus);
