/**
 * Real x402 client for KaJota Coach's premium endpoint — produces a SIGNED
 * payment and completes a live on-chain settlement on Casper.
 *
 * Why Node and not the Python `x402_demo.py`: the signing step is secp256k1
 * EIP-712 over a Casper `transfer_with_authorization`, using Casper's custom
 * EIP-712 domain. That's audited cryptography in `@make-software/casper-x402`
 * + `casper-js-sdk` — reimplementing it in Python would be unjustified risk.
 * So the *server* side is pure Python (this repo), and the *client* signer
 * reuses Casper's official library here. `wrapFetchWithPayment` does the whole
 * 402 → sign → retry dance; we just point it at /coach/premium.
 *
 * Setup:
 *   cd agent/scripts && npm install
 *   export CLIENT_PRIVATE_KEY_PATH=./payer.pem      # PEM for the payer account
 *   export CLIENT_KEY_ALGO=secp256k1                # matches the demo account
 *   export SERVER_URL=http://localhost:8080
 *   node x402_client.mjs
 *
 * The payer account must hold the payment asset (testnet Wrapped CSPR) — wrap
 * some faucet CSPR first. The merchant (X402_PAY_TO on the server) receives it.
 */

import { config } from "dotenv";
import { x402Client, x402HTTPClient, wrapFetchWithPayment } from "@x402/fetch";
// Both exported from the package root (see @make-software/casper-x402 index).
import { createClientCasperSigner, ExactCasperScheme } from "@make-software/casper-x402";
import casperSdk from "casper-js-sdk";

const { KeyAlgorithm } = casperSdk;

config();

const keyPath = process.env.CLIENT_PRIVATE_KEY_PATH;
const keyAlgo = process.env.CLIENT_KEY_ALGO || "secp256k1";
const baseURL = process.env.SERVER_URL || "http://localhost:8080";
const endpointPath = process.env.ENDPOINT_PATH || "/coach/premium";
const message = process.env.MESSAGE || null;
const userId = process.env.USER_ID || "demo-user-1";

async function main() {
  if (!keyPath) {
    console.error("❌ CLIENT_PRIVATE_KEY_PATH is required (PEM-encoded payer key)");
    process.exit(1);
  }

  const algorithm =
    keyAlgo === "secp256k1" ? KeyAlgorithm.SECP256K1 : KeyAlgorithm.ED25519;
  const signer = await createClientCasperSigner(keyPath, algorithm);

  // Register the Casper exact scheme; prefer any casper:* option the server offers.
  const client = new x402Client((_v, options) => {
    const match = options.find(o => o.network.startsWith("casper:"));
    return match || options[0];
  }).register("casper:*", new ExactCasperScheme(signer));

  const fetchWithPayment = wrapFetchWithPayment(fetch, client);
  const url = `${baseURL}${endpointPath}`;

  console.log(`🌐 POST ${url}  (will pay on 402)\n`);
  const response = await fetchWithPayment(url, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ message, userId }),
  });

  const body = await response.json();
  console.log(`✅ HTTP ${response.status}`);
  console.log("Premium insight:", body.response);
  if (body.settlement) {
    console.log("\n💰 On-chain settlement:");
    console.log("   network:    ", body.settlement.network);
    console.log("   deploy hash:", body.settlement.transaction);
    console.log("   payer:      ", body.settlement.payer);
  }

  // The settlement receipt also rides in the X-PAYMENT-RESPONSE header.
  const settle = new x402HTTPClient(client).getPaymentSettleResponse(name =>
    response.headers.get(name),
  );
  if (settle) console.log("\n📜 X-PAYMENT-RESPONSE:", settle);
}

main().catch(err => {
  console.error("❌", err?.response?.data?.error ?? err?.message ?? err);
  process.exit(1);
});
