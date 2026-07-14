/**
 * Deploy our own Cep18X402 token to Casper Testnet.
 *
 * Cep18X402 is an Odra CEP-18 that implements `transfer_with_authorization`
 * (the EIP-712 extension Casper's x402 `exact` scheme signs). Deploying our
 * OWN instance does two things for the buildathon:
 *   1. satisfies the "Working Smart Contracts — functional, deployed contracts
 *      on Casper Testnet" judging criterion (we ship a real contract, not just
 *      reuse the shared WCSPR), and
 *   2. gives us an asset our x402 settlements land on-chain against.
 *
 * The install args mirror Casper's reference deployer (infra/local/deployer/
 * deployer.cs), adjusted for TESTNET: `chain_id` is the CAIP-2 network baked
 * into the token's EIP-712 domain, so it MUST be `casper:casper-test`, and the
 * token `name` here MUST equal X402_ASSET_NAME in the paywall config (the
 * facilitator rebuilds the same domain to verify the signature).
 *
 * SAFETY: this SPENDS ~800 testnet CSPR (the install payment). It only submits
 * when you pass `--submit`; without it, it builds, signs, and prints a dry run
 * so you can sanity-check the args and the transaction hash first.
 *
 * Usage:
 *   cd agent/scripts && npm install
 *   export CLIENT_PRIVATE_KEY_PATH=./payer.pem
 *   export CLIENT_KEY_ALGO=secp256k1
 *   node deploy_cep18x402.mjs            # dry run (no spend)
 *   node deploy_cep18x402.mjs --submit   # actually deploy
 *
 * After a successful deploy the token's package hash appears under your
 * account's named keys as `kajota_x402_package_hash` (also printed here).
 * Put it in agent/.env.casper:
 *   X402_ASSET=<package hash, no "hash-" prefix>
 *   X402_ASSET_NAME="<TOKEN_NAME below>"
 */
import { readFile } from "node:fs/promises";
import casperSdk from "casper-js-sdk";

const {
  PrivateKey,
  KeyAlgorithm,
  Args,
  CLValue,
  SessionBuilder,
  RpcClient,
  HttpHandler,
} = casperSdk;

// ---- config (env-overridable) --------------------------------------------
const RPC_URL = process.env.CASPER_RPC || "https://node.testnet.casper.network/rpc";
const CHAIN_NAME = process.env.CHAIN_NAME || "casper-test";
const CAIP2 = process.env.X402_NETWORK || "casper:casper-test";
const KEY_PATH = process.env.CLIENT_PRIVATE_KEY_PATH;
const KEY_ALGO = process.env.CLIENT_KEY_ALGO || "secp256k1";

// Token identity. TOKEN_NAME feeds the EIP-712 domain → keep it in sync with
// X402_ASSET_NAME in agent/.env.casper.
const TOKEN_NAME = process.env.TOKEN_NAME || "KaJota USD";
const TOKEN_SYMBOL = process.env.TOKEN_SYMBOL || "KJUSD";
const DECIMALS = Number(process.env.TOKEN_DECIMALS || 9);
const INITIAL_SUPPLY = process.env.INITIAL_SUPPLY || "1000000000000000"; // 1M @ 9dp
const PACKAGE_KEY_NAME = process.env.PACKAGE_KEY_NAME || "kajota_x402_package_hash";
const PAYMENT = process.env.INSTALL_PAYMENT || "800000000000"; // 800 CSPR, per reference

const SUBMIT = process.argv.includes("--submit");

async function main() {
  if (!KEY_PATH) {
    console.error("❌ CLIENT_PRIVATE_KEY_PATH is required (PEM-encoded deployer key)");
    process.exit(1);
  }

  const algorithm =
    KEY_ALGO === "secp256k1" ? KeyAlgorithm.SECP256K1 : KeyAlgorithm.ED25519;
  const pem = await readFile(KEY_PATH, "utf-8");
  const privateKey = PrivateKey.fromPem(pem, algorithm);
  const publicKey = privateKey.publicKey;

  const wasm = new Uint8Array(await readFile(new URL("./contracts/Cep18X402.wasm", import.meta.url)));

  // Install args — mirror deployer.cs, testnet chain_id.
  const args = Args.fromMap({
    name: CLValue.newCLString(TOKEN_NAME),
    symbol: CLValue.newCLString(TOKEN_SYMBOL),
    decimals: CLValue.newCLUint8(DECIMALS),
    initial_supply: CLValue.newCLUInt256(INITIAL_SUPPLY),
    chain_id: CLValue.newCLString(CAIP2),
    odra_cfg_is_upgradable: CLValue.newCLValueBool(true),
    odra_cfg_is_upgrade: CLValue.newCLValueBool(false),
    odra_cfg_allow_key_override: CLValue.newCLValueBool(true),
    odra_cfg_package_hash_key_name: CLValue.newCLString(PACKAGE_KEY_NAME),
  });

  console.log("── Cep18X402 deploy (Casper Testnet) ──");
  console.log(`  deployer   ${publicKey.toHex()}`);
  console.log(`  account    00${publicKey.accountHash().toHex()}`);
  console.log(`  rpc        ${RPC_URL}   chain=${CHAIN_NAME}`);
  console.log(`  token      name="${TOKEN_NAME}" symbol=${TOKEN_SYMBOL} decimals=${DECIMALS}`);
  console.log(`  supply     ${INITIAL_SUPPLY}   caip2=${CAIP2}`);
  console.log(`  payment    ${PAYMENT} motes (~${Number(PAYMENT) / 1e9} CSPR)`);
  console.log(`  pkg key    ${PACKAGE_KEY_NAME}\n`);

  const tx = new SessionBuilder()
    .from(publicKey)
    .wasm(wasm)
    .installOrUpgrade()
    .runtimeArgs(args)
    .chainName(CHAIN_NAME)
    // The SDK serializer expects a Number here (not BigInt). 800 CSPR is well
    // within Number.MAX_SAFE_INTEGER, so this is lossless.
    .payment(Number(PAYMENT))
    .build();
  tx.sign(privateKey);

  const hash = txHash(tx);
  console.log(`  tx hash    ${hash || "(computed on submit)"}`);

  if (!SUBMIT) {
    console.log("\n🟡 DRY RUN — nothing submitted. Re-run with --submit to deploy (spends ~800 CSPR).");
    return;
  }

  const rpc = new RpcClient(new HttpHandler(RPC_URL));
  console.log("\n▸ submitting install transaction…");
  const res = await rpc.putTransaction(tx);
  const submittedHash = String(res?.transactionHash?.toHex?.() ?? res?.transactionHash ?? hash);
  console.log(`✅ submitted. tx: ${submittedHash}`);
  console.log(`   explorer: https://testnet.cspr.live/transaction/${submittedHash}`);

  console.log("\n▸ waiting for execution (up to ~90s)…");
  await waitForTx(rpc, tx);

  console.log(`\n▸ reading package hash from named key "${PACKAGE_KEY_NAME}"…`);
  const pkg = await findPackageHash(rpc, publicKey);
  if (pkg) {
    console.log(`\n🎉 Cep18X402 deployed. package hash:\n   ${pkg}\n`);
    console.log("Set in agent/.env.casper:");
    console.log(`   X402_ASSET=${pkg.replace(/^(hash-|contract-package-)/, "")}`);
    console.log(`   X402_ASSET_NAME="${TOKEN_NAME}"`);
  } else {
    console.log(
      `\n⚠ Could not auto-read the package hash. It's under your account's named keys` +
        ` as "${PACKAGE_KEY_NAME}" — view it on https://testnet.cspr.live and set X402_ASSET.`,
    );
  }
}

/** Best-effort transaction-hash accessor across SDK shapes. */
function txHash(tx) {
  try {
    return (
      tx?.hash?.toHex?.() ??
      tx?.getTransactionV1?.()?.hash?.toHex?.() ??
      tx?.getTransactionWrapper?.()?.transactionV1?.hash?.toHex?.() ??
      ""
    );
  } catch {
    return "";
  }
}

/** Poll until the transaction is retrievable (executed) or timeout. */
async function waitForTx(rpc, tx) {
  const hash = txHash(tx);
  if (!hash) return;
  for (let i = 0; i < 30; i++) {
    try {
      const r = await rpc.getTransactionByTransactionHash(hash);
      if (r) {
        console.log("   ✓ transaction executed");
        return;
      }
    } catch {
      /* not yet */
    }
    await sleep(3000);
  }
  console.log("   … still pending; check the explorer link above.");
}

/** Look up the token package hash under the deployer account's named keys. */
async function findPackageHash(rpc, publicKey) {
  try {
    const info = await rpc.getAccountInfo(publicKey);
    const account = info?.account ?? info?.Account ?? info;
    const namedKeys = account?.namedKeys?.keys ?? account?.namedKeys ?? account?.NamedKeys ?? [];
    const list = Array.isArray(namedKeys) ? namedKeys : namedKeys?.keys ?? [];
    for (const nk of list) {
      const name = nk?.name ?? nk?.Name;
      if (name === PACKAGE_KEY_NAME) {
        return String(nk?.key?.toString?.() ?? nk?.key ?? nk?.Key ?? "");
      }
    }
  } catch (e) {
    console.log(`   (named-key lookup failed: ${e?.message ?? e})`);
  }
  return "";
}

const sleep = ms => new Promise(r => setTimeout(r, ms));

main().catch(err => {
  console.error("❌", err?.message ?? err);
  process.exit(1);
});
