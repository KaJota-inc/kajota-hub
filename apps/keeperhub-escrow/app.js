// Escrow Console client — talks to server.mjs on the same origin.
// Wallet-connect + deposit + auto-release flow uses viem via ESM CDN.
import {
  createPublicClient,
  createWalletClient,
  custom,
  http,
  parseAbi,
  formatUnits,
  formatEther,
  decodeEventLog,
} from "https://esm.sh/viem@2.21.0";
import { sepolia } from "https://esm.sh/viem@2.21.0/chains";
import { evaluateRelease, signalsFromDeposit } from "./cfo.js";

const $ = (s) => document.querySelector(s);
const logEl = $("#log");

// ---------- helpers ----------
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
function txLink(hash) {
  return `${CFG.chain.explorer}/tx/${hash}`;
}

let CFG = null;
let walletClient = null;
let publicClient = null;
let account = null;

// ---------- initial config load ----------

// Null-safe DOM writers. The page is redesigned often; an element that
// gets renamed or dropped must degrade to a no-op, never take the whole
// init down with it. It did exactly that once: a stale `#arch-wf` left
// over from a removed diagram threw here, so `publicClient` below was
// never assigned and every wallet action failed with a null-deref that
// pointed nowhere near the real cause.
const setText = (sel, value) => {
  const el = $(sel);
  if (el) el.textContent = value;
  else console.warn(`[keeperhub] missing element ${sel} — skipped`);
};
const setLink = (sel, href, text) => {
  const el = $(sel);
  if (!el) return console.warn(`[keeperhub] missing element ${sel} — skipped`);
  el.href = href;
  if (text != null) el.textContent = text;
};

async function loadConfig() {
  // Build the RPC client FIRST. It has no DOM dependency, and nothing
  // that follows should be able to prevent the wallet flow from working.
  publicClient = createPublicClient({
    chain: sepolia,
    transport: http("https://ethereum-sepolia-rpc.publicnode.com"),
  });

  const r = await fetch("config", { cache: "no-store" });
  CFG = await r.json();

  setText("#cfg-workflow", CFG.workflowId);
  setLink("#cfg-contract-link", CFG.contract.explorer, CFG.contract.address);
  setText("#cfg-fn", CFG.contract.function);
  setText("#cfg-selector", CFG.contract.selector);
  setLink("#cfg-keeper-link", CFG.keeper.explorer, CFG.keeper.address);
  setText("#cfg-chain", `${CFG.chain.name} · ${CFG.chain.chainId}`);
  setLink("#cfg-dashboard", CFG.kh.dashboard);
  setText("#demo-deposit", CFG.demoDepositId);
  setText("#fl-listing", short(CFG.fullLoop.listingId, 10));

  if (!CFG.khKeyConfigured) {
    line("warn", "! server has no KH_API_KEY configured — /status and release actions will 503.");
  }
}

// ---------- executions list ----------
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

    const c0 = document.createElement("div");
    const pill = document.createElement("span");
    pill.className = `pill ${cls}`;
    pill.textContent = e.status;
    c0.appendChild(pill);

    const c1 = document.createElement("div");
    c1.className = "mono";
    c1.textContent = e.duration ? `${e.duration} ms` : "—";

    const c2 = document.createElement("div");
    if (tx) {
      const a = document.createElement("a");
      a.className = "h";
      a.href = txLink(tx);
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

// ---------- wallet ----------
const SEPOLIA_CHAIN_ID_HEX = "0xaa36a7";

async function connectWallet() {
  if (!window.ethereum) {
    line("err", "No injected wallet found. Install MetaMask (or another EIP-1193 wallet) and reload.");
    return;
  }
  try {
    // Ensure Sepolia
    try {
      await window.ethereum.request({
        method: "wallet_switchEthereumChain",
        params: [{ chainId: SEPOLIA_CHAIN_ID_HEX }],
      });
    } catch (switchErr) {
      if (switchErr?.code === 4902) {
        await window.ethereum.request({
          method: "wallet_addEthereumChain",
          params: [{
            chainId: SEPOLIA_CHAIN_ID_HEX,
            chainName: "Sepolia",
            nativeCurrency: { name: "Ether", symbol: "ETH", decimals: 18 },
            rpcUrls: ["https://ethereum-sepolia-rpc.publicnode.com"],
            blockExplorerUrls: ["https://sepolia.etherscan.io"],
          }],
        });
      } else if (switchErr?.code === 4001) {
        line("warn", "Chain switch rejected.");
        return;
      } else {
        throw switchErr;
      }
    }
    const accounts = await window.ethereum.request({ method: "eth_requestAccounts" });
    account = accounts[0];
    walletClient = createWalletClient({
      account,
      chain: sepolia,
      transport: custom(window.ethereum),
    });
    line("acc", `connected: ${account}`);
    await refreshBalances();
    $("#connect-btn").textContent = "Reconnect";
    $("#wallet-info").style.display = "block";
  } catch (e) {
    line("err", `connect failed: ${e.shortMessage || e.message}`);
  }
}

const USDC_ABI = parseAbi([
  "function balanceOf(address) view returns (uint256)",
  "function allowance(address owner, address spender) view returns (uint256)",
  "function approve(address spender, uint256 value) returns (bool)",
]);
const ESCROW_ABI = parseAbi([
  "function deposit(bytes32 listingId, uint256 grossAmount) returns (bytes32 depositId)",
  "event Deposited(bytes32 indexed depositId, bytes32 indexed listingId, address indexed buyer, uint256 grossAmount)",
]);

async function refreshBalances() {
  const [ethBal, usdcBal] = await Promise.all([
    publicClient.getBalance({ address: account }),
    publicClient.readContract({
      address: CFG.fullLoop.usdc,
      abi: USDC_ABI,
      functionName: "balanceOf",
      args: [account],
    }),
  ]);
  const link = $("#wallet-addr-link");
  link.href = `${CFG.chain.explorer}/address/${account}`;
  link.textContent = account;
  $("#wallet-eth").textContent = `${Number(formatEther(ethBal)).toFixed(4)} ETH`;
  $("#wallet-usdc").textContent = `${Number(formatUnits(usdcBal, 6)).toFixed(2)} USDC`;

  const need = BigInt(CFG.fullLoop.depositAmountRaw);
  const lowUsdc = usdcBal < need;
  const lowEth = ethBal < 500_000_000_000_000n; // 0.0005 ETH ≈ enough for approve+deposit
  $("#fund-usdc-btn").style.display = lowUsdc ? "" : "none";
  $("#fund-usdc-btn").onclick = () => window.open(CFG.fullLoop.faucets.usdc, "_blank");
  $("#fund-eth-btn").style.display = lowEth ? "" : "none";
  $("#fund-eth-btn").onclick = () => window.open(CFG.fullLoop.faucets.eth, "_blank");
  $("#deposit-btn").disabled = lowUsdc || lowEth;
  if (lowUsdc) line("warn", `need ${CFG.fullLoop.depositAmountHuman} USDC — click "Get Sepolia USDC" for the faucet.`);
  if (lowEth) line("warn", `need Sepolia ETH for gas — click "Get Sepolia ETH".`);
}

// ---------- deposit + auto-release ----------
async function depositAndAutoRelease() {
  const btn = $("#deposit-btn");
  btn.disabled = true;
  clearLog();
  try {
    const need = BigInt(CFG.fullLoop.depositAmountRaw);

    // 1. Approve if allowance too low
    const allow = await publicClient.readContract({
      address: CFG.fullLoop.usdc,
      abi: USDC_ABI,
      functionName: "allowance",
      args: [account, CFG.contract.address],
    });
    if (allow < need) {
      line("acc", `→ approve(USDC → escrow, ${CFG.fullLoop.depositAmountHuman})  awaiting signature…`);
      const hash = await walletClient.writeContract({
        address: CFG.fullLoop.usdc,
        abi: USDC_ABI,
        functionName: "approve",
        args: [CFG.contract.address, need],
      });
      line("dim", `  approve tx: ${short(hash, 10)}  (waiting for receipt…)`);
      await publicClient.waitForTransactionReceipt({ hash });
      line("ok", `  approve confirmed`);
    } else {
      line("dim", `allowance already sufficient — skipping approve`);
    }

    // 2. Deposit
    line("acc", `→ deposit(listingId, ${CFG.fullLoop.depositAmountHuman})  awaiting signature…`);
    const depHash = await walletClient.writeContract({
      address: CFG.contract.address,
      abi: ESCROW_ABI,
      functionName: "deposit",
      args: [CFG.fullLoop.listingId, need],
    });
    line("dim", `  deposit tx: ${short(depHash, 10)}  ${txLink(depHash)}`);
    const rcpt = await publicClient.waitForTransactionReceipt({ hash: depHash });

    // 3. Extract depositId from Deposited event
    let depositId = null;
    for (const log of rcpt.logs) {
      if (log.address.toLowerCase() !== CFG.contract.address.toLowerCase()) continue;
      try {
        const decoded = decodeEventLog({ abi: ESCROW_ABI, data: log.data, topics: log.topics });
        if (decoded.eventName === "Deposited") {
          depositId = decoded.args.depositId;
          break;
        }
      } catch {}
    }
    if (!depositId) throw new Error("Deposited event not found in receipt");
    line("ok", `  deposit landed. depositId = ${short(depositId, 10)}`);

    // Hand the deposit to the autonomous watcher. From here Coach would
    // reach the same verdict on its own schedule with no browser open —
    // the click below just skips the wait.
    try {
      await fetch("autonomous/track", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ depositId, source: "console-deposit" }),
      });
      line("dim", `  registered with the autonomous watcher (see "Coach on its own")`);
    } catch { /* watcher is optional — never block the demo on it */ }

    // 4. Coach CFO decision. Deliberately evaluated with the buyer's
    //    confirmation ABSENT, because at this instant it genuinely is:
    //    money has moved into escrow and nothing else has happened yet.
    //    The honest verdict here is HOLD, and showing that is the point
    //    — a release layer that always says yes isn't a decision layer.
    line("acc", `→ Coach CFO evaluating release (deterministic decides, template explains)…`);
    PENDING = { depositId, grossAmountRaw: need, depositedAt: Math.floor(Date.now() / 1000) };
    const verdict = evaluateRelease(signalsFromDeposit({
      depositId,
      buyer: account,
      grossAmountRaw: need,
      listingId: CFG.fullLoop.listingId,
      depositedAt: PENDING.depositedAt,
      buyerConfirmed: false,
    }));
    renderVerdict(verdict);

    if (verdict.decision !== "release") {
      line("warn", `⚠ Coach is holding the funds. It will not ask KeeperHub to sign yet.`);
      line("dim", `  Two ways this resolves: you confirm receipt below, or the ${BUYER_WINDOW_DAYS}-day`);
      line("dim", `  acceptance window elapses and the autonomous watcher releases it unattended.`);
      $("#confirm-row").style.display = "flex";
      return;
    }

    await fireReleaseFor(depositId);
    await refreshBalances();
  } catch (e) {
    line("err", `flow failed: ${e.shortMessage || e.message}`);
  } finally {
    btn.disabled = false;
  }
}

// Acceptance window mirrored from cfo.js so the copy above stays honest
// if the rule ever changes.
const BUYER_WINDOW_DAYS = 7;

// The deposit awaiting the buyer's confirmation, if any.
let PENDING = null;

function renderVerdict(verdict) {
  for (const r of verdict.rules) {
    const glyph = r.passed ? "✓" : "✗";
    const cls = r.passed ? "ok" : "err";
    line(cls, `  ${glyph} [${r.weight}] ${r.name} — ${r.detail}`);
  }
  const pillCls = verdict.decision === "release" ? "ok"
    : verdict.decision === "hold" ? "warn" : "err";
  line(pillCls, `  Verdict: ${verdict.decision.toUpperCase()}`);
  line("dim", `  ${verdict.why}`);
}

/** Buyer confirms receipt → Coach re-evaluates → release if it now passes. */
async function confirmReceiptAndRelease() {
  if (!PENDING) return;
  const btn = $("#confirm-btn");
  btn.disabled = true;
  try {
    // This records the buyer's acceptance in the marketplace's own
    // records — the off-chain signal the rules engine reads. It is not
    // the escrow's on-chain confirmReceipt(), which would settle the
    // deposit directly and cut KeeperHub out of the loop entirely.
    line("acc", `→ buyer confirms receipt · re-running the same rules with that one signal flipped`);
    const verdict = evaluateRelease(signalsFromDeposit({
      depositId: PENDING.depositId,
      buyer: account,
      grossAmountRaw: PENDING.grossAmountRaw,
      listingId: CFG.fullLoop.listingId,
      depositedAt: PENDING.depositedAt,
      buyerConfirmed: true,
    }));
    renderVerdict(verdict);

    // Record the confirmation with the autonomous watcher. If the watcher
    // is armed it takes ownership of the release from here — and we must
    // NOT fire our own, or both submit against the same deposit and the
    // loser reverts on the escrow's idempotency guard.
    let handedOff = false;
    try {
      const r = await fetch("autonomous/confirm", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ depositId: PENDING.depositId }),
      });
      const body = await r.json();
      handedOff = Boolean(body.handedOff);
      line("dim", `  buyer confirmation recorded with the autonomous watcher`);
    } catch { /* optional — never block the demo on it */ }

    if (verdict.decision !== "release") {
      line("warn", `⚠ still not releasable — see the failing rule above.`);
      return;
    }
    $("#confirm-row").style.display = "none";

    if (handedOff) {
      // The strongest version of the demo: from here nobody clicks
      // anything. The loop re-evaluates on its own timer and fires.
      line("acc", `→ handing off to the autonomous watcher — it will release on its next tick`);
      await awaitWatcherRelease(PENDING.depositId);
    } else {
      await fireReleaseFor(PENDING.depositId);
    }
    PENDING = null;
    await refreshBalances();
  } catch (e) {
    line("err", `confirm failed: ${e.shortMessage || e.message}`);
  } finally {
    btn.disabled = false;
  }
}

/**
 * Watch the autonomous loop take a deposit to a terminal state.
 *
 * Deliberately passive: this issues no release of its own, it only reads
 * /autonomous. Everything it prints was decided and executed by the
 * server-side loop on its own timer, which is the point — the browser is
 * a spectator here, not a participant.
 */
async function awaitWatcherRelease(depositId, timeoutMs = 90000) {
  const id = depositId.toLowerCase();
  const t0 = Date.now();
  let lastNote = "";
  while (Date.now() - t0 < timeoutMs) {
    await new Promise((r) => setTimeout(r, 3000));
    let st;
    try { st = await fetch("autonomous", { cache: "no-store" }).then((r) => r.json()); }
    catch { continue; }

    const rec = (st.tracked || []).find((t) => t.depositId === id);
    const secs = Math.round((Date.now() - t0) / 1000);

    // Surface the loop's own log lines for this deposit as they appear.
    const entry = (st.log || []).find((l) => (l.depositId || "").toLowerCase() === id);
    if (entry && entry.message !== lastNote) {
      lastNote = entry.message;
      line(entry.level === "ok" ? "ok" : entry.level === "err" ? "err" : "dim", `  ${entry.message}`);
    }

    if (rec?.status === "released-by-coach" && rec.executionId) {
      line("ok", `✓ the watcher fired it — executionId=${rec.executionId} (${secs}s, no clicks)`);
      // Resolve the on-chain tx from KH's execution list.
      for (let i = 0; i < 20; i++) {
        await new Promise((r) => setTimeout(r, 3000));
        const s = await fetch("status", { cache: "no-store" }).then((r) => r.json()).catch(() => null);
        if (!s) continue;
        const run = (s.executions || []).find((x) => x.id === rec.executionId);
        if (!run) continue;
        renderRuns(s.executions);
        if (run.status === "success") {
          const tx = (run.transactionHashes || [])[0]?.hash;
          line("ok", `✓ release confirmed on Sepolia in ${run.duration} ms`);
          if (tx) line("acc", `  release tx: ${txLink(tx)}`);
          line("ok", `\n🎉 Coach released this on its own. Nobody clicked release.`);
          return;
        }
        if (run.status === "error") {
          line("err", `⚠ watcher release errored: ${(run.error || "").slice(0, 180)}`);
          return;
        }
      }
      line("warn", `  release fired but the tx hasn't confirmed yet — see "Recent runs".`);
      return;
    }
    if (rec && rec.status !== "watching") {
      line("warn", `  watcher marked this deposit '${rec.status}' — not releasing.`);
      return;
    }
    if (secs % 15 === 0) line("dim", `  waiting on the watcher… (${secs}s)`);
  }
  line("warn", `  gave up watching after ${Math.round(timeoutMs / 1000)}s — check "Coach on its own" below.`);
}

/** Fire the KH workflow for a depositId and poll it to a terminal state. */
async function fireReleaseFor(depositId) {
  line("acc", `→ POST /demo-release  { depositId }  (KH signs via EIP-7702 Turnkey)`);
  const r = await fetch("demo-release", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ depositId }),
  });
  const body = await r.json();
  if (!r.ok) throw new Error(body.error || `HTTP ${r.status}`);
  const eid = body.executionId;
  line("ok", `← KH accepted · executionId=${eid} status=${body.status}`);

  for (let elapsed = 0; elapsed < 60000; elapsed += 3000) {
    await new Promise((res) => setTimeout(res, 3000));
    const s = await fetch("status", { cache: "no-store" }).then((x) => x.json());
    const run = (s.executions || []).find((x) => x.id === eid);
    if (!run) { line("dim", `  waiting… (${elapsed / 1000 + 3}s)`); continue; }
    renderRuns(s.executions);
    if (run.status === "success") {
      const tx = (run.transactionHashes || [])[0]?.hash;
      line("ok", `✓ release success in ${run.duration} ms`);
      if (tx) line("acc", `  release tx: ${txLink(tx)}`);
      line("ok", `\n🎉 end-to-end complete. Coach decided, KeeperHub signed, USDC split 85/15.`);
      return;
    }
    if (run.status === "error") {
      line("err", `⚠ release error: ${(run.error || "").slice(0, 200)}`);
      return;
    }
    line("dim", `  polling KH… status=${run.status} (${elapsed / 1000 + 3}s)`);
  }
  line("warn", `  stopped polling after 60s — check "Recent runs" for the outcome.`);
}

// ---------- fire (idempotency demo) ----------
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

    for (let elapsed = 0; elapsed < 60000; elapsed += 3000) {
      await new Promise((r) => setTimeout(r, 3000));
      const s = await fetch("status", { cache: "no-store" }).then((r) => r.json());
      const run = (s.executions || []).find((x) => x.id === eid);
      if (!run) { line("dim", `  waiting… (${elapsed / 1000 + 3}s)`); continue; }
      renderRuns(s.executions);
      if (run.status === "success") {
        const tx = (run.transactionHashes || [])[0]?.hash;
        line("ok", `✓ success in ${run.duration} ms`);
        if (tx) line("acc", `  tx: ${txLink(tx)}`);
        break;
      }
      if (run.status === "error") {
        line("warn", `⚠ error (${elapsed / 1000 + 3}s): ${(run.error || "").slice(0, 200)}`);
        line("dim", `  ↑ the release path ran end-to-end; the contract rejected the double-spend, which is the correct guard.`);
        break;
      }
      line("dim", `  polling… status=${run.status} (${elapsed / 1000 + 3}s)`);
    }
  } catch (e) {
    line("err", `fire failed: ${e.message}`);
  } finally {
    btn.disabled = false;
  }
}

// ---------- wire buttons ----------
// Same reasoning as the DOM writers above: one renamed id shouldn't
// leave every other control dead. Wire each independently.
const on = (sel, handler) => {
  const el = $(sel);
  if (el) el.addEventListener("click", handler);
  else console.warn(`[keeperhub] missing control ${sel} — not wired`);
};

on("#connect-btn", connectWallet);
on("#deposit-btn", depositAndAutoRelease);
on("#confirm-btn", confirmReceiptAndRelease);
on("#refresh-btn", loadStatus);
on("#fire-btn", fireRelease);

// Independent, not chained. loadStatus reads the KH execution list and
// has nothing to do with config; chaining meant a config failure also
// left "Recent runs" spinning forever, which hid the real error.
loadConfig().catch((e) => line("err", `config load failed: ${e.message}`));
loadStatus();
