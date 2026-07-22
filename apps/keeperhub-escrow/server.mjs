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

const INDEX_HTML = readFileSync(join(__dir, "index.html"), "utf8");
const APP_JS = readFileSync(join(__dir, "app.js"), "utf8");

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
  };
}

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
