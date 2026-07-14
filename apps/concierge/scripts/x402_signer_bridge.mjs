/**
 * x402 signer bridge — a tiny local HTTP endpoint that turns a Casper x402
 * price tag into a signed `X-PAYMENT` payload.
 *
 * The mobile Premium screen can't sign on-device easily (secp256k1 EIP-712
 * over Casper's domain). So it POSTs the 402 requirements here; this bridge
 * signs with Casper's audited `@make-software/casper-x402` + `casper-js-sdk`
 * and returns the base64 payload the app re-sends to settle. One tap, no paste.
 *
 *   POST /sign   { "requirements": <PaymentRequirements> }  →  { "xPayment": "<base64>" }
 *   GET  /health →  { "ok": true, "account": "00...", "algo": "secp256k1" }
 *
 * Run:
 *   cd agent/scripts && npm install
 *   export CLIENT_PRIVATE_KEY_PATH=./payer.pem    # payer key (holds Wrapped CSPR)
 *   export CLIENT_KEY_ALGO=secp256k1
 *   node x402_signer_bridge.mjs                    # listens on :4040
 *
 * Point the app at it via app.json → extra.casperSignerUrl (default
 * http://localhost:4040/sign — reachable from the iOS simulator as localhost).
 *
 * SECURITY: this holds a private key and signs on request. It's a LOCAL demo
 * aid — bind to localhost, never expose it publicly.
 */
import { createServer } from "node:http";
import { createClientCasperSigner, ExactCasperScheme } from "@make-software/casper-x402";
import casperSdk from "casper-js-sdk";

const { KeyAlgorithm } = casperSdk;

const PORT = Number(process.env.SIGNER_PORT || 4040);
const X402_VERSION = Number(process.env.X402_VERSION || 2);
const keyPath = process.env.CLIENT_PRIVATE_KEY_PATH;
const keyAlgo = process.env.CLIENT_KEY_ALGO || "secp256k1";

if (!keyPath) {
  console.error("❌ CLIENT_PRIVATE_KEY_PATH is required (PEM-encoded payer key)");
  process.exit(1);
}

const algorithm =
  keyAlgo === "secp256k1" ? KeyAlgorithm.SECP256K1 : KeyAlgorithm.ED25519;
const signer = await createClientCasperSigner(keyPath, algorithm);
const scheme = new ExactCasperScheme(signer);

/** Read and JSON-parse a request body. */
function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", chunk => (data += chunk));
    req.on("end", () => {
      try {
        resolve(data ? JSON.parse(data) : {});
      } catch (e) {
        reject(e);
      }
    });
    req.on("error", reject);
  });
}

function send(res, status, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(status, {
    "Content-Type": "application/json",
    // The app is a different origin (Expo dev server); allow it.
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
  });
  res.end(body);
}

const server = createServer(async (req, res) => {
  if (req.method === "OPTIONS") return send(res, 204, {});

  if (req.method === "GET" && req.url === "/health") {
    return send(res, 200, {
      ok: true,
      account: signer.accountAddress(),
      algo: keyAlgo,
    });
  }

  if (req.method === "POST" && (req.url === "/sign" || req.url === "/")) {
    try {
      const { requirements } = await readBody(req);
      if (!requirements || typeof requirements !== "object") {
        return send(res, 400, { error: "body must be { requirements: <PaymentRequirements> }" });
      }

      // Sign the transfer_with_authorization for these requirements.
      const result = await scheme.createPaymentPayload(X402_VERSION, requirements);

      // Assemble the full v2 PaymentPayload envelope the facilitator expects:
      // top-level `accepted` echoes the requirements, `payload` carries the
      // signature + authorization. base64 it for the X-PAYMENT header.
      const full = {
        x402Version: result.x402Version ?? X402_VERSION,
        accepted: requirements,
        payload: result.payload,
      };
      const xPayment = Buffer.from(JSON.stringify(full)).toString("base64");

      console.log(`✍️  signed payment for ${requirements.amount} of ${requirements.asset?.slice(0, 10)}…`);
      return send(res, 200, { xPayment });
    } catch (err) {
      const message = err?.message ?? String(err);
      console.error("❌ sign failed:", message);
      return send(res, 500, { error: message });
    }
  }

  send(res, 404, { error: "not found — use POST /sign or GET /health" });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`🔐 x402 signer bridge on http://localhost:${PORT}`);
  console.log(`   payer account: ${signer.accountAddress()}  (${keyAlgo})`);
  console.log(`   POST /sign { requirements } → { xPayment }`);
});
