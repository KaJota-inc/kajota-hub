// Pay the x402-gated release endpoint and fire the KeeperHub release.
//
//   npm i viem                       # once
//   export X402_PAYER_KEY=0x…        # Base Sepolia key, holds test USDC
//   node x402-pay.mjs <depositId>
//
// The full agentic path in one script: read the 402 challenge, sign an
// EIP-3009 transferWithAuthorization for the quoted USDC, retry with the
// X-PAYMENT header, and print both receipts — the settlement on Base
// Sepolia and the release on Ethereum Sepolia.
//
// The key never leaves this process, and it is only ever used to sign a
// typed-data authorisation for the exact amount the server quoted. There
// is no approve() and no unlimited allowance: EIP-3009 authorises one
// transfer, scoped to one nonce, with its own validity window.

import { createWalletClient, http, parseAbi } from "viem";
import { privateKeyToAccount } from "viem/accounts";
import { baseSepolia } from "viem/chains";
import { randomBytes } from "node:crypto";

const ENDPOINT =
  process.env.X402_ENDPOINT ||
  "https://kajota-hub.onrender.com/concierge/escrow/schedule-release";
const DEPOSIT_ID = process.argv[2];
const KEY = process.env.X402_PAYER_KEY;

if (!DEPOSIT_ID) { console.error("usage: node x402-pay.mjs <depositId>"); process.exit(1); }
if (!KEY) { console.error("set X402_PAYER_KEY (Base Sepolia, holds test USDC)"); process.exit(1); }

const account = privateKeyToAccount(KEY);
console.log("payer:", account.address);

// ── 1. read the price ────────────────────────────────────────────────
const challenge = await (await fetch(ENDPOINT)).json();
const req = challenge.accepts?.[0];
if (!req) { console.error("no PaymentRequirements in 402:", challenge); process.exit(1); }
if (!req.payTo) {
  console.error("server has no payTo configured — set ETH_X402_PAY_TO in Render.");
  process.exit(1);
}
console.log(
  `quote: ${(Number(req.maxAmountRequired) / 1e6).toFixed(2)} USDC on ${req.network} → ${req.payTo}`,
);

// ── 2. sign the EIP-3009 authorisation ───────────────────────────────
const now = Math.floor(Date.now() / 1000);
const authorization = {
  from: account.address,
  to: req.payTo,
  value: BigInt(req.maxAmountRequired),
  validAfter: BigInt(now - 60),                       // clock-skew slack
  validBefore: BigInt(now + (req.maxTimeoutSeconds ?? 60) + 300),
  nonce: `0x${randomBytes(32).toString("hex")}`,
};

const wallet = createWalletClient({ account, chain: baseSepolia, transport: http() });
const signature = await wallet.signTypedData({
  domain: {
    name: req.extra?.name ?? "USD Coin",
    version: req.extra?.version ?? "2",
    chainId: baseSepolia.id,
    verifyingContract: req.asset,
  },
  types: {
    TransferWithAuthorization: [
      { name: "from", type: "address" },
      { name: "to", type: "address" },
      { name: "value", type: "uint256" },
      { name: "validAfter", type: "uint256" },
      { name: "validBefore", type: "uint256" },
      { name: "nonce", type: "bytes32" },
    ],
  },
  primaryType: "TransferWithAuthorization",
  message: authorization,
});
console.log("signed EIP-3009 authorisation");

// ── 3. pay and execute ───────────────────────────────────────────────
const payload = {
  x402Version: challenge.x402Version ?? 1,
  scheme: req.scheme,
  network: req.network,
  payload: {
    signature,
    authorization: {
      ...authorization,
      value: authorization.value.toString(),
      validAfter: authorization.validAfter.toString(),
      validBefore: authorization.validBefore.toString(),
    },
  },
};

const res = await fetch(ENDPOINT, {
  method: "POST",
  headers: {
    "content-type": "application/json",
    "X-PAYMENT": Buffer.from(JSON.stringify(payload)).toString("base64"),
  },
  body: JSON.stringify({ depositId: DEPOSIT_ID }),
});

const body = await res.json();
console.log("\nHTTP", res.status);
console.log(JSON.stringify(body, null, 2));

if (res.status === 200) {
  const s = body.settlement || {}, k = body.keeper || {};
  console.log("\n── receipts ──");
  console.log("settlement :", s.transaction, `(${s.network})`);
  console.log("             https://sepolia.basescan.org/tx/" + s.transaction);
  console.log("release    :", k.releaseTx, `(${k.network})  status=${k.status}`);
  if (k.releaseTx) console.log("             https://sepolia.etherscan.io/tx/" + k.releaseTx);
  console.log("\nx402 settlements are indexed at https://x402scan.com");
} else {
  console.log("\nnot settled — the error above says why.");
  process.exit(1);
}
