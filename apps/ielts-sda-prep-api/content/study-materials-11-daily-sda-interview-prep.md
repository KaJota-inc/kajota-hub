# Daily SDA Interview Prep — AI-Native Engineering (60-Day Driver)

*One concrete AI-native system-design prompt per weekday, sequenced from fundamentals to a full
viva-grade capstone. This is the **drill engine** — the weekly domain content lives in
`07-twelve-week-programme.md` and `12-domain-curriculum.md`; this file tells you exactly what to
whiteboard each day and how to score it. Log every session in `13-progress-tracker.md`.*

**The spine (say it on every prompt):** reliability compounds — `0.95²⁰ ≈ 36%`; keep determinism
at the boundary and trust the model only within it; bound the scope, ground the model, validate the
output, meter the cost, put a human at the expensive edge.

---

## How a day runs (45–90 min)

| Phase | Min | What you do |
|---|---|---|
| **Frame** | 5 | Restate the prompt; clarify users, scale, quality bar, cost ceiling, "what does *wrong* cost?" |
| **HLD** | 10 | Draw the data path: request → orchestrator → retrieval/tools → model → validation → response |
| **Deep dive** | 20 | The day's named focus — go deep on *one* thing, not shallow on five |
| **Trade-offs** | 10 | Failure modes, how you *detect* them, graceful degradation |
| **Score + speak** | 10 | Self-score /5 (rubric below); then summarise aloud for 2 min in band-8 register |

**SD self-score rubric (1–5):**
1 — couldn't structure it · 2 — structure but missed core components · 3 — solid HLD, shallow
deep-dive · 4 — strong deep-dive + named trade-offs, minor gaps · **5 — complete, named failure
modes, grounded in a real system, crisp.**
**Mastery bar:** score 4+ on a prompt twice → mastered. Score ≤2 → flag `REDO` in the tracker.

**Fridays are timed mocks** (60 min, recorded, no notes). **Sundays are retro** (re-attempt one
flagged prompt + read one engineering blog/paper).

---

## WEEK 1 — Foundations through the AI-native lens

**D1 — "Design a system that answers questions over a company's internal documents."**
Focus: what makes it *AI-native* vs a search feature. Must hit: RAG data path, grounding,
citations, the model as a probabilistic dependency. Grounding: Atlas vector→full-text fallback.
Trap: don't let it become plain keyword search — defend why retrieval + generation.

**D2 — "Your LLM feature 500s whenever the model provider is slow or over quota. Fix it."**
Focus: treating the model as an unreliable dependency. Must hit: timeout, bounded retry +
backoff, deterministic fallback, graceful degradation. Grounding: Pulse bounded retry (60%→90%+).
Trap: naming "retry" without a cap or jitter → retry storm.

**D3 — "Design request-level cost control for an LLM product at 6k req/s peak."**
Focus: cost as a first-class constraint. Must hit: caching, model tiering, prompt compression,
per-user quotas, token budgeting. Grounding: Pulse `thinkingBudget:0`; hub $25-vs-$49.
Trap: optimising the model before measuring where the tokens actually go.

**D4 — "Design dedup for an at-least-once event stream feeding an AI pipeline."**
Focus: idempotency. Must hit: idempotency key, Redis L1 → DB L2, the DB *unique constraint* as
the real guarantee, atomic check-and-write. Grounding: `processed_event` + sparse unique index.
Trap: a check-then-write race; say why the constraint, not the `if`, saves you.

**D5 — MOCK: "Design a document Q&A copilot (GitHub-Copilot-style) end to end."**
Timed 60 min. Combine D1–D4: RAG + unreliable-dependency handling + cost + idempotent ingestion.
Score against the full rubric; record yourself.

---

## WEEK 2 — Inference & serving infrastructure

**D6 — "Design a model-serving layer for millions of users with versioning and result caching."**
Focus: serving topology. Must hit: batching, GPU utilisation, model versioning, result cache,
autoscaling. Trap: ignoring cold starts and cache invalidation.

**D7 — "Design a model router that sends easy requests to a cheap model, hard ones to an expensive
one."** Focus: model tiering / cascades. Must hit: a routing signal (confidence/complexity),
fallback on low confidence, cost/latency trade-off. Trap: routing on nothing measurable.

**D8 — "Cut p95 latency of an LLM endpoint by 40% without changing the model."**
Focus: latency engineering. Must hit: streaming, caching, speculative/parallel calls, prompt
trimming — *after* instrumenting. Grounding: Witness per-stage timings found the real bottleneck.
Trap: optimising inference when the bottleneck is retrieval or I/O.

**D9 — "Design KV-cache / batching strategy for a high-throughput inference service."**
Focus: throughput mechanics. Must hit: continuous batching, KV-cache reuse, the
latency-vs-throughput trade-off. Trap: treating throughput and latency as the same lever.

**D10 — MOCK: "Design the inference platform behind a consumer AI product (routing + serving +
cost + latency)."** Timed. Combine D6–D9.

---

## WEEK 3 — RAG systems

**D11 — "Design the retrieval layer: chunking, embeddings, index choice."**
Focus: retrieval quality. Must hit: chunking strategy, embedding model, ANN index, metadata
filters. Grounding: Witness in-process MiniLM, 384-dim. Trap: one-size chunk size.

**D12 — "How do you evaluate a RAG system before users complain?"**
Focus: RAG evaluation. Must hit: separate retrieval (recall/precision vs known-relevant) from
generation (faithfulness, answer relevance), LLM-as-judge *validated against human labels*, online
sampling. Trap: a single end-to-end accuracy number.

**D13 — "Your RAG answers are fluent but subtly wrong. Diagnose and fix."**
Focus: hallucination mitigation. Must hit: grounding checks, faithfulness scoring, source
attribution, "I don't know" as a valid answer. Grounding: Witness `escalate_to_human`.
Trap: blaming the model when retrieval is the culprit.

**D14 — "Design freshness: the corpus updates hourly; stale answers are unacceptable."**
Focus: index freshness vs cost. Must hit: incremental indexing, invalidation, consistency window.
Trap: full re-index every change (cf. Witness's O(n) rewrite — name it as the anti-pattern).

**D15 — MOCK: "Design a Perplexity-style real-time answer engine with citations and eval."**
Timed. Combine D11–D14.

---

## WEEK 4 — Agents I: single-agent loops, tools, memory

**D16 — "Design a single agent that books meetings across tools (calendar, email, contacts)."**
Focus: the perceive–plan–act loop. Must hit: orchestrator vs model split, tool gateway, step cap.
Trap: an unbounded `while` loop with no budget.

**D17 — "Design the tool gateway: make tool use secure, reliable, observable."**
Focus: the gateway. Must hit: schema-validated inputs, allowlist, rate limits, dry-run for
destructive calls, full audit of every call. Grounding: Mesh split-math in code, not model.
Trap: letting the model call tools unchecked.

**D18 — "How do you stop an agent looping on the same failed action?"**
Focus: runaway-loop defence. Must hit: bounded retries + backoff, loop detector on repeated
(action, args), hard step/wall-clock/token ceilings, escalate on exhaustion. Trap: "just retry."

**D19 — "Design agent memory: short-term scratchpad + long-term store."**
Focus: memory architecture. Must hit: context-window management, vector long-term memory,
read-after-write where the next step depends on it, eviction. Grounding: Coach session memory +
30-min TTL. Trap: unbounded context growth.

**D20 — MOCK: "Design an autonomous email-campaign agent with tools, memory, and loop safety."**
Timed. Combine D16–D19.

---

## WEEK 5 — Agents II: multi-agent, orchestration, long-horizon reliability

**D21 — "A 20-step agent task succeeds ~36% of the time. Make it production-reliable."**
Focus: the compounding-reliability problem. Must hit: bounded scope, per-step verification,
checkpoints, human escalation. Trap: not quoting the maths.

**D22 — "Design a multi-agent system where specialised agents collaborate/debate."**
Focus: orchestration vs choreography, handoffs. Must hit: coordination failure modes, state
consistency across handoffs. Grounding: Witness 3 jurors + judge. Trap: more agents = more
coordination failure; justify the count.

**D23 — "Reason about state consistency across agent retries and handoffs."**
Focus: distributed state for agents. Must hit: idempotency keys on every side-effect, saga-style
compensation, where the failure boundary sits. Trap: assuming a retry is free.

**D24 — "Where should the failure boundary sit — model, orchestrator, or tool layer?"**
Focus: failure-boundary design. Must hit: deterministic orchestrator owns control/retries/budget;
model reasons within limits; tools validate. Trap: trusting the model with control flow.

**D25 — MOCK: "Design a multi-step code-review agent (plan → analyse → comment → verify)."**
Timed. Combine D21–D24.

---

## WEEK 6 — Evaluation & observability for AI

**D26 — "Design offline + online evaluation for a production AI feature."**
Focus: evaluation that lives *inside* the workflow. Must hit: gold-sets, online sampling,
architecture-informed metrics (planner→completion, memory→coherence, router→tool-accuracy).
Grounding: Pulse fallback-rate as the metric. Trap: eval as a pre-launch checkbox.

**D27 — "Design observability for an autonomous agent."**
Focus: the three pillars for agents. Must hit: full decision trace tied to a request ID, cost/token
telemetry, drift detection. Grounding: Witness per-stage timings. Trap: scattered logs that can't
reconstruct a multi-step decision.

**D28 — "Detect quality drift in a live LLM product before users notice."**
Focus: drift detection. Must hit: online eval sampling, canary gold-sets, alert thresholds.
Trap: waiting for user complaints as the signal.

**D29 — "Design an LLM-as-judge pipeline you can actually trust."**
Focus: judge validation. Must hit: validate the judge against human labels, re-calibrate on
disagreement, never let it grade its own distribution. Trap: trusting an unvalidated judge.

**D30 — MOCK: "Design the eval + monitoring system for a RAG product (detect degradation early)."**
Timed. Combine D26–D29.

---

## WEEK 7 — Guardrails, safety, verification

**D31 — "Design the guardrail layer around an LLM that can take actions."**
Focus: the deterministic safety envelope. Must hit: input/output validation, content filters,
schema enforcement, confidence/$ thresholds. Grounding: Shield `checkAndSpend`. Trap: guardrails
in the prompt instead of in code.

**D32 — "AI is probabilistic; settlement cannot violate invariants. Reconcile them."**
Focus: separating probabilistic decision from deterministic execution. Must hit: propose →
verify-against-invariants → execute; verification proportional to risk. Grounding: Mesh split in
Solidity. Trap: letting the model mutate the ledger.

**D33 — "You can't formally verify an LLM. How do you assure the system?"**
Focus: hybrid assurance. Must hit: formally verify the envelope + invariants, validate the model
empirically. Grounding: Mesh 87 adversarial tests; Shield 7/7. Trap: claiming to verify the model.

**D34 — "Design a kill-switch and spend-mandate for an autonomous financial agent."**
Focus: bounded autonomy. Must hit: per-agent mandate, latching kill-switch, fail-safe default.
Grounding: Shield. Trap: a kill-switch the agent can talk its way past.

**D35 — MOCK: "Design an insurance-claims agent: RAG decision, cost control, human fallback above
threshold."** Timed. The canonical 2026 prompt. Combine D31–D34.

---

## WEEK 8 — AI-native financial systems

**D36 — "Design an AI payment-router choosing routes on success rate, latency, cost, risk."**
Focus: your Project #1. Must hit: features, learned policy vs rules baseline, a verified
constraint layer the policy can't violate. Grounding: Remita + Shield. Trap: optimising capability
without the safety envelope.

**D37 — "A downstream bank goes unavailable mid-payment. What does the system do?"**
Focus: failure handling in money movement. Must hit: idempotent retry, fallback route, fail-safe
not fail-operational, reconciliation. Trap: double-charging on retry.

**D38 — "Design real-time fraud detection with an AI model in the loop."**
Focus: AI + hard rules. Must hit: model scores, deterministic rule gate, human review queue,
false-positive cost. Trap: a black-box auto-block with no appeal.

**D39 — "Design idempotent refunds triggered by an AI dispute-resolution decision."**
Focus: idempotency + human-in-loop in finance. Must hit: idempotency key, approval gate, audit.
Grounding: dispute-refund `REFUND_<reportId>`; Witness escalation. Trap: non-idempotent credit.

**D40 — MOCK: "Introduce an autonomous agent into payment infrastructure without compromising
settlement correctness."** Timed. The PhD-grade prompt. Combine D36–D39.

---

## WEEK 9 — Distributed-systems backbone under AI load

**D41 — "Design the event backbone feeding async AI workloads (Kafka topics, consumers)."**
Focus: EDA for AI. Must hit: partitioning by key, consumer groups, delivery semantics, DLQ.
Grounding: `read_committed` consumer; RabbitMQ→Kafka migration. Trap: ordering assumptions.

**D42 — "Choose consistency for an agent's shared state across replicas."**
Focus: consistency spectrum. Must hit: strong vs eventual, read-after-write where the next action
depends, consistency window. Grounding: Redis-optional dedup (availability over cache consistency).
Trap: eventual consistency for a decision input.

**D43 — "Design backpressure when the AI layer is slower than ingestion."**
Focus: backpressure + queueing. Must hit: bounded queues, load shedding, the queue as a buffer not
a swamp. Trap: unbounded queue growth → memory blow-up.

**D44 — "Make a fleet of agents fault-tolerant on one constrained host."**
Focus: resource contention + isolation. Must hit: per-process limits, health checks, blast-radius
containment. Grounding: hub 7-services-one-box (and its one-health-check gap). Trap: one dead
process silently taking the box.

**D45 — MOCK: "Design a scalable async pipeline: ingest → AI enrichment → durable store →
notify."** Timed. Combine D41–D44.

---

## WEEK 10 — Security for agentic systems

**D46 — "An agent has access to financial APIs. Enumerate and mitigate the security risks."**
Focus: agentic attack surface. Must hit: authn vs authz, least privilege, prompt injection via
tool outputs, secrets handling, audit. Trap: treating tool output as trusted.

**D47 — "Defend an agent against prompt injection from retrieved/third-party content."**
Focus: injection defence. Must hit: treat all external text as untrusted, input sanitisation,
privilege separation, output validation. Trap: assuming your own corpus is safe.

**D48 — "Design authorization + identity for autonomous agents acting on a user's behalf."**
Focus: delegated authority. Must hit: scoped tokens, per-action authz, bounded mandate, revocation.
Grounding: Shield mandate; Mesh three-key separation. Trap: a single over-privileged agent key.

**D49 — "Design a tamper-evident audit trail for autonomous agent decisions."**
Focus: auditability. Must hit: immutable record, provenance, non-repudiation, who-did-what-when.
Grounding: Witness on-chain `verdictRoot` ≡ stored CID. Trap: mutable logs the actor can rewrite.

**D50 — MOCK: "Security-review an agent that moves money: authz, injection, secrets, audit."**
Timed. Combine D46–D49.

---

## WEEK 11 — Web2 × Web3 AI-native settlement

**D51 — "Design settlement that spans a bank rail and a blockchain. Where's the risk?"**
Focus: the seam. Must hit: finality mismatch, reconciliation across rails, idempotency across
chains. Grounding: Mesh cross-chain deploys. Trap: assuming on-chain finality == bank settlement.

**D52 — "Design on-chain authorization for an agent's spend (mandate enforced by contract)."**
Focus: contract-enforced autonomy. Must hit: on-chain mandate, rate-limited operator path, dispute
freeze. Grounding: Mesh buyer-confirm inversion; Shield. Trap: trusting an off-chain cron for a
guarantee that must be on-chain.

**D53 — "Design an on-chain + off-chain split: what goes where, and why?"**
Focus: the split decision. Must hit: invariants/money on-chain, data/evidence off-chain with a
hash pointer, cost. Grounding: Witness/Mesh "on-chain mirror" pattern. Trap: putting everything
on-chain.

**D54 — "Design a verifiable AI-verdict anchor (anyone can check without trusting your server)."**
Focus: trustless verification. Must hit: content-addressed storage, on-chain root ≡ CID, public
`/verify`. Grounding: Witness. Trap: an audit trail only you can read.

**D55 — MOCK: "Design an AI-native escrow: agent decides, contract enforces, anchor proves."**
Timed. Combine D51–D54.

---

## WEEK 12 — Capstone (viva-grade)

**D56 — "Whiteboard your thesis system end to end: risk-adaptive autonomous payment processing."**
Full design + defend every boundary. This is Project #1 + #2 fused.

**D57 — "Defend: why not just use rules? why not full autonomy? why hybrid assurance?"**
Pure trade-off defence; expect hostile follow-ups.

**D58 — "Design AI-assisted debugging of a distributed payment system."**
Project #3. Must hit: ingest traces/logs/events, localise root cause, faithfulness of the
explanation validated against experts. Grounding: Remita incidents + Kafka/Mongo backend.

**D59 — "Teach the compounding-reliability problem to a non-specialist in 3 minutes."**
Register + explainability drill; band-8 plain-language delivery.

**D60 — FINAL MOCK: 30-min panel simulation.** IELTS Speaking Parts 1–3 on your domain, then a PhD
technical defence of the thesis and Project #3. Score against band descriptors *and* research-fit.

---

## After D60

Re-run every prompt flagged `REDO`. Then cycle the MOCK days (D5, D10, …, D60) cold, monthly, to
keep the designs warm for live loops. Promote the three strongest into your portfolio talk-track:
Mesh escrow inversion, Redis-optional dedup, Witness latency instrumentation.
