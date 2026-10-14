# Research Direction & Portfolio — AI Engineering for Reliable Autonomous Systems

*For PhD applications and research-fit interviews. Ties your real systems to a coherent research
identity. Note the CSC Nigeria deadline (~14 Oct 2026) and supervisor-lock timing — this file is
the raw material for the SOP and the first supervisor email.*

---

## The thesis in one sentence

> **Engineering Reliable AI-Native Distributed Systems for Autonomous Financial Transaction
> Processing** — how to let learned, autonomous components make consequential decisions inside
> money-movement systems *without* surrendering the safety, consistency, and auditability that
> regulated finance demands.

Why this framing wins: it sits precisely at the **SE4AI ∩ distributed-systems ∩ fintech**
intersection, it's under-served (most agent research ignores regulated constraints), and it's the
one direction where *your* CV is a genuine moat — Remita-scale payments plus a dozen shipped
agentic/on-chain systems.

---

## Supervisor alignment

- **Zhen Ming (Jack) Jiang (York)** — names AI4SE *and* SE4AI explicitly, plus software performance
  engineering and **automated program analysis & debugging**. Project #3 below is built for this.
- **Transferable to your ranked list** (Edinburgh > Oxford > UCL > Imperial): frame to each
  group's language — LFCS/dependable-systems at Edinburgh, programming-languages/verification at
  Oxford, software-systems at UCL, dependable-systems/verification at Imperial. The *substance*
  travels; retune the vocabulary per group.
- Also live at **TUM SEAI** and **Aarhus (human-centred AI4SE)** if you widen the net.

---

## Research Project #1 — AI-Native Architecture for Autonomous Payment Transaction Routing

**Question.** Can an AI agent select payment routes — across providers, rails, and conditions —
optimising success rate, latency, and cost, *while provably honouring deterministic safety
constraints* (never exceed a mandate, never route to a blocked provider, always settle
idempotently)?

**Why it matters.** Payment routing today is rules-engines and manual tuning; a learning agent
could adapt to shifting provider reliability and network conditions — but only if the adaptivity is
boxed inside hard guarantees. That box is the research contribution.

**Method.** Model routing as sequential decision-making over features — *historical success rates,
latency, cost, provider availability, transaction type, risk, network conditions*. Compare a
learned policy against a rules baseline (**run the null hypothesis first**). The novel part: a
verified constraint layer the policy cannot violate, with an empirical study of the
reliability/adaptivity trade-off.

**Your grounding.** Remita routing experience + Kajota's event-driven payment backend + Kajota
Shield's `checkAndSpend` mandate primitive. You've *built* the constraint layer; the PhD formalises
and evaluates it.

**The gap in the literature.** Agent research optimises for capability; it rarely proves the
safety envelope. Regulated routing forces both — that's the publishable tension.

---

## Research Project #2 — Reliability & Verification of LLM Agents in Mission-Critical Distributed Systems

**Question.** How do you prevent an LLM agent from making an unsafe decision in a financial system,
and how do you *verify* that prevention holds — given you can't formally verify the model itself?

**Why it matters.** The `0.95²⁰ ≈ 36%` reliability collapse is fatal in money movement. The field
needs a principled account of where to place verification, retries, human escalation, and the
model/orchestrator/tool failure boundary.

**Method.** A taxonomy of agent failure modes (hallucinated actions, overconfidence, runaway
loops, state inconsistency across retries). A *hybrid assurance* framework: formal verification of
the deterministic envelope + empirical validation of the model via gold-sets and online eval.
Evaluate on a realistic multi-step financial workflow with injected faults.

**Your grounding.** Witness (multi-agent + human escalation + tamper-evident audit), Mesh (87
adversarial tests on the safety invariants), Shield (spend mandate + kill-switch). These are three
instances of the same pattern — the PhD generalises it.

**The gap.** "Hybrid assurance" — formally verifying the envelope while empirically validating the
core — is under-theorised. You have three working examples already.

---

## Research Project #3 — AI-Assisted Automated Debugging of Distributed Payment Systems ⭐

*The strongest fit for Jiang, and the one that fuses AI4SE with your Remita experience.*

**Question.** Can an LLM agent localise and explain faults in a distributed payment system —
reconstructing a failure from logs, traces, and events across services — more effectively than
existing automated-debugging techniques, and can its explanations be trusted?

**Why it matters.** Distributed payment failures are notoriously hard to debug: partial failures,
out-of-order events, cross-service causality. Automated debugging is a mature SE research area;
LLM agents bring new reasoning power *and* new trust problems. The intersection is wide open.

**Method.** Agent ingests distributed traces + logs + event streams, hypothesises a root cause,
and is evaluated on (a) localisation accuracy against known faults and (b) *faithfulness* of its
explanation — validated against human expert labels, never self-reported. Benchmark against classic
fault-localisation. **Architecture-informed evaluation:** tie the planner to localisation accuracy,
memory to multi-service coherence.

**Your grounding.** Remita production-debugging scars + Kafka/Mongo event-driven backend +
documented real incidents (the fanout index migrations, the non-atomic dedup). You have a *corpus
of real distributed-payment bugs* — that's a dataset most applicants can't offer.

**The gap.** AI4SE debugging work centres on single-codebase bugs; *distributed-systems* debugging
with an agent, evaluated for explanation faithfulness, is barely touched. This is your sharpest
wedge.

---

## Portfolio artefacts you already hold (map, don't rebuild)

| Artefact | Evidences |
|---|---|
| **Kajota Mesh** (97/87 tests, multi-chain, verified contracts) | deterministic safety envelope; adversarial V&V |
| **Kajota Witness** (on-chain anchored verdicts) | multi-agent eval, human-in-the-loop, auditability by construction |
| **Kajota Shield** (`checkAndSpend`) | bounded autonomy; safety invariants in code |
| **Pulse** (bounded retry, measured 60%→90%+) | reliability engineering around an unreliable model |
| **Mobile backend** (Kafka/Mongo, dedup) | idempotency, consistency, event-driven distribution |
| **Remita** | regulated payment distribution at national scale |

**The move (from your own playbook):** don't claim the research matters — *show the shipped system*,
then state the open question it left unanswered. That gap IS the PhD.

---

## Three sentences to have ready for any supervisor email

1. *"My work sits at SE4AI ∩ distributed systems ∩ regulated payments — I build autonomous
   financial systems and I'm interested in how to let learned components make consequential
   decisions without surrendering safety, consistency, and auditability."*
2. *"I've shipped the primitives — a verified spend-mandate layer, a multi-agent dispute system with
   tamper-evident audit, and an event-driven payment backend — and each left a crisp open question I
   want to formalise."*
3. *"Project #3 — AI-assisted automated debugging of distributed payment systems — maps directly onto
   your automated-analysis and debugging work, and I can bring a corpus of real distributed-payment
   failures to it."*
