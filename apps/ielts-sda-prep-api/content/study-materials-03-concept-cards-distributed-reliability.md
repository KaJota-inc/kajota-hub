# Concept Cards C — Distributed Systems & Reliability

*These are your home turf — Remita + Kajota's Kafka/Mongo backend. In an AI-native interview the
winning move is to show that agent reliability is *the same discipline* applied to an expensive,
unpredictable dependency. Each card closes that loop.*

---

### 12. Distributed systems

**Definition.** Systems whose components run on separate machines, coordinating over an unreliable
network to appear as one — trading simplicity for scale, availability, and fault tolerance.

**Lexis:** *to coordinate over an unreliable network*, *partial failure*, *horizontal scale*, *the
CAP trade-off*, *event-driven architecture*, *loose coupling*, *a single logical system*.

**Model answer.** "A distributed system is really a study in *partial failure* — any node, or the
network between nodes, can fail independently, and the whole art is behaving sensibly when it does.
That's the mental shift from a monolith: you stop assuming calls succeed and start designing for the
times they don't. The classic trade-off is CAP — under a network partition you must choose between
consistency and availability — but I find the day-to-day reality is subtler, about *which*
inconsistencies you can tolerate and for how long. My default is loose coupling through
event-driven architecture, because a queue between services means one component's failure buffers
rather than cascades."

**Grounded in your work.** "My Kajota backend is event-driven over Kafka precisely for this — the
payment service emits an event and returns; if the notification consumer is down, messages buffer
in the log rather than failing the payment. The queue *is* the fault-tolerance."

**Be ready for:** *"How does this connect to agents?"* → An agent calling flaky tools over a
network IS a distributed system; the same partial-failure thinking applies to tool calls.

---

### 13. Fault tolerance

**Definition.** A system's ability to keep functioning — possibly degraded — despite component
failures, through redundancy, retries, timeouts, circuit breakers, and graceful degradation.

**Lexis:** *graceful degradation*, *redundancy*, *to contain a failure*, *circuit breaker*, *a
fallback path*, *blast radius*, *to fail soft rather than hard*.

**Model answer.** "Fault tolerance is the discipline of failing *soft* rather than hard. The goal
isn't to prevent failure — that's impossible — but to contain it so a single component going down
degrades the experience rather than collapsing the system. The techniques are well-worn: retries
with backoff for transient faults, timeouts so you don't hang on a dead dependency, circuit
breakers to stop hammering something that's clearly down, and above all a *fallback path* that
delivers a worse-but-working answer. I think about blast radius constantly — when this fails, what
else does it take with it? — and I try to make that radius as small as the design allows."

**Grounded in your work.** "My image search degrades beautifully — when the embeddings provider hit
quota and the vector query failed, I caught it and re-ran the keywords through full-text search,
keeping the *same response shape* so the client never knew. A worse answer beats a five-hundred."

**Be ready for:** *"Retries can make things worse — when?"* → Under load (retry storms) and on
non-idempotent operations; cap attempts, add jitter, and only retry what's safe to repeat.

---

### 14. Consistency

**Definition.** The guarantee about *when* and *whether* all parts of a distributed system see the
same data — ranging from strong (everyone sees the latest write immediately) to eventual (they
converge given time).

**Lexis:** *strong vs eventual consistency*, *to converge*, *a read-after-write guarantee*, *a
consistency window*, *monotonic reads*, *to tolerate staleness*, *tunable consistency*.

**Model answer.** "Consistency is one of those words that hides a spectrum. At one end, strong
consistency means every reader sees the latest write the instant it lands — clean to reason about,
but costly and fragile under partition. At the other, eventual consistency accepts a window of
staleness in exchange for availability and speed. The engineering judgment is matching the
guarantee to the *cost of being stale* for that particular data. A user's account balance may
demand strong consistency; a 'trending products' widget can happily be seconds behind. I try to be
explicit about the consistency window rather than letting it be an accident of the infrastructure."

**Grounded in your work.** "In my notification backend I chose availability over cache consistency
deliberately — the Redis dedup cache is allowed to be stale or even down, because Mongo is the
source of truth and a database *unique constraint* is what actually guarantees correctness. The
cache just makes it fast."

**Be ready for:** *"Eventual consistency for an AI agent's memory — safe?"* → For read-mostly
context, yes; for anything the next action depends on, you need read-after-write.

---

### 15. Idempotency

**Definition.** The property that performing an operation multiple times has the same effect as
performing it once — the foundation of safe retries in any system that can fail and replay.

**Lexis:** *an idempotency key*, *a no-op on replay*, *at-least-once delivery*, *to deduplicate*,
*exactly-once as an illusion*, *a natural / derived key*, *safe to retry*.

**Model answer.** "Idempotency is, to my mind, the quiet hero of distributed systems. Once you
accept that messages arrive at-least-once — because exactly-once delivery across independent systems
is largely a fiction — you need every side-effecting operation to be safe to repeat. The pattern is
an idempotency key: a stable identifier for the operation, so that a replay becomes a no-op rather
than a double charge. The subtlety I've learned the hard way is that the *check* and the *write*
must be atomic, or two concurrent replays both pass the check — so the real guarantee has to live
in a database constraint, not an application-level `if`. It's also exactly how you make an AI
agent's retries safe: key every tool side-effect, and a re-run can't double-act."

**Grounded in your work.** "My payment-event consumer dedups in Redis with a twenty-four-hour TTL,
but what actually prevents a double notification is a *sparse unique index* on the event ID. I even
have a latent bug where the check-then-mark isn't atomic — the unique index is what saves me."

**Be ready for:** *"Who generates the key — client or server?"* → Client-supplied for end-to-end
safety across retries; the server enforces uniqueness. A server-only key can't dedupe a client retry.

---

### 16. Observability

**Definition.** The ability to understand a system's internal state from its outputs — logs,
metrics, and traces — well enough to answer questions you didn't anticipate, including *why* a
specific request behaved as it did.

**Lexis:** *logs, metrics, and traces*, *the three pillars*, *to instrument*, *a distributed
trace*, *high-cardinality telemetry*, *unknown-unknowns*, *to reconstruct a decision*.

**Model answer.** "Observability goes a step beyond monitoring. Monitoring answers questions you
knew to ask — is latency high, is the error rate up. Observability lets you interrogate the system
about things you *didn't* anticipate, which is where the hard bugs live. The three pillars are logs,
metrics, and traces, but the one I lean on most for distributed and agentic systems is the trace,
because it lets you reconstruct the path of a single request across many components. For an AI
agent that means capturing the whole decision trail — every reasoning step, every tool call, every
cost — so that when it does something strange, you can reconstruct *why* rather than shrug. You
genuinely cannot improve what you haven't instrumented."

**Grounded in your work.** "Instrumentation is how I found my real bottleneck — Witness returns
per-stage timings, and they revealed the twenty-two-second request was dominated by the storage
upload, not the model. Without those numbers I'd have optimised the wrong thing."

**Be ready for:** *"Logs vs traces for an agent?"* → Traces — you need the causal chain of steps
tied to one request ID; scattered logs can't reconstruct a multi-step decision.
