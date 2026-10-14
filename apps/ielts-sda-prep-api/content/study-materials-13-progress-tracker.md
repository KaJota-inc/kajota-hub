# Progress Tracker — Daily SDA (AI-Native Engineering)

*Fill one row per session. Pairs with `11-daily-sda-interview-prep.md`. The point of the tracker is
honesty: a self-score you fudge is a viva you fail. Score cold, before you look at the grounding
hook.*

---

## How to score (calibrate every time)

**SD /5** — 1 couldn't structure · 2 missed core components · 3 solid HLD, shallow deep-dive ·
4 strong deep-dive + named trade-offs · **5 complete + named failure modes + grounded + crisp.**

**Register band** (how you *sounded* summarising aloud) — rough IELTS Speaking self-estimate:
6.0 hesitant/jargon-dense · 6.5 clear but simple · 7.0 fluent, some range · 7.5 precise lexis +
varied grammar · 8.0 effortless, *sophisticated yet plain*. Target ≥7.5.

**Redo?** — mark `REDO` if SD ≤2 OR you leaned on notes. **Mastered** a prompt = SD 4+ on two
separate attempts.

**Daily minimum to count the day:** Frame→HLD→Deep-dive→Trade-offs→Score + a 2-min spoken summary.
No spoken summary = the day doesn't count (register is half the goal).

---

## Streak & headline (update at each session)

- **Current streak:** 0 days
- **Longest streak:** 0 days
- **Days logged:** 0 / 60
- **Prompts mastered (4+ twice):** 0 / 48 build-prompts
- **Open REDOs:** —
- **Next mock:** D5

---

## Week 1 — Foundations through the AI-native lens

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note (what broke / what clicked) |
|----|------|----------------|-----|-------|------|-------|-------------------------------------------|
| D1 |      | Internal-docs Q&A (AI-native vs search) |  |  |  |  |  |
| D2 |      | LLM 500s on slow provider — fix |  |  |  |  |  |
| D3 |      | Request-level cost control @6k rps |  |  |  |  |  |
| D4 |      | Dedup an at-least-once stream |  |  |  |  |  |
| D5 |      | 🔴 MOCK: Doc-Q&A copilot end-to-end |  |  |  |  |  |

## Week 2 — Inference & serving infrastructure

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D6 |      | Model-serving layer + versioning + cache |  |  |  |  |  |
| D7 |      | Model router (cheap vs expensive) |  |  |  |  |  |
| D8 |      | Cut p95 latency 40%, same model |  |  |  |  |  |
| D9 |      | KV-cache / batching for throughput |  |  |  |  |  |
| D10|      | 🔴 MOCK: Inference platform |  |  |  |  |  |

## Week 3 — RAG systems

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D11|      | Retrieval layer: chunking/embeds/index |  |  |  |  |  |
| D12|      | Evaluate RAG before users complain |  |  |  |  |  |
| D13|      | Fluent-but-wrong answers — diagnose |  |  |  |  |  |
| D14|      | Index freshness vs cost |  |  |  |  |  |
| D15|      | 🔴 MOCK: Real-time answer engine + citations |  |  |  |  |  |

## Week 4 — Agents I: loops, tools, memory

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D16|      | Single meeting-booking agent |  |  |  |  |  |
| D17|      | Tool gateway: secure/reliable/observable |  |  |  |  |  |
| D18|      | Stop an agent looping |  |  |  |  |  |
| D19|      | Agent memory: short + long term |  |  |  |  |  |
| D20|      | 🔴 MOCK: Email-campaign agent |  |  |  |  |  |

## Week 5 — Agents II: multi-agent & long-horizon

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D21|      | 20-step task @36% → production-reliable |  |  |  |  |  |
| D22|      | Multi-agent collaborate/debate |  |  |  |  |  |
| D23|      | State consistency across retries/handoffs |  |  |  |  |  |
| D24|      | Where does the failure boundary sit? |  |  |  |  |  |
| D25|      | 🔴 MOCK: Code-review agent |  |  |  |  |  |

## Week 6 — Evaluation & observability

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D26|      | Offline + online evaluation |  |  |  |  |  |
| D27|      | Observability for an autonomous agent |  |  |  |  |  |
| D28|      | Detect quality drift early |  |  |  |  |  |
| D29|      | Trustworthy LLM-as-judge pipeline |  |  |  |  |  |
| D30|      | 🔴 MOCK: RAG eval + monitoring system |  |  |  |  |  |

## Week 7 — Guardrails, safety, verification

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D31|      | Guardrail layer around an acting LLM |  |  |  |  |  |
| D32|      | Probabilistic AI vs invariant settlement |  |  |  |  |  |
| D33|      | Assure a system you can't verify |  |  |  |  |  |
| D34|      | Kill-switch + spend-mandate |  |  |  |  |  |
| D35|      | 🔴 MOCK: Insurance-claims agent |  |  |  |  |  |

## Week 8 — AI-native financial systems

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D36|      | AI payment-router (Project #1) |  |  |  |  |  |
| D37|      | Downstream bank unavailable mid-payment |  |  |  |  |  |
| D38|      | Real-time fraud detection + rules gate |  |  |  |  |  |
| D39|      | Idempotent AI-triggered refunds |  |  |  |  |  |
| D40|      | 🔴 MOCK: Agent in payment infra, safely |  |  |  |  |  |

## Week 9 — Distributed backbone under AI load

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D41|      | Event backbone for async AI |  |  |  |  |  |
| D42|      | Consistency for shared agent state |  |  |  |  |  |
| D43|      | Backpressure when AI < ingestion |  |  |  |  |  |
| D44|      | Fault-tolerant agent fleet, one host |  |  |  |  |  |
| D45|      | 🔴 MOCK: Async ingest→enrich→store→notify |  |  |  |  |  |

## Week 10 — Security for agentic systems

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D46|      | Agent + financial APIs: risks |  |  |  |  |  |
| D47|      | Defend against prompt injection |  |  |  |  |  |
| D48|      | Authz + identity for agents |  |  |  |  |  |
| D49|      | Tamper-evident agent audit trail |  |  |  |  |  |
| D50|      | 🔴 MOCK: Security-review a money-moving agent |  |  |  |  |  |

## Week 11 — Web2 × Web3 settlement

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D51|      | Settlement across bank + chain |  |  |  |  |  |
| D52|      | On-chain authorization for agent spend |  |  |  |  |  |
| D53|      | On-chain vs off-chain split |  |  |  |  |  |
| D54|      | Verifiable AI-verdict anchor |  |  |  |  |  |
| D55|      | 🔴 MOCK: AI-native escrow |  |  |  |  |  |

## Week 12 — Capstone (viva-grade)

| Day | Date | Prompt (short) | Min | SD /5 | Band | Redo? | One-line note |
|----|------|----------------|-----|-------|------|-------|---------------|
| D56|      | Whiteboard the thesis system |  |  |  |  |  |
| D57|      | Defend: rules? autonomy? hybrid assurance? |  |  |  |  |  |
| D58|      | AI-assisted distributed debugging (Proj #3) |  |  |  |  |  |
| D59|      | Teach compounding-reliability in 3 min |  |  |  |  |  |
| D60|      | 🔴 FINAL MOCK: 30-min panel |  |  |  |  |  |

---

## Weekly retro (fill each Sunday)

| Wk | Avg SD /5 | Avg band | REDOs cleared | Weakest area | One change for next week |
|----|-----------|----------|---------------|--------------|--------------------------|
| 1  |  |  |  |  |  |
| 2  |  |  |  |  |  |
| 3  |  |  |  |  |  |
| 4  |  |  |  |  |  |
| 5  |  |  |  |  |  |
| 6  |  |  |  |  |  |
| 7  |  |  |  |  |  |
| 8  |  |  |  |  |  |
| 9  |  |  |  |  |  |
| 10 |  |  |  |  |  |
| 11 |  |  |  |  |  |
| 12 |  |  |  |  |  |

---

## Rules that keep the tracker honest

1. **Score before you peek** at the grounding hook — otherwise you're grading hindsight.
2. **A day without a spoken summary doesn't count.** Register is half the exam.
3. **Three sub-3 scores in one week** → that domain becomes next Sunday's retro re-attempt.
4. **Never advance past a MOCK scoring ≤3** — re-run it before the next week. A shaky mock means the
   week didn't land.
5. **Convert the score to the real unit:** "4/5" means nothing; the note column — *what broke* —
   is where the learning lives. Fill it every time.
