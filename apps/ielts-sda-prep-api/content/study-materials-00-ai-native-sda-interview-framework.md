# AI-Native System Design Interview — The Framework

*The reusable spine for any "design an AI/agentic system" prompt in 2026. Grounded in current
interview sources (see end) and mapped to systems you've actually shipped.*

---

## The one fact the whole interview turns on

**Step reliability compounds.** If each step of an agent is 95% reliable, a 20-step task
succeeds only `0.95²⁰ ≈ 36%` of the time. An agent that *feels magical in a demo* becomes
unusable in production. **Every strong answer is organised around defeating this number**:
bound the scope, verify each step, retry with limits, and insert a human where the cost of
being wrong is high.

Say this out loud early. It signals you think about agents as *unreliable distributed systems*,
not as a clever prompt.

---

## The control-plane boundary (the second thing to say)

Separate the two cleanly:

- **The orchestrator is deterministic.** It owns control flow, retries, state, budget
  enforcement, and the failure boundary. Plain software.
- **The LLM reasons *within boundaries the orchestrator enforces*.** It plans and decides; it
  does not get to move money, call a tool unchecked, or loop forever.
- **The tool gateway makes tool use secure, reliable, and observable** — schema-validated
  inputs, allowlisted actions, rate limits, and a full audit trail of every call.

> *Your line:* "I keep determinism at the boundaries and trust the model only in between. In my
> Mesh escrow the commission split is Solidity, not model arithmetic; in my Witness system the
> payment gate runs before the agent turn ever starts. The model never touches the invariant."

---

## The 5-step progression (pace yourself to this)

1. **Problem framing (5–10 min).** Users, constraints, quality bar, guardrails, cost ceiling,
   latency budget. *Clarify what "wrong" costs* — that decides where the human sits.
2. **High-level architecture (10–15 min).** Prompt → orchestrator → retrieval/tools → model →
   validation → response. Draw the data path.
3. **Deep dive (20–30 min).** Pick RAG design, tool use, memory, and **evaluation + safety** —
   interviewers steer here.
4. **Trade-offs (10–15 min).** Failure modes, how you *detect* them, graceful degradation.
5. **Conclusion.** One-paragraph risk summary + the next iteration.

---

## The four repeatable patterns

| Pattern | What to cover | Your grounding |
|---|---|---|
| **RAG / grounding** | retrieval, chunking, citations, review | Atlas vector→full-text fallback (same response shape, no client release) |
| **Feedback loops** | implicit/explicit signals, active learning | Witness delivery/opened tracking back through Kafka |
| **Hallucination mitigation** | retrieval grounding, confidence estimation, source transparency | Witness `escalate_to_human` on unparseable output; confidence clamped [0,1] |
| **Scalability & cost** | multi-layer caching, model tiering, prompt compression, quotas | hub $25 vs $49 consolidation; `thinkingBudget:0` to stop token burn |

---

## Evaluation — the part juniors skip and seniors lead with

**Evaluation lives *inside* the workflow, online and offline — not a pre-launch checkbox.**

Separate the two layers and measure them differently:

- **Retrieval:** recall / precision against a set of known-relevant documents.
- **Generation:** *faithfulness* (is the answer grounded in retrieved context?) and *answer
  relevance* — scored by **LLM-as-judge, itself validated against human labels**. An unvalidated
  judge is just a second opinion from the same failure distribution.

**Architecture-informed evaluation:** tie each component to an observable metric — the planner to
task-completion rate, memory to cross-turn coherence, the tool router to tool-selection accuracy.
"What to measure and why" follows from the architecture, not a generic dashboard.

> *Your line:* "I'd build a gold-set of cases, run offline evals on every change, and keep online
> evals sampling live traffic to catch quality drift *before users complain*. In Pulse I measured
> the Gemini fallback rate and watched it move from ~60% to ~90%+ real-model answers after adding
> a bounded retry — that number is the eval."

---

## Failure modes unique to agents (name them, then defend)

- **Hallucinated actions** → schema-validate tool inputs; allowlist; dry-run destructive calls.
- **Overconfident decisions** → calibrated confidence; route above a confidence/dollar threshold
  to a human. *A wrong auto-approval is expensive.*
- **Runaway execution loops** → step budget, loop detection (same action N times → halt),
  wall-clock and token ceilings.
- **State inconsistency across retries/handoffs** → idempotency keys on every side-effect so a
  replay is a no-op.

The classic probe: **"How do you stop an agent looping on the same failed action?"** Answer:
bounded retries with backoff, a loop detector on repeated (action, args), and a hard step cap
that escalates to a human on exhaustion — never an unbounded `while`.

---

## Example prompts to rehearse (from live 2026 loops)

- Design an **insurance-claims agent**: ingest claims → approval decision via RAG, control token
  cost, route anything above a confidence/$ threshold to a human.
- Design a **RAG evaluation + monitoring system** that detects degradation before users complain.
- Design a **multi-step agentic workflow** (meeting scheduling, code review, email campaigns).
- Design a **document Q&A / co-pilot** (GitHub Copilot-style).
- Design **cross-conversation memory** (ChatGPT-style).
- Design a **fraud detection** system.
- Design a **unified query engine** across email, calendar, docs, chat.

Each reduces to the same spine: *bound the scope, ground the model, validate the output, meter
the cost, and put a human at the expensive edge.*

---

## Your unfair advantage — map the prompt to a shipped system

| If they ask about… | You say "I built this" with… |
|---|---|
| Multi-agent reasoning + human escalation | **Witness**: 3 Groq jurors in parallel + judge, `escalate_to_human` default |
| Deterministic boundary around an LLM | **Mesh**: split math in Solidity; payment gate before the agent turn |
| Unreliable, expensive dependency | **Pulse**: bounded retry with a hard 9s deadline + heuristic floor |
| At-least-once + dedup | **Mobile backend**: Redis→Mongo dedup, DB unique constraint as the real guarantee |
| Verifiable audit trail | **Witness**: on-chain `verdictRoot` byte-identical to the stored CID |
| Cost-driven architecture | **hub**: 7 services on one box, $25 vs $49, documented blast radius |

Lead with the shipped system, then generalise. That is the "PR not a meeting" move — you're not
theorising, you're reporting.
