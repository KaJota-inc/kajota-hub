# The 12-Week IELTS × Systems × PhD Programme

*The operational spine. Each week fuses one technical domain with an IELTS skill rotation and a
PhD-interview angle, reusing the concept cards and foundations sheet already in this folder. The
governing method is **one topic, four ways**: system design → IELTS speaking → IELTS writing → PhD
interview. Run the daily loop every day; the Friday SD mock and the Sunday retro are
non-negotiable, exactly as in `PLAN.md`.*

**Target:** IELTS Academic 8.0 overall (L 8.5 / R 8.5 / W 7.5 / S 7.5+). Minimums are far lower
(see `10-english-requirements-and-targets.md`); we train above them because the real exam is the
viva, not the test centre.

---

## The daily loop (≈45–60 min)

1. **Read aloud** one concept card from `01`–`04` (register practice).
2. **Transform** one engineer-sentence into academic English (`08-register-transformation.md`).
3. **Speak** the week's prompt for 2 minutes, recorded, no notes.
4. **Bank** three collocations from `09-technical-vocabulary-bank.md` into a sentence each.
5. One day/week: **write** the week's Task-2 prompt (250–300 words, timed 40 min).

**The register rule, above all:** *technically sophisticated without sounding unnecessarily
complicated.* One idea per sentence; lead with the why; name the mechanism, not the jargon.

---

## Week-by-week

### Weeks 1–2 — IELTS fundamentals + Distributed Systems
- **Cards/refs:** `03` (12–16), foundations §Distributed Systems. Framework file intro.
- **Anchor topic (4 ways):** *Fault tolerance in financial infrastructure.*
- **Speaking:** "Why is fault tolerance important in financial infrastructure?"
- **Writing:** "Discuss the trade-off between availability and consistency in high-volume payment
  systems."
- **PhD angle:** where does your verified constraint layer sit relative to the CAP choice?
- **Grounding:** Kafka backend buffering; Redis-optional dedup; the fanout index-migration incident.

### Week 3 — Microservices + APIs
- **Cards/refs:** `03` (12), foundations §Distributed Systems (EDA, idempotency, DLQ).
- **Anchor:** *Idempotency across service boundaries.*
- **Speaking:** "What are the advantages and disadvantages of microservices architecture?"
- **Writing:** "Microservices increase flexibility but add operational complexity — discuss."
- **PhD angle:** the orchestrator-vs-model boundary IS a service boundary with a trust gradient.
- **Grounding:** hub's 7-services-one-box as the *counter*-example (consolidation for cost).

### Week 4 — Databases + Caching
- **Cards/refs:** `03` (14), foundations §Distributed Systems + §AI Eng (caching).
- **Anchor:** *When the database constraint, not the cache, guarantees correctness.*
- **Speaking:** "When would you choose PostgreSQL over MongoDB?"
- **Writing:** "A caching strategy for a high-throughput financial application — design and defend."
- **PhD angle:** consistency windows for an agent's memory layer.
- **Grounding:** materialised `marked_up_price` (precompute) vs Pulse append-only views.

### Week 5 — Event-Driven Architecture + Kafka
- **Cards/refs:** `03` (12, 15), foundations §Distributed Systems (delivery semantics).
- **Anchor:** *At-least-once + idempotent consumers = effectively-once.*
- **Speaking:** "Explain how Kafka can improve the scalability of a payment processing system."
- **Writing:** "The advantages and limitations of event-driven architecture in high-volume
  financial systems."
- **PhD angle:** event replay as the substrate for Project #3 (distributed-payment debugging).
- **Grounding:** `read_committed` consumer; the RabbitMQ→Kafka migration; non-atomic dedup bug.

### Week 6 — Financial / Payment Architecture
- **Cards/refs:** `04` (20, auditability), foundations §Finance.
- **Anchor:** *Payment System* (the canonical four-ways topic).
- **Speaking:** "How should a payment system respond when a downstream bank becomes unavailable?"
  → problem → alternatives → trade-offs → recommendation.
- **Writing:** "Should financial institutions increasingly automate payment decisions with AI?"
- **PhD angle:** Project #1 — risk-adaptive payment routing under deterministic constraints.
- **Grounding:** Remita routing; dispute-refund idempotent `REFUND_<reportId>`.

### Week 7 — Reliability Engineering + Observability
- **Cards/refs:** `03` (13, 16), `04` (18), foundations §AI Eng (observability).
- **Anchor:** *SLOs and error budgets for an AI-dependent service.*
- **Speaking:** "What is more important for a financial system: availability or consistency?"
  (Force the *"it depends…"* + trade-off structure — this is prime band-8 speaking.)
- **Writing:** "Chaos engineering: deliberately breaking a system to make it reliable — discuss."
- **PhD angle:** Project #2 — hybrid assurance (verify the envelope, validate the model).
- **Grounding:** Witness per-stage timings finding the real bottleneck.

### Week 8 — AI Inference Infrastructure
- **Cards/refs:** `01` (1), foundations §AI + §AI Eng (routing/tiering).
- **Anchor:** *Model tiering = cache tiering for an expensive dependency.*
- **Speaking:** "Why shouldn't every financial decision use the most powerful AI model available?"
  → cost → latency → risk → proportionality.
- **Writing:** "Adaptive inference: matching computational effort to the stakes of a decision."
- **PhD angle:** *intelligence budgets* and verification allocation (Tier-8 thesis vocabulary).
- **Grounding:** Pulse `thinkingBudget:0` to stop token burn; bounded retry with a hard deadline.

### Week 9 — AI Agents + Bounded Autonomy
- **Cards/refs:** `01` (2–6), framework file (the whole spine).
- **Anchor:** *Should an agent execute a financial transaction autonomously? Yes, under
  constraints.* → risk → authorization → decision → verification → execution → audit.
- **Speaking:** the anchor question, 3–4 minutes, no notes.
- **Writing:** "Autonomous agents in finance should act without human intervention — discuss both
  views and give your opinion."
- **PhD angle:** the `0.95²⁰≈36%` reliability collapse as the organising problem.
- **Grounding:** Witness `escalate_to_human`; Shield `checkAndSpend`; Mesh buyer-confirm inversion.

### Week 10 — AI Safety & Verification
- **Cards/refs:** `04` (17, 18, 19), foundations §AI Eng (guardrails).
- **Anchor:** *AI can be probabilistic; financial settlement cannot violate deterministic
  invariants.* (Memorise this sentence — it's your thesis in one line.)
- **Speaking:** "Why might deterministic verification be necessary when AI is used in finance?"
- **Writing:** "Formal guarantees vs empirical confidence in safety-critical AI — discuss."
- **PhD angle:** verifying the deterministic envelope while validating the model empirically.
- **Grounding:** Mesh's 87 adversarial tests; Shield's 7/7 invariant tests.

### Week 11 — Web2 / Web3 Financial Architecture
- **Cards/refs:** `04` (20), foundations §Finance + §AI Eng (security/governance).
- **Anchor:** *Risk at the seam between banking rails and blockchain settlement.*
- **Speaking:** "What additional risks arise when infrastructure spans banks and blockchains?"
- **Writing:** "The convergence of Web2 and Web3 financial security — opportunities and threats."
- **PhD angle:** tamper-evident audit as the bridge (on-chain root = off-chain record).
- **Grounding:** Witness on-chain `verdictRoot` ≡ stored CID; Mesh cross-chain deploys.

### Week 12 — Full Simulation
- **Deliverable:** a recorded 20–30 min mock — IELTS Speaking Parts 1–3 on your domain, then a
  PhD technical interview defending the thesis and Project #3.
- **Scored against:** IELTS band descriptors (fluency, coherence, lexis, grammar, pronunciation)
  *and* research-fit (clarity of contribution, handling of hostile follow-ups).

---

## How to use "one topic, four ways"

Take any anchor topic and run it through all four registers in a single sitting. The payoff is
*compounding*: the system-design pass builds the content, the speaking pass builds fluency, the
writing pass builds structure, and the PhD pass builds the research framing — each reinforcing the
others. One topic mastered four ways beats four topics skimmed once.

> **Worked example — Payment System (Week 6):**
> - *System design:* "Design a payment processing platform." → gateway → risk engine → ledger →
>   settlement, with idempotent retries and a downstream-failure fallback.
> - *Speaking:* "Explain how a payment platform works" — in plain language, for a non-specialist.
> - *Writing:* "Should institutions automate payment decisions with AI?" — both views + opinion.
> - *PhD:* "How would you introduce an autonomous agent into payment infrastructure without
>   compromising settlement correctness?" — separate probabilistic decision from deterministic
>   execution; gate on risk and consequence.

---

## Timeline it serves (parallel, not sequential)

- **Oct 2026** — thesis proposal draft + supervisor shortlist (overlaps CSC ~14 Oct deadline).
- **Nov** — supervisor outreach + programme Weeks 1–5 + IELTS baseline mock.
- **Dec** — first full IELTS mock + proposal refinement + Weeks 6–9.
- **Jan** — funding/scholarship materials + Weeks 10–12.
- **Feb 2027** — UCL cycle-1 target (12 Feb). **Mar–Apr** — Imperial / York / UCL cycle-2 + interviews.

IELTS prep must not stall the proposal; they run on one track because the technical world you
already inhabit *is* the English classroom.
