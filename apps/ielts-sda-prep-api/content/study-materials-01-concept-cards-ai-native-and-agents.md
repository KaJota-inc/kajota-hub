# Concept Cards A — AI-Native Systems & Agents

*Each card: definition → band-7.5+ lexis → a spoken model answer (~90s) → grounding in your work
→ the follow-up to expect. Read the model answers aloud; they are tuned for IELTS Speaking Part 3
register and double as PhD/technical-interview answers.*

---

### 1. What makes a system AI-native

**Definition.** A system is *AI-native* when a learned model sits on the critical path as a
first-class component — not bolted on as a feature — so the architecture is built around the
model's unpredictability, cost, and need for evaluation from day one.

**Lexis:** *on the critical path*, *first-class component*, *bolted-on*, *non-deterministic core*,
*evaluation-driven design*, *to architect around*, *a probabilistic dependency*.

**Model answer.** "I'd draw a sharp distinction between a system that *uses* AI and one that is
genuinely AI-native. In the former, a model is bolted on — a sprinkling of classification on top
of otherwise deterministic software. In an AI-native system, by contrast, a learned model sits
squarely *on the critical path*, which forces you to architect around three awkward properties:
it is non-deterministic, it is expensive, and its quality drifts. So the tell-tale signs are
structural — you'll see evaluation built into the workflow rather than tacked on at the end,
guardrails around the model's outputs, and graceful degradation when it misbehaves. What strikes
me is that being AI-native is less about *having* a model and more about having *designed for its
unreliability*."

**Grounded in your work.** "My Pulse recommender is AI-native in that sense — the Gemini call is
on the critical path, so I built a bounded retry and a deterministic heuristic *floor* around it,
and I measured the fallback rate as a first-class metric."

**Be ready for:** *"Isn't every system with an API call to an LLM AI-native?"* → No — the test is
whether the architecture *changes* to accommodate the model's properties. A thin wrapper isn't.

---

### 2. AI agents and agentic systems

**Definition.** An agent is a system that pursues a goal by *planning, taking actions through
tools, observing results, and iterating* — rather than producing a single response. Agentic
systems chain these loops, often across multiple specialised agents.

**Lexis:** *to pursue a goal autonomously*, *a perceive–plan–act loop*, *tool use*, *bounded
autonomy*, *to decompose a task*, *orchestration*, *handoff between agents*.

**Model answer.** "An agent differs from a plain model call in that it operates in a loop — it
plans, acts through tools, observes the outcome, and decides what to do next, all in service of a
goal. That autonomy is precisely what makes agentic systems powerful and, equally, what makes them
treacherous. The reliability maths is unforgiving: if each step is ninety-five per cent reliable,
a twenty-step task succeeds barely a third of the time. So the engineering challenge isn't making
an agent clever; it's making a *long* chain of steps reliable — through bounded scope, verification
at each step, and a human placed where being wrong is costly. I tend to think of the orchestrator
as a deterministic spine and the model as the reasoning muscle it permits to move, but only within
limits."

**Grounded in your work.** "My Witness system is agentic — three juror agents deliberate in
parallel and a judge synthesises — but I deliberately kept the *consequential* decisions bounded:
unparseable output defaults to human escalation rather than a confident guess."

**Be ready for:** *"When would you NOT use an agent?"* → When a deterministic pipeline suffices;
autonomy you don't need is just a new surface for failure.

---

### 3. LLM-based software agents

**Definition.** Agents whose reasoning engine is a large language model, which plans in natural
language, selects tools via function-calling, and maintains context through a memory layer.

**Lexis:** *function-calling*, *a reasoning engine*, *context window*, *scratchpad / working
memory*, *tool routing*, *to ground a decision*, *prompt as interface*.

**Model answer.** "An LLM-based agent uses a language model as its reasoning engine — it plans in
natural language, then calls tools through a structured interface, typically function-calling. The
appeal is obvious: you get flexible reasoning without hand-coding every branch. The catch is that
the model's output is a *suggestion*, not a guarantee, so everything it emits has to be treated as
untrusted until validated. In practice I find the hard problems aren't in the model at all — they
sit in the plumbing around it: how you route tools safely, how you manage a finite context window,
and how you keep the thing from looping. The model, frankly, is the easy part; turning it into a
dependable service is ordinary distributed-systems engineering applied to an unusually expensive
and unpredictable dependency."

**Grounded in your work.** "My Coach agent uses Gemini with function-calling over MongoDB tools
discovered through MCP — and the lesson I took away is that I was patching behaviour through the
*prompt* when I should have enforced it in code; forcing tool-use by shouting in the prompt is a
smell."

**Be ready for:** *"How do you make a tool output safe to feed back to the model?"* → Validate the
schema, bound its size, strip anything that could be a prompt injection, and treat it as data.

---

### 4. Autonomous decision-making

**Definition.** A system acting without human sign-off per decision, within explicitly delegated
authority and hard constraints — distinct from automation, which executes fixed rules.

**Lexis:** *delegated authority*, *within guardrails*, *a confidence threshold*, *to act without
sign-off*, *bounded autonomy*, *a kill-switch*, *deterministic safety constraints*.

**Model answer.** "Autonomy, to me, is a spectrum rather than a switch. The question is never
'should the system act on its own' but 'how much authority have we delegated, and what are the
hard limits'. The design pattern I trust is to pair autonomous reasoning with *deterministic*
safety constraints — let the model decide freely, but gate anything consequential behind a
threshold. Above a certain confidence or a certain monetary value, the decision routes to a human,
because the cost of a wrong auto-approval dwarfs the cost of a brief delay. I'm wary of framing
autonomy as a virtue in itself; unneeded autonomy simply widens the blast radius when something
goes wrong."

**Grounded in your work.** "In my Mesh escrow, the operator *can* release funds autonomously, but
I deliberately rate-limited that path behind a two-day grace period and let the buyer's
confirmation be the fast path — so a compromised key can't instant-drain deposits."

**Be ready for:** *"Where exactly do you draw the autonomy line?"* → At the point where reversal
becomes expensive or impossible; irreversibility is the real axis, not confidence alone.

---

### 5. Human-in-the-loop systems

**Definition.** Designs that insert human judgment at defined points — approval, correction, or
escalation — to catch what the model gets wrong, especially on high-stakes or low-confidence
decisions.

**Lexis:** *to insert human judgment*, *an escalation path*, *review queue*, *fail toward a
human*, *active learning*, *oversight*, *a confidence-gated handoff*.

**Model answer.** "Human-in-the-loop is less a feature than a *posture* — it's deciding, up front,
that the system should fail toward a human rather than toward a confident error. The art is in
*where* you place the human, because put them everywhere and you've destroyed the efficiency that
justified the AI in the first place. So I gate on stakes and confidence: routine, high-confidence
cases flow through automatically, while the long tail — the ambiguous, the expensive, the novel —
lands in a review queue. There's a lovely secondary benefit, too: those human corrections become
labelled data, so the loop quietly improves the model over time through active learning."

**Grounded in your work.** "My Witness jury embodies this — when the model's ruling can't be
parsed or confidence is low, the verdict defaults to `escalate_to_human`. The system never
pretends to a certainty it doesn't have."

**Be ready for:** *"Doesn't a human in the loop just move the bottleneck?"* → Only if you gate
badly; the point is to route *selectively* so humans see the few cases that actually need them.

---

### 6. Monitoring autonomous agents

**Definition.** Continuous observation of a running agent — its traces, tool calls, costs,
loop behaviour, and output quality — so drift and failures are caught in production, not by users.

**Lexis:** *tracing*, *a decision trail*, *cost and token telemetry*, *drift detection*, *to
instrument*, *online evaluation*, *anomaly detection on behaviour*.

**Model answer.** "Monitoring an agent is harder than monitoring a service, because the failure
modes are stranger — it isn't just latency and errors, it's hallucinated actions, overconfidence,
and runaway loops. So I instrument three things: the *trace* of every reasoning step and tool call,
so a decision can be reconstructed; the *cost*, because an agent can quietly burn tokens in a loop;
and the *quality*, through online evaluation sampling live traffic. The guiding principle is that
evaluation can't be a pre-launch ritual — it has to live inside the running workflow, continuously,
so that quality drift is caught *before users complain* rather than after."

**Grounded in your work.** "My Witness responses carry per-stage timings — evidence, jury,
verdict-write, anchor — which is exactly how I discovered the bottleneck was the storage upload,
not the model. You can't improve what you don't instrument."

**Be ready for:** *"What's the single most important thing to log?"* → The full decision trace
tied to an idempotency key — without it, you can neither debug nor audit a wrong action.
