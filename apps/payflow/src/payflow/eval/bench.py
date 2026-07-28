from typing import Optional

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from payflow.eval.fixture import Prediction

# Per-million-token prices. Verify against vendor pricing pages before quoting on a pilot call.
# Anthropic: https://www.anthropic.com/pricing   Gemini: https://ai.google.dev/pricing
PRICING_PER_MTOK: dict[str, dict[str, float]] = {
    "claude-haiku-4-5-20251001": {
        "input": 1.00, "output": 5.00, "cache_read": 0.10, "cache_write": 1.25,
    },
    "claude-sonnet-5": {
        "input": 3.00, "output": 15.00, "cache_read": 0.30, "cache_write": 3.75,
    },
    "gemini-2.5-flash-lite": {
        "input": 0.10, "output": 0.40, "cache_read": 0.025, "cache_write": 0.10,
    },
    "gemini-2.5-flash": {
        "input": 0.30, "output": 2.50, "cache_read": 0.075, "cache_write": 0.30,
    },
    "gemini-2.5-pro": {
        "input": 1.25, "output": 10.00, "cache_read": 0.3125, "cache_write": 1.25,
    },
}

# Anthropic path uses prompt caching (~1800 KB tokens sent once, cached-read thereafter).
LLM_TRIAGER_TOKENS_CACHED = {
    "input": 250,          # envelope JSON + user question
    "output": 180,         # tool_use structured response
    "cache_read": 1800,    # KB + role prompt (cache hit after 1st call)
}
# Gemini path (MVP): no prompt caching yet, so the KB rides in `input` every call.
# TODO: wire Gemini context caching in GeminiTriager, then swap to a cached profile.
LLM_TRIAGER_TOKENS_UNCACHED = {
    "input": 2050,         # (250 message + 1800 system, sent every call)
    "output": 180,
    "cache_read": 0,
}
VERIFIER_TOKENS = {
    "input": 400,          # envelope + proposed verdict
    "output": 80,          # tool_use verdict
}


def _is_gemini(model_name: str) -> bool:
    return "gemini" in model_name.lower()


def _triager_tokens_for(model_name: str) -> dict:
    return LLM_TRIAGER_TOKENS_UNCACHED if _is_gemini(model_name) else LLM_TRIAGER_TOKENS_CACHED


# Kept for backwards compat with existing test imports and any downstream users.
LLM_TRIAGER_TOKENS = LLM_TRIAGER_TOKENS_CACHED


class BenchLatency(BaseModel):
    p50_ms: float
    p95_ms: float
    p99_ms: float
    mean_ms: float
    total_ms: float
    max_ms: float


class BenchCost(BaseModel):
    model_config = {"protected_namespaces": ()}

    mode: str
    llm_model: Optional[str] = None
    verifier_model: Optional[str] = None
    per_envelope_usd: float
    per_1k_usd: float
    per_10k_usd: float
    per_100k_usd: float


class BenchReport(BaseModel):
    mode: str
    total: int
    latency: BenchLatency
    cost: BenchCost
    throughput_envelopes_per_sec: float


def compute_bench(
    predictions: list[Prediction],
    *,
    mode: Optional[str] = None,
    llm_model: str = "claude-haiku-4-5-20251001",
    verifier_model: str = "claude-sonnet-5",
) -> BenchReport:
    filtered = [p for p in predictions if (mode is None or p.mode == mode)]
    if not filtered:
        raise ValueError(f"No predictions for mode {mode!r}")
    resolved = mode or filtered[0].mode

    durations = [p.duration_ms for p in filtered]
    mean_ms = sum(durations) / len(durations)
    latency = BenchLatency(
        p50_ms=_percentile(durations, 0.50),
        p95_ms=_percentile(durations, 0.95),
        p99_ms=_percentile(durations, 0.99),
        mean_ms=mean_ms,
        total_ms=sum(durations),
        max_ms=max(durations),
    )
    cost = _estimate_cost(resolved, llm_model, verifier_model)
    throughput = 1000.0 / mean_ms if mean_ms > 0 else float("inf")
    return BenchReport(
        mode=resolved,
        total=len(filtered),
        latency=latency,
        cost=cost,
        throughput_envelopes_per_sec=throughput,
    )


def _percentile(data: list[float], q: float) -> float:
    if not data:
        return 0.0
    if len(data) == 1:
        return data[0]
    sorted_data = sorted(data)
    idx = min(int(q * len(sorted_data)), len(sorted_data) - 1)
    return sorted_data[idx]


def _estimate_cost(mode: str, llm_model: str, verifier_model: str) -> BenchCost:
    if mode == "kb_only":
        return BenchCost(
            mode=mode, per_envelope_usd=0.0,
            per_1k_usd=0.0, per_10k_usd=0.0, per_100k_usd=0.0,
        )
    primary = PRICING_PER_MTOK.get(llm_model)
    if primary is None:
        raise ValueError(f"No pricing for llm_model={llm_model!r}. Add to PRICING_PER_MTOK.")

    tokens = _triager_tokens_for(llm_model)
    per_envelope = (
        tokens["input"] / 1_000_000 * primary["input"]
        + tokens["output"] / 1_000_000 * primary["output"]
        + tokens["cache_read"] / 1_000_000 * primary["cache_read"]
    )
    resolved_verifier_model = None
    if mode == "with_verifier":
        vp = PRICING_PER_MTOK.get(verifier_model)
        if vp is None:
            raise ValueError(f"No pricing for verifier_model={verifier_model!r}. Add to PRICING_PER_MTOK.")
        per_envelope += (
            VERIFIER_TOKENS["input"] / 1_000_000 * vp["input"]
            + VERIFIER_TOKENS["output"] / 1_000_000 * vp["output"]
        )
        resolved_verifier_model = verifier_model
    return BenchCost(
        mode=mode,
        llm_model=llm_model,
        verifier_model=resolved_verifier_model,
        per_envelope_usd=per_envelope,
        per_1k_usd=per_envelope * 1_000,
        per_10k_usd=per_envelope * 10_000,
        per_100k_usd=per_envelope * 100_000,
    )


def format_bench(report: BenchReport, console: Optional[Console] = None) -> None:
    console = console or Console()
    console.rule(f"[bold]Bench — mode: [cyan]{report.mode}[/cyan]")

    top = Table.grid(padding=(0, 2))
    top.add_column(style="bold")
    top.add_column()
    top.add_row("Envelopes measured:", str(report.total))
    top.add_row(
        "Latency:",
        f"p50={report.latency.p50_ms:.2f}ms  p95={report.latency.p95_ms:.2f}ms  "
        f"p99={report.latency.p99_ms:.2f}ms  mean={report.latency.mean_ms:.2f}ms  "
        f"max={report.latency.max_ms:.2f}ms",
    )
    tps = report.throughput_envelopes_per_sec
    tps_str = f"{tps:.0f} envelopes/sec" if tps != float("inf") else "n/a (0ms)"
    top.add_row("Throughput:", tps_str)
    console.print(top)

    cost_table = Table(title="Cost projections")
    cost_table.add_column("Volume", style="cyan")
    cost_table.add_column("Cost (USD)", justify="right")
    for label, value in [
        ("per envelope", report.cost.per_envelope_usd),
        ("per 1,000 envelopes", report.cost.per_1k_usd),
        ("per 10,000 envelopes", report.cost.per_10k_usd),
        ("per 100,000 envelopes", report.cost.per_100k_usd),
    ]:
        cost_table.add_row(label, _fmt_usd(value))
    console.print(cost_table)

    if report.cost.llm_model:
        note = f"LLM model: [magenta]{report.cost.llm_model}[/magenta]"
        if report.cost.verifier_model:
            note += f"  +  Verifier: [magenta]{report.cost.verifier_model}[/magenta]"
        console.print(f"[dim]{note}[/dim]")


def format_bench_comparison(reports: list[BenchReport], console: Optional[Console] = None) -> None:
    console = console or Console()
    console.rule("[bold]Bench comparison across modes")

    tab = Table(title="Latency & throughput")
    tab.add_column("Mode", style="cyan")
    tab.add_column("Envs", justify="right")
    tab.add_column("p50 ms", justify="right")
    tab.add_column("p95 ms", justify="right")
    tab.add_column("p99 ms", justify="right")
    tab.add_column("mean ms", justify="right")
    tab.add_column("env/sec", justify="right")
    for r in reports:
        tps = r.throughput_envelopes_per_sec
        tps_str = f"{tps:.0f}" if tps != float("inf") else "∞"
        tab.add_row(
            r.mode, str(r.total),
            f"{r.latency.p50_ms:.2f}", f"{r.latency.p95_ms:.2f}",
            f"{r.latency.p99_ms:.2f}", f"{r.latency.mean_ms:.2f}",
            tps_str,
        )
    console.print(tab)

    cost_tab = Table(title="Cost projections (USD)")
    cost_tab.add_column("Mode", style="cyan")
    cost_tab.add_column("per envelope", justify="right")
    cost_tab.add_column("per 1k", justify="right")
    cost_tab.add_column("per 10k", justify="right")
    cost_tab.add_column("per 100k", justify="right")
    for r in reports:
        cost_tab.add_row(
            r.mode,
            _fmt_usd(r.cost.per_envelope_usd),
            _fmt_usd(r.cost.per_1k_usd),
            _fmt_usd(r.cost.per_10k_usd),
            _fmt_usd(r.cost.per_100k_usd),
        )
    console.print(cost_tab)


def _fmt_usd(v: float) -> str:
    if v == 0:
        return "$0.00"
    if v < 0.01:
        return f"${v:.6f}"
    if v < 1:
        return f"${v:.4f}"
    return f"${v:,.2f}"
