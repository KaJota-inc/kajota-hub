/**
 * Kajota × KeeperHub — Escrow Console.
 *
 * Live, read-mostly UI for the hackathon judges: shows the latest KeeperHub
 * workflow execution for CosellEscrow.release() on Sepolia, with links to
 * Etherscan and the KeeperHub dashboard.
 *
 * Also exposes an optional trigger endpoint that re-invokes the KH workflow
 * with the current known-good depositId — the release() will revert on-chain
 * (deposit already settled) but the tx composition + KH keeper signing + RPC
 * submission all run, which is precisely what a judge wants to click.
 *
 * Endpoints:
 *   GET  /            → index.html
 *   GET  /healthz     → 200 ok
 *   GET  /config      → { workflowId, contract, keeper, network } (no secrets)
 *   GET  /status      → { executions: [...] }  live from KH's REST API
 *   POST /demo-release → forwards to KH /api/workflows/{id}/execute
 *                        Body:  { depositId?: hex }  (default = last-known-good)
 *                        Response: { executionId, statusUrl }
 *
 * The KEEPERHUB_API_KEY is server-held and never returned to the browser.
 * The keeper only has release rights on ONE contract on Sepolia — even a
 * malicious re-trigger is bounded to that surface.
 */
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createWatcher } from "./watcher.mjs";

const __dir = dirname(fileURLToPath(import.meta.url));
const PORT = Number(process.env.KH_ESCROW_PORT || process.env.PORT || 8108);

// ---- KeeperHub config ----------------------------------------------
const KH_BASE = (process.env.KH_API_BASE || "https://app.keeperhub.com").replace(/\/$/, "");
const KH_KEY = process.env.KH_API_KEY || ""; // kh_...
const KH_WORKFLOW_ID = process.env.KH_WORKFLOW_ID || "1pyjp0c15z2h558jld8pn";

// ---- On-chain artefacts (public, safe to expose) --------------------
const KH_CONTRACT = process.env.KH_CONTRACT_ADDRESS || "0x599869cef2e4c52e2c9074caaf8f9fb0cb191776";
const KH_KEEPER = process.env.KH_KEEPER_ADDRESS || "0x4c629AD055B3Ad07beF13b3b2f47E74aFE493bc2";
const KH_CHAIN_ID = Number(process.env.KH_CHAIN_ID || 11155111);
const KH_DEMO_DEPOSIT_ID = process.env.KH_DEMO_DEPOSIT_ID
  || "0xe713d5a3eb6c0c3c247e3c86ad23696e006c6097de47d5fad9a303838f0f2d13";
// Full-loop (Connect Wallet → Deposit → Auto-release) needs:
const KH_REGISTRY = process.env.KH_REGISTRY_ADDRESS || "0xfce6bd68d8d6f858d447f537d206c1e354b44315";
const KH_USDC = process.env.KH_USDC_ADDRESS || "0x1c7D4B196Cb0C7B01d743Fbc6116a902379C7238";
const KH_DEMO_LISTING_ID = process.env.KH_DEMO_LISTING_ID
  || "0x22d917c51456ff35e7e678534cc6059d86659e0bfa926bf137e036cf6f9a7426";
const KH_DEMO_DEPOSIT_USDC = process.env.KH_DEMO_DEPOSIT_USDC || "100000"; // 0.10 USDC (6 dp)

const INDEX_HTML = readFileSync(join(__dir, "index.html"), "utf8");
const APP_JS = readFileSync(join(__dir, "app.js"), "utf8");
const AUDITOR_JS = readFileSync(join(__dir, "auditor.js"), "utf8");
const CFO_JS = readFileSync(join(__dir, "cfo.js"), "utf8");

// ---- Helpers --------------------------------------------------------
function json(res, code, body) {
  res.writeHead(code, {
    "content-type": "application/json",
    "cache-control": "no-store",
  });
  res.end(JSON.stringify(body));
}

async function readBody(req) {
  return new Promise((resolve, reject) => {
    const chunks = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      if (!raw) return resolve({});
      try { resolve(JSON.parse(raw)); } catch (e) { reject(e); }
    });
    req.on("error", reject);
  });
}

async function kh(path, init = {}) {
  const url = `${KH_BASE}${path}`;
  const r = await fetch(url, {
    ...init,
    headers: {
      Authorization: `Bearer ${KH_KEY}`,
      "content-type": "application/json",
      ...(init.headers || {}),
    },
  });
  const text = await r.text();
  let body;
  try { body = JSON.parse(text); } catch { body = { raw: text }; }
  return { status: r.status, body };
}

// ---- Public config projection (no secrets) --------------------------
function publicConfig() {
  const explorer = `https://sepolia.etherscan.io`;
  return {
    workflowId: KH_WORKFLOW_ID,
    khKeyConfigured: Boolean(KH_KEY),
    contract: {
      address: KH_CONTRACT,
      name: "CosellEscrow",
      explorer: `${explorer}/address/${KH_CONTRACT}`,
      function: "release(bytes32 depositId)",
      selector: "0x67d42a8b",
    },
    keeper: {
      address: KH_KEEPER,
      type: "turnkey",
      role: "releaseAuth on CosellEscrow (EIP-7702)",
      explorer: `${explorer}/address/${KH_KEEPER}`,
    },
    chain: {
      chainId: KH_CHAIN_ID,
      name: "Ethereum Sepolia",
      explorer,
    },
    demoDepositId: KH_DEMO_DEPOSIT_ID,
    kh: {
      dashboard: `${KH_BASE}/workflows/${KH_WORKFLOW_ID}`,
      docs: "https://docs.keeperhub.com",
    },
    // Full-loop UI: judge signs their own deposit, we auto-fire release.
    fullLoop: {
      listingId: KH_DEMO_LISTING_ID,
      registry: KH_REGISTRY,
      registryExplorer: `${explorer}/address/${KH_REGISTRY}`,
      usdc: KH_USDC,
      usdcExplorer: `${explorer}/token/${KH_USDC}`,
      depositAmountRaw: KH_DEMO_DEPOSIT_USDC,
      depositAmountHuman: "0.10",
      productLabel: "KH-DEMO-1784730454",
      faucets: {
        eth: "https://cloud.google.com/application/web3/faucet/ethereum/sepolia",
        usdc: "https://faucet.circle.com/",
      },
    },
  };
}

// ---- Autonomous Coach watcher ---------------------------------------
// Proves Coach decides on its own, not just when a browser is open.
//
// SAFETY POSTURE: dry-run unless KH_WATCHER_LIVE=1. In dry-run the loop
// reads chain state and evaluates the rules for real, and records the
// verdict it would have acted on, but never asks KeeperHub to sign
// anything. Unattended transaction submission is an explicit operator
// decision, so it lives behind an env var that a human has to set —
// it never starts happening merely because the process booted.
const KH_RPC_URL = process.env.KH_RPC_URL || "https://ethereum-sepolia-rpc.publicnode.com";
const KH_WATCHER_TICK_MS = Number(process.env.KH_WATCHER_TICK_MS || 20_000);
const KH_WATCHER_ON = process.env.KH_WATCHER !== "0";
const KH_WATCHER_LIVE = process.env.KH_WATCHER_LIVE === "1";

const watcher = createWatcher({
  rpcUrl: KH_RPC_URL,
  contract: KH_CONTRACT,
  tickMs: KH_WATCHER_TICK_MS,
  enabled: KH_WATCHER_ON && Boolean(KH_KEY),
  dryRun: !KH_WATCHER_LIVE,
  // Injected, so the watcher holds no KH credential or transport of its
  // own — it asks this server to fire, exactly as the browser does.
  fireRelease: async (depositId) => {
    const r = await kh(`/api/workflows/${KH_WORKFLOW_ID}/execute`, {
      method: "POST",
      body: JSON.stringify({ input: { depositId } }),
    });
    if (r.status !== 200) throw new Error(`KH ${r.status}: ${JSON.stringify(r.body).slice(0, 200)}`);
    return { executionId: r.body.executionId, status: r.body.status };
  },
});
watcher.start();

// ---- HTTP server ----------------------------------------------------
const server = createServer(async (req, res) => {
  try {
    const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
    const path = url.pathname;

    if (req.method === "GET" && (path === "/" || path === "/index.html")) {
      res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
      res.end(INDEX_HTML);
      return;
    }
    if (req.method === "GET" && path === "/app.js") {
      res.writeHead(200, {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "no-store",
      });
      res.end(APP_JS);
      return;
    }
    if (req.method === "GET" && path === "/auditor.js") {
      res.writeHead(200, {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "no-store",
      });
      res.end(AUDITOR_JS);
      return;
    }
    if (req.method === "GET" && path === "/cfo.js") {
      res.writeHead(200, {
        "content-type": "application/javascript; charset=utf-8",
        "cache-control": "no-store",
      });
      res.end(CFO_JS);
      return;
    }
    // ---- autonomous watcher -----------------------------------------
    if (req.method === "GET" && path === "/autonomous") {
      return json(res, 200, watcher.state());
    }
    if (req.method === "POST" && path === "/autonomous/track") {
      let body = {};
      try { body = await readBody(req); }
      catch (e) { return json(res, 400, { error: "invalid_json", detail: String(e) }); }
      const depositId = body.depositId;
      if (!/^0x[0-9a-fA-F]{64}$/.test(depositId || "")) {
        return json(res, 400, { error: "invalid_deposit_id", detail: "must be 0x + 64 hex chars" });
      }
      const rec = watcher.track(depositId, {
        source: body.source || "api",
        buyerConfirmed: Boolean(body.buyerConfirmed),
      });
      return json(res, 200, {
        tracked: true,
        depositId: rec.depositId,
        status: rec.status,
        buyerConfirmed: Boolean(rec.buyerConfirmed),
      });
    }
    // The buyer accepting delivery is an off-chain fact the chain cannot
    // tell the loop. Recording it here is what lets the watcher release
    // before the acceptance window expires — and it is the buyer's own
    // action, not an operator reaching for the release button.
    if (req.method === "POST" && path === "/autonomous/confirm") {
      let body = {};
      try { body = await readBody(req); }
      catch (e) { return json(res, 400, { error: "invalid_json", detail: String(e) }); }
      const depositId = body.depositId;
      if (!/^0x[0-9a-fA-F]{64}$/.test(depositId || "")) {
        return json(res, 400, { error: "invalid_deposit_id", detail: "must be 0x + 64 hex chars" });
      }
      const rec = watcher.confirm(depositId);
      const st = watcher.state();
      // Tell the caller whether the loop is going to act on this, so the
      // browser knows not to fire its own release. Without this both
      // raced the same deposit: one won, the other reverted on the
      // escrow's idempotency guard and printed an error at the exact
      // moment the release had in fact succeeded.
      const handedOff = st.running && !st.dryRun && rec.status === "watching";
      return json(res, 200, {
        depositId: rec.depositId,
        buyerConfirmed: Boolean(rec.buyerConfirmed),
        status: rec.status,
        handedOff,
        tickMs: st.tickMs,
        note: handedOff
          ? "The autonomous watcher owns this release — do not fire it separately."
          : "Watcher is not armed for this deposit; the caller should fire the release itself.",
      });
    }
    // One evaluation pass on demand — the same code the interval calls.
    // Handy for a judge who does not want to wait out a tick.
    if (req.method === "POST" && path === "/autonomous/tick") {
      await watcher.tick();
      return json(res, 200, watcher.state());
    }

    if (req.method === "GET" && path === "/healthz") {
      res.writeHead(200, { "content-type": "text/plain" });
      res.end("ok");
      return;
    }
    if (req.method === "GET" && path === "/config") {
      return json(res, 200, publicConfig());
    }
    if (req.method === "GET" && path === "/status") {
      if (!KH_KEY) return json(res, 503, { error: "KH_API_KEY not configured on server" });
      const r = await kh(`/api/workflows/${KH_WORKFLOW_ID}/executions`);
      if (r.status !== 200) return json(res, 502, { error: "kh_upstream", detail: r.body });
      // Trim to the client-safe subset.
      const trim = (e) => ({
        id: e.id,
        status: e.status,
        startedAt: e.startedAt,
        completedAt: e.completedAt,
        duration: e.duration,
        error: e.error,
        input: e.input,
        transactionHashes: (e.transactionHashes || []).map((t) =>
          typeof t === "string" ? { hash: t } : { hash: t.hash, nodeName: t.nodeName },
        ),
        gasUsedWei: e.gasUsedWei,
      });
      const executions = (r.body || []).slice(0, 10).map(trim);
      return json(res, 200, { workflowId: KH_WORKFLOW_ID, executions });
    }
    if (req.method === "POST" && path === "/demo-release") {
      if (!KH_KEY) return json(res, 503, { error: "KH_API_KEY not configured on server" });
      let body = {};
      try { body = await readBody(req); }
      catch (e) { return json(res, 400, { error: "invalid_json", detail: String(e) }); }
      const depositId = body.depositId || KH_DEMO_DEPOSIT_ID;
      if (!/^0x[0-9a-fA-F]{64}$/.test(depositId)) {
        return json(res, 400, { error: "invalid_deposit_id", detail: "must be 0x + 64 hex chars" });
      }
      const r = await kh(`/api/workflows/${KH_WORKFLOW_ID}/execute`, {
        method: "POST",
        body: JSON.stringify({ input: { depositId } }),
      });
      if (r.status !== 200) return json(res, 502, { error: "kh_execute_failed", detail: r.body });
      return json(res, 200, {
        executionId: r.body.executionId,
        status: r.body.status,
        depositId,
        statusUrl: "/status",
      });
    }

    res.writeHead(404, { "content-type": "text/plain" });
    res.end("not found\n");
  } catch (e) {
    // eslint-disable-next-line no-console
    console.error("[keeperhub-escrow] handler error:", e);
    json(res, 500, { error: "server_error", detail: String(e?.message || e) });
  }
});

server.listen(PORT, "0.0.0.0", () => {
  // eslint-disable-next-line no-console
  console.log(
    `[keeperhub-escrow] listening on :${PORT}  workflow=${KH_WORKFLOW_ID}  kh_key=${KH_KEY ? "set" : "MISSING"}`,
  );
});
