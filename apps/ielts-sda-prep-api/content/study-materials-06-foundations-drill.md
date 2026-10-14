# Foundations Drill — Rapid-Recall Sheet

*One crisp line per concept + the "say-this" angle + a Kajota hook where you have one. Drill these
until each is a reflex. Format: **Term** — definition // *say-this* // ⚓ your grounding.*

---

## Distributed Systems

- **CAP theorem** — under a network partition, choose consistency or availability, not both. //
  *"The real question is which inconsistencies I can tolerate and for how long."* ⚓ Redis-optional
  dedup chose availability; Mongo + unique index is the consistency backstop.
- **Consensus** — getting distributed nodes to agree on one value despite failures (Raft/Paxos). //
  *"Expensive; I avoid needing it where an idempotency key will do."*
- **Replication** — copies of data across nodes for availability + read scale; sync vs async trades
  consistency for latency.
- **Partition tolerance** — the system keeps working when the network splits; non-negotiable in
  practice, so CAP is really a C-vs-A choice.
- **Distributed transactions** — atomicity across services; 2PC is blocking and fragile. //
  *"I prefer sagas + idempotency + an outbox over 2PC."*
- **Event-driven architecture** — services communicate via events on a log; decouples producers
  from consumers. ⚓ Kafka backend: payment emits, returns; consumer failure buffers.
- **Eventual consistency** — replicas converge given time; fine for read-mostly, dangerous for
  read-after-write dependencies.
- **Exactly-once vs at-least-once** — exactly-once delivery is largely a fiction across independent
  systems; you get at-least-once + idempotent processing = *effectively* once. ⚓ `read_committed`
  Kafka consumer + unique-index dedup.
- **Idempotency** — repeat = same effect as once; the foundation of safe retries. ⚓ `processed_event`
  key; the DB unique constraint is the real guarantee, not the `if`.
- **Distributed locking** — mutual exclusion across nodes (e.g. Redlock); prefer a DB constraint
  where possible. // *"Push the invariant into the database, don't race it in app code."*
- **Failure detection** — heartbeats/timeouts to decide a node is down; the catch is you can't
  distinguish 'slow' from 'dead'. // *"Timeouts are a guess; design for being wrong about them."*

---

## AI / ML

- **Neural networks** — layered function approximators learning weights by gradient descent.
- **Transformers** — attention-based architecture; processes sequences in parallel, captures
  long-range dependencies. The backbone of modern LLMs.
- **Embeddings** — dense vectors placing semantically similar items near each other; the substrate
  of retrieval. ⚓ Witness runs MiniLM in-process, 384-dim, cosine top-K.
- **Attention** — each token weighs the relevance of every other; "what should I look at?" made
  differentiable.
- **RAG** — retrieve relevant documents, ground the generation in them; reduces hallucination,
  adds freshness. // *"Separate retrieval (recall/precision) from generation (faithfulness)."*
  ⚓ Atlas vector→full-text fallback.
- **LLMs** — large autoregressive models predicting the next token; capable but non-deterministic
  and confidently wrong.
- **Fine-tuning** — adapting a pretrained model on task data; vs prompting/RAG, a cost/control
  trade-off. // *"I reach for RAG and prompting before fine-tuning — cheaper, more controllable."*
- **Evaluation** — offline gold-sets + online sampling; LLM-as-judge validated against human labels.
  ⚓ Pulse fallback rate 60%→90%+ was the metric.
- **Hallucination** — fluent, confident, ungrounded output; mitigate with retrieval grounding +
  confidence + source transparency. ⚓ Witness `escalate_to_human` on unparseable output.
- **Agents** — goal-driven perceive–plan–act loops with tools; reliability compounds badly
  (`0.95²⁰≈36%`).
- **Tool calling** — structured function invocation from the model; validate inputs, allowlist,
  audit.
- **Planning** — decomposing a goal into steps; the planner is a distinct component to evaluate
  (task-completion rate).
- **Memory** — short-term (context/scratchpad) vs long-term (vector store); evaluate for cross-turn
  coherence.
- **Multi-agent systems** — specialised agents collaborating/debating; more capability, more
  coordination failure. ⚓ Witness: 3 jurors + a judge.

---

## AI Engineering

- **AI system architecture** — orchestrator (deterministic) + model (reasoning) + tools + memory +
  eval + guardrails. // *"Determinism at the boundaries, trust the model only in between."*
- **Agent orchestration** — the control plane owning flow, state, retries, budget; LLM acts within
  its limits.
- **Evaluation frameworks** — gold-sets, metamorphic tests, LLM-as-judge, online eval; eval lives
  *inside* the workflow.
- **Observability** — logs/metrics/traces; for agents, the full decision trail tied to a request
  ID. ⚓ Witness per-stage timings found the real bottleneck.
- **Guardrails** — input/output validation, content filters, schema enforcement, thresholds; the
  deterministic safety layer.
- **Model routing / tiering** — cheap model for easy cases, expensive for hard; a cost lever. //
  *"Tier the model the way you'd tier a cache."*
- **AI testing** — behavioural + adversarial + invariant tests; invariants hold regardless of
  output. ⚓ Mesh 87 adversarial tests.
- **Reliability engineering** — retries, timeouts, circuit breakers, graceful degradation applied
  to an expensive, unpredictable dependency.
- **AI security** — prompt injection, data exfiltration via tools, jailbreaks; treat model output
  and tool results as untrusted.
- **AI governance** — policy, accountability, audit, compliance for autonomous decisions. ⚓ Witness
  on-chain tamper-evident audit; your fintech/regulated angle is the differentiator.

---

## The three reflexes to never lose under pressure

1. **"Each step 95% → 20 steps ≈ 36%."** Agents fail by compounding; bound, verify, escalate.
2. **"The DB constraint makes it correct; the cache/model just makes it fast."** Push invariants
   down to where they can't be raced.
3. **"The model is the easy part."** Production AI = distributed-systems engineering around an
   expensive, unpredictable dependency. That sentence *is* your positioning.
