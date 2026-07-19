/**
 * KaJota Coach × Casper — live x402 judge demo server.
 *
 * Serves a one-page demo that lets anyone click "Pay & settle on Casper" and
 * watch a REAL CEP-18 micropayment settle on-chain — signing a
 * `transfer_with_authorization` with the payer key and POSTing to the
 * production CSPR.cloud facilitator's /verify + /settle. No mock mode.
 *
 * Reuses the exact audited signer from settle_once.mjs (@make-software/casper-x402
 * + casper-js-sdk) — no crypto is reimplemented here.
 *
 * The payment is a self-transfer (payTo == payer) of 0.001 KaJota USD with gas
 * paid by the facilitator's sponsored feePayer, so it is net-zero cost and safe
 * to run unlimited times. Testnet only.
 *
 * Env: CLIENT_PRIVATE_KEY_PATH (or CLIENT_PRIVATE_KEY_PEM inline), CLIENT_KEY_ALGO,
 * X402_FACILITATOR_API_KEY, and the X402_* config (mirrors agent/.env.casper).
 */
import { readFile, writeFile } from "node:fs/promises";
import { createServer } from "node:http";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { createClientCasperSigner, ExactCasperScheme } from "@make-software/casper-x402";
import casperSdk from "casper-js-sdk";

const { KeyAlgorithm } = casperSdk;
const __dir = dirname(fileURLToPath(import.meta.url));

const PORT = Number(process.env.JUDGE_PORT || process.env.PORT || 4050);
const FACILITATOR = (process.env.X402_FACILITATOR_URL || "https://x402-facilitator.cspr.cloud").replace(/\/$/, "");
const KEY = process.env.X402_FACILITATOR_API_KEY || process.env.CSPR_CLOUD_API_KEY;
const X402_VERSION = Number(process.env.X402_VERSION || 2);
const NETWORK = process.env.X402_NETWORK || "casper:casper-test";

const requirements = () => ({
  scheme: "exact",
  network: NETWORK,
  amount: process.env.X402_MAX_AMOUNT || "1000000",
  resource: process.env.X402_RESOURCE || "https://kajota-hub.onrender.com/concierge/coach/premium",
  description: "KaJota Coach — premium agentic purchase insight",
  mimeType: "application/json",
  payTo: process.env.X402_PAY_TO,
  maxTimeoutSeconds: Number(process.env.X402_TIMEOUT_SECONDS || 60),
  asset: process.env.X402_ASSET,
  extra: {
    name: process.env.X402_ASSET_NAME || "KaJota USD",
    version: process.env.X402_ASSET_VERSION || "1",
    decimals: process.env.X402_ASSET_DECIMALS || "9",
    ...(process.env.X402_FEE_PAYER ? { feePayer: process.env.X402_FEE_PAYER } : {}),
  },
});

// ── resolve the payer key: prefer an inline PEM env (Render secret), else a path ──
async function resolveKeyPath() {
  const inline = process.env.CLIENT_PRIVATE_KEY_PEM;
  if (inline && inline.includes("BEGIN")) {
    const p = join(__dir, "payer.runtime.pem");
    await writeFile(p, inline.replace(/\\n/g, "\n"), { mode: 0o600 });
    return p;
  }
  return process.env.CLIENT_PRIVATE_KEY_PATH || join(__dir, "payer.pem");
}

let scheme, payerAddress;
async function initSigner() {
  const keyPath = await resolveKeyPath();
  const algo = (process.env.CLIENT_KEY_ALGO || "secp256k1") === "secp256k1"
    ? KeyAlgorithm.SECP256K1 : KeyAlgorithm.ED25519;
  await readFile(keyPath);
  const signer = await createClientCasperSigner(keyPath, algo);
  scheme = new ExactCasperScheme(signer);
  payerAddress = signer.accountAddress();
  console.log(`[judge] signer ready — payer ${payerAddress}`);
}

async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: KEY },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  try { return JSON.parse(text); }
  catch { throw new Error(`${url} → HTTP ${res.status}: ${text.slice(0, 200)}`); }
}

// A real, on-chain-confirmed settlement to fall back to if the shared sponsored
// gas account is momentarily drained (a cohort-wide condition, not our bug).
let lastGoodTx = process.env.FALLBACK_TX || "85041ff37d4e7b4840f738a465bfd933875bdf81604ced3fc6b62dba5fe1d7ea";

async function settleOnce() {
  const req = requirements();
  if (!KEY) throw new Error("facilitator API key not configured");
  if (!req.payTo || !req.asset) throw new Error("X402_PAY_TO and X402_ASSET required");
  const result = await scheme.createPaymentPayload(X402_VERSION, req);
  const paymentPayload = { x402Version: result.x402Version ?? X402_VERSION, accepted: req, payload: result.payload };
  const body = { x402Version: X402_VERSION, paymentPayload, paymentRequirements: req };
  const vr = await post(`${FACILITATOR}/verify`, body);
  if (!vr.isValid) throw new Error(`verify rejected: ${vr.invalidReason || ""} ${vr.invalidMessage || ""}`.trim());
  const sr = await post(`${FACILITATOR}/settle`, body);
  const tx = sr.transaction || sr.txHash || sr.deployHash;
  if (sr.success && tx) {
    lastGoodTx = tx;
    return { tx, explorer: `https://testnet.cspr.live/transaction/${tx}`, verified: true, payer: sr.payer || payerAddress };
  }
  // Graceful degradation: the facilitator's SHARED sponsored gas account
  // (81d557c9…) drains under whole-cohort load → "insufficient balance". The
  // signature + verify still pass; only the on-chain submit is gas-starved.
  const reason = `${sr.errorReason || ""} ${sr.errorMessage || ""}`;
  if (/insufficient balance|put_deploy_failed/i.test(reason)) {
    const err = new Error("shared testnet gas momentarily exhausted");
    err.gasOut = true;
    err.fallbackTx = lastGoodTx;
    err.fallbackExplorer = `https://testnet.cspr.live/transaction/${lastGoodTx}`;
    throw err;
  }
  throw new Error(`settle did not succeed: ${JSON.stringify(sr).slice(0, 200)}`);
}

// ── light abuse guard (funds are net-zero, so this only protects the facilitator) ──
let inFlight = false, last = 0, dayCount = 0, dayStamp = 0;
const MIN_GAP_MS = 6000, DAY_CAP = 500;

const html = readFileSync(join(__dir, "index.html"));
const send = (res, code, type, body) => { res.writeHead(code, { "Content-Type": type, "Access-Control-Allow-Origin": "*" }); res.end(body); };

const server = createServer(async (req, res) => {
  const url = (req.url || "/").split("?")[0].replace(/\/$/, "") || "/";
  try {
    if (req.method === "GET" && (url === "/" || url === "/judge" || url === "/index.html"))
      return send(res, 200, "text/html; charset=utf-8", html);
    if (req.method === "GET" && (url === "/healthz" || url === "/judge/healthz"))
      return send(res, 200, "application/json", JSON.stringify({ ok: true, payer: payerAddress }));
    if (req.method === "GET" && (url === "/challenge" || url === "/judge/challenge"))
      return send(res, 402, "application/json", JSON.stringify({ x402Version: X402_VERSION, accepts: [requirements()] }));
    if (req.method === "POST" && (url === "/pay" || url === "/judge/pay")) {
      const now = Date.now();
      if (Math.floor(now / 86400000) !== dayStamp) { dayStamp = Math.floor(now / 86400000); dayCount = 0; }
      if (inFlight) return send(res, 429, "application/json", JSON.stringify({ ok: false, error: "a settlement is already in progress — try again in a moment" }));
      if (now - last < MIN_GAP_MS) return send(res, 429, "application/json", JSON.stringify({ ok: false, error: "please wait a few seconds between settlements" }));
      if (dayCount >= DAY_CAP) return send(res, 429, "application/json", JSON.stringify({ ok: false, error: "daily demo cap reached" }));
      inFlight = true; last = now; dayCount++;
      try { const out = await settleOnce(); return send(res, 200, "application/json", JSON.stringify({ ok: true, ...out })); }
      catch (e) {
        if (e?.gasOut) return send(res, 200, "application/json", JSON.stringify({ ok: false, gasOut: true, error: e.message, fallbackTx: e.fallbackTx, fallbackExplorer: e.fallbackExplorer }));
        return send(res, 200, "application/json", JSON.stringify({ ok: false, error: e?.message || String(e) }));
      }
      finally { inFlight = false; }
    }
    return send(res, 404, "application/json", JSON.stringify({ error: "not found" }));
  } catch (e) {
    return send(res, 500, "application/json", JSON.stringify({ error: e?.message || String(e) }));
  }
});

initSigner()
  .then(() => server.listen(PORT, () => console.log(`[judge] live on :${PORT}`)))
  .catch(err => { console.error("[judge] signer init failed:", err?.message ?? err); process.exit(1); });
