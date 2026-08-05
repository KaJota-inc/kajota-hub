/**
 * Autonomous Coach watcher — the "no human clicks after start" loop.
 *
 * The interactive console proves Coach *can* decide. This proves Coach
 * decides *on its own*: a poll loop reads escrow state directly from
 * Sepolia, runs the same deterministic rules the CFO endpoint runs, and
 * when a deposit becomes releasable it fires the KeeperHub workflow —
 * with no browser open and nobody clicking anything.
 *
 * Scope guard: the loop only considers deposits that were explicitly
 * registered with it (via POST /autonomous/track, which the console
 * calls after a successful deposit). It never scans the chain for
 * arbitrary deposits, so its blast radius is exactly the set of
 * deposits a human handed it, on one contract, on one testnet.
 *
 * Idempotency: a deposit is fired at most once. After the KH workflow
 * is invoked the deposit moves to a terminal local status and the loop
 * stops evaluating it, regardless of what the chain says next. That
 * matters because KH executions are async — re-firing on a slow
 * confirmation would double-submit.
 */

import { evaluateRelease, signalsFromDeposit } from "./cfo.js";

// ---- on-chain reads (raw JSON-RPC, no client library) ---------------

// keccak("getDeposit(bytes32)")[0:4] — verified against the deployed
// contract on Sepolia; returns 5 static words (no offset word) because
// every member of the Escrowed struct is a value type.
const SEL_GET_DEPOSIT = "0x7a86983f";

// CosellEscrow.State
const STATE = ["held", "released", "refunded", "disputed"];

const strip = (h) => (h.startsWith("0x") ? h.slice(2) : h);

/** eth_call getDeposit(depositId) → decoded record, or null if absent. */
async function readDeposit(rpcUrl, contract, depositId) {
  const r = await fetch(rpcUrl, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "eth_call",
      params: [{ to: contract, data: SEL_GET_DEPOSIT + strip(depositId) }, "latest"],
    }),
  });
  const body = await r.json();
  // The contract reverts DepositNotFound for unknown ids — surfaced as
  // an error object rather than empty data.
  if (body.error || !body.result || body.result === "0x") return null;

  const h = strip(body.result);
  const word = (i) => h.slice(i * 64, (i + 1) * 64);
  return {
    listingId: "0x" + word(0),
    buyer: "0x" + word(1).slice(24),
    grossAmountRaw: BigInt("0x" + word(2)),
    depositedAt: Number(BigInt("0x" + word(3))),
    stateCode: Number(BigInt("0x" + word(4))),
    state: STATE[Number(BigInt("0x" + word(4)))] ?? "unknown",
  };
}

// ---- watcher --------------------------------------------------------

const MAX_LOG = 60;

export function createWatcher({
  rpcUrl,
  contract,
  tickMs = 20_000,
  fireRelease,          // async (depositId) => { executionId, status } — injected
  enabled = true,
  // DRY-RUN IS THE DEFAULT AND IS DELIBERATE.
  //
  // In dry-run the loop does everything except the last step: it reads
  // chain state, evaluates the rules, and records the verdict it would
  // have acted on — but never calls `fireRelease`, so no transaction is
  // ever signed or submitted without a human having flipped the flag.
  //
  // Unattended submission of on-chain transactions is a decision an
  // operator should make explicitly, not something that starts happening
  // because a process booted. Set KH_WATCHER_LIVE=1 to opt in.
  dryRun = true,
} = {}) {
  /** depositId -> { depositId, addedAt, status, lastVerdict, executionId, firedAt } */
  const tracked = new Map();
  const log = [];
  let timer = null;
  let lastTickAt = null;
  let ticks = 0;

  const note = (level, depositId, message, extra = {}) => {
    log.unshift({ at: Date.now(), level, depositId, message, ...extra });
    if (log.length > MAX_LOG) log.length = MAX_LOG;
  };

  function track(depositId, meta = {}) {
    const id = depositId.toLowerCase();
    if (tracked.has(id)) {
      // Re-tracking an existing deposit carries new off-chain signals —
      // most importantly the buyer's confirmation, which is the whole
      // reason a deposit becomes releasable before the timeout.
      const existing = tracked.get(id);
      if (meta.buyerConfirmed && !existing.buyerConfirmed) {
        existing.buyerConfirmed = true;
        note("info", id, "buyer confirmed receipt — will release on the next tick");
      }
      return existing;
    }
    const rec = {
      depositId: id,
      addedAt: Date.now(),
      status: "watching",     // watching | released-by-coach | settled-elsewhere | ignored
      lastVerdict: null,
      executionId: null,
      firedAt: null,
      // Off-chain signal the chain cannot tell us. In production this
      // comes from the marketplace's own record of the buyer accepting
      // delivery; here it arrives via POST /autonomous/track.
      buyerConfirmed: false,
      ...meta,
    };
    tracked.set(id, rec);
    note("info", id, `now watching this deposit${rec.buyerConfirmed ? " (buyer already confirmed)" : ""}`);
    return rec;
  }

  /** Record the buyer's acceptance for a deposit already being watched. */
  function confirm(depositId) {
    return track(depositId, { buyerConfirmed: true });
  }

  async function evaluateOne(rec) {
    const onchain = await readDeposit(rpcUrl, contract, rec.depositId);
    if (!onchain) {
      rec.status = "ignored";
      rec.lastVerdict = null;
      note("warn", rec.depositId, "deposit not found on chain — dropping from the watch list");
      return;
    }

    // Someone else (buyer confirm, refund, arbiter) settled it first.
    if (onchain.state !== "held") {
      rec.status = "settled-elsewhere";
      note("info", rec.depositId, `settled outside the loop — on-chain state is '${onchain.state}'`);
      return;
    }

    const verdict = await Promise.resolve(evaluateRelease(signalsFromDeposit({
      depositId: rec.depositId,
      buyer: onchain.buyer,
      grossAmountRaw: onchain.grossAmountRaw,
      listingId: onchain.listingId,
      depositedAt: onchain.depositedAt,
      // Signals the chain cannot tell us. `buyerConfirmed` arrives from
      // the marketplace via POST /autonomous/track; absent it we take the
      // conservative reading that the buyer has NOT confirmed, so the
      // release waits out the acceptance window in the rules engine.
      buyerConfirmed: Boolean(rec.buyerConfirmed),
      sellerShipped: true,
      activeDispute: false,
    })));

    rec.lastVerdict = {
      decision: verdict.decision,
      why: verdict.why,
      at: Date.now(),
      failing: verdict.rules.filter((r) => !r.passed).map((r) => r.name),
    };

    if (verdict.decision !== "release") {
      note(verdict.decision === "reject" ? "err" : "dim", rec.depositId,
        `${verdict.decision.toUpperCase()} — ${verdict.why}`);
      return;
    }

    // Verdict is release.
    note("ok", rec.depositId, `RELEASE — ${verdict.why}`);

    if (dryRun) {
      // Everything above this line already happened for real: the chain
      // read, the rule evaluation, the verdict. Only the signature is
      // withheld. The deposit stays in `watching` so the loop keeps
      // showing its reasoning on every tick rather than going quiet.
      rec.wouldFireAt = Date.now();
      note("warn", rec.depositId,
        "DRY-RUN — would fire the KeeperHub workflow now (set KH_WATCHER_LIVE=1 to arm)");
      return;
    }

    // Fire exactly once.
    rec.status = "released-by-coach";
    rec.firedAt = Date.now();
    try {
      const run = await fireRelease(rec.depositId);
      rec.executionId = run?.executionId ?? null;
      note("ok", rec.depositId,
        `fired KeeperHub workflow autonomously · executionId=${rec.executionId ?? "?"}`,
        { executionId: rec.executionId });
    } catch (e) {
      // Keep the terminal status: we do not want a retry storm against
      // KH if its API is briefly unhappy. A human can re-track the
      // deposit explicitly if they want another attempt.
      note("err", rec.depositId, `KeeperHub invoke failed: ${e.message}`);
    }
  }

  async function tick() {
    lastTickAt = Date.now();
    ticks += 1;
    const live = [...tracked.values()].filter((r) => r.status === "watching");
    for (const rec of live) {
      try {
        await evaluateOne(rec);
      } catch (e) {
        note("err", rec.depositId, `tick error: ${e.message}`);
      }
    }
  }

  function start() {
    if (timer || !enabled) return;
    note("info", null,
      `autonomous watcher started · tick ${Math.round(tickMs / 1000)}s · ` +
      (dryRun ? "DRY-RUN (no transactions will be submitted)" : "LIVE (will submit transactions)"));
    timer = setInterval(() => { tick().catch(() => {}); }, tickMs);
    if (typeof timer.unref === "function") timer.unref();
  }

  function stop() {
    if (timer) clearInterval(timer);
    timer = null;
  }

  function state() {
    return {
      enabled,
      dryRun,
      mode: dryRun ? "dry-run" : "live",
      running: Boolean(timer),
      tickMs,
      ticks,
      lastTickAt,
      nextTickInMs: lastTickAt ? Math.max(0, tickMs - (Date.now() - lastTickAt)) : null,
      contract,
      counts: {
        watching: [...tracked.values()].filter((r) => r.status === "watching").length,
        releasedByCoach: [...tracked.values()].filter((r) => r.status === "released-by-coach").length,
        settledElsewhere: [...tracked.values()].filter((r) => r.status === "settled-elsewhere").length,
      },
      tracked: [...tracked.values()].map((r) => ({
        depositId: r.depositId,
        status: r.status,
        buyerConfirmed: Boolean(r.buyerConfirmed),
        addedAt: r.addedAt,
        firedAt: r.firedAt,
        wouldFireAt: r.wouldFireAt ?? null,
        executionId: r.executionId,
        lastVerdict: r.lastVerdict,
      })),
      log,
    };
  }

  return { track, confirm, start, stop, state, tick };
}
