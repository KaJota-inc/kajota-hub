/**
 * One-shot x402 settlement — sign a payment and settle it on Casper directly
 * through the facilitator (bypasses the agent, for a fast on-chain proof).
 *
 * Builds the same PaymentRequirements the server's /coach/premium emits, signs
 * a `transfer_with_authorization` with the payer key (Casper's audited
 * casper-x402 + casper-js-sdk), and POSTs to the facilitator's /settle — which
 * submits the CEP-18 transfer on-chain and returns the deploy hash.
 *
 * Env: CLIENT_PRIVATE_KEY_PATH, CLIENT_KEY_ALGO, and the X402_* config
 * (mirrors agent/.env.casper). API key from X402_FACILITATOR_API_KEY.
 */
import { readFile } from "node:fs/promises";
import { createClientCasperSigner, ExactCasperScheme } from "@make-software/casper-x402";
import casperSdk from "casper-js-sdk";

const { KeyAlgorithm } = casperSdk;

const FACILITATOR = (process.env.X402_FACILITATOR_URL || "https://x402-facilitator.cspr.cloud").replace(/\/$/, "");
const KEY = process.env.X402_FACILITATOR_API_KEY || process.env.CSPR_CLOUD_API_KEY;
const X402_VERSION = Number(process.env.X402_VERSION || 2);

const requirements = {
  scheme: "exact",
  network: process.env.X402_NETWORK || "casper:casper-test",
  amount: process.env.X402_MAX_AMOUNT || "1000000",
  resource: "https://api.kajota.test/coach/premium",
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
};

async function main() {
  if (!KEY) throw new Error("X402_FACILITATOR_API_KEY is required");
  if (!requirements.payTo || !requirements.asset) throw new Error("X402_PAY_TO and X402_ASSET are required");

  const keyPath = process.env.CLIENT_PRIVATE_KEY_PATH || "./payer.pem";
  const algo = (process.env.CLIENT_KEY_ALGO || "secp256k1") === "secp256k1" ? KeyAlgorithm.SECP256K1 : KeyAlgorithm.ED25519;
  await readFile(keyPath); // fail early if missing
  const signer = await createClientCasperSigner(keyPath, algo);
  const scheme = new ExactCasperScheme(signer);

  console.log("── x402 settlement ──");
  console.log(`  payer   ${signer.accountAddress()}`);
  console.log(`  asset   ${requirements.asset} (${requirements.extra.name})`);
  console.log(`  amount  ${requirements.amount}  →  payTo ${requirements.payTo}`);
  console.log(`  facilitator ${FACILITATOR}\n`);

  console.log("▸ signing transfer_with_authorization…");
  const result = await scheme.createPaymentPayload(X402_VERSION, requirements);
  const paymentPayload = {
    x402Version: result.x402Version ?? X402_VERSION,
    accepted: requirements,
    payload: result.payload,
  };

  const body = { x402Version: X402_VERSION, paymentPayload, paymentRequirements: requirements };

  // Verify first (cheap, no chain write) — surfaces field errors clearly.
  console.log("▸ /verify …");
  const vr = await post(`${FACILITATOR}/verify`, body);
  console.log("  ", JSON.stringify(vr));
  if (!vr.isValid) throw new Error(`verify rejected: ${vr.invalidReason} ${vr.invalidMessage ?? ""}`);

  console.log("▸ /settle …");
  const sr = await post(`${FACILITATOR}/settle`, body);
  console.log("  ", JSON.stringify(sr));

  const tx = sr.transaction || sr.txHash || sr.deployHash;
  if (sr.success && tx) {
    console.log(`\n🎉 SETTLED on Casper. tx: ${tx}`);
    console.log(`   explorer: https://testnet.cspr.live/transaction/${tx}`);
  } else {
    console.log(`\n⚠ settle did not report success — full response above.`);
  }
}

async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: KEY },
    body: JSON.stringify(body),
  });
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${url} → HTTP ${res.status}: ${text.slice(0, 300)}`);
  }
}

main().catch(err => {
  console.error("❌", err?.message ?? err);
  process.exit(1);
});
