"""Verbose reasoning trace for a single envelope.

`payflow explain` walks through the pipeline layer by layer and prints:
- What the deterministic KB layer decided (and why)
- What the LLM triager would decide (either simulated cost estimate or a
  real call with `--force-llm`)
- What the verifier would say (either simulated or `--force-verify`)
- The final verdict + a per-layer cost accounting

This is a trust feature for pilot conversations ("how does it reason?") and a
research/SOP artefact ("here is the evidence chain for a decision").
"""
from typing import Any, Optional

from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from payflow.eval.bench import LLM_TRIAGER_TOKENS_CACHED, PRICING_PER_MTOK, VERIFIER_TOKENS
from payflow.kb import KB, load_kb, lookup
from payflow.models import Envelope, Retryability, TriageResult
from payflow.triage import LLMTriager, LLMVerifier
from payflow.triage.deterministic import triage_deterministic
from payflow.triage.llm import TriagerProtocol
from payflow.triage.verifier import VerifierProtocol


class ExplainReport(BaseModel):
    envelope: Envelope
    kb_result: TriageResult
    llm_result: Optional[TriageResult] = None
    verified_result: Optional[TriageResult] = None
    final_result: TriageResult
    layers_fired: list[str]
    layers_simulated: list[str]
    estimated_llm_cost_usd: float = 0.0
    estimated_verifier_cost_usd: float = 0.0
    llm_model: Optional[str] = None
    verifier_model: Optional[str] = None


def run_explain(
    env: Envelope,
    kb: Optional[KB] = None,
    *,
    force_llm: bool = False,
    force_verify: bool = False,
    llm_triager: Optional[TriagerProtocol] = None,
    llm_verifier: Optional[VerifierProtocol] = None,
    llm_model: str = "claude-haiku-4-5-20251001",
    verifier_model: str = "claude-sonnet-5",
) -> ExplainReport:
    """Trace the pipeline verbosely.

    Rules:
    - Deterministic KB always runs first
    - LLM triager runs if KB missed OR `force_llm=True`
    - Verifier runs if LLM ran AND (verify was configured OR `force_verify=True`)
    - When a layer does NOT run, we estimate what it WOULD have cost so
      the accounting is complete regardless
    """
    kb = kb or load_kb()

    kb_result = triage_deterministic(env, kb)
    layers_fired = ["deterministic"]
    layers_simulated: list[str] = []
    final_result = kb_result

    llm_result: Optional[TriageResult] = None
    verified_result: Optional[TriageResult] = None

    kb_hit = kb_result.confidence == "high"
    should_fire_llm = force_llm or not kb_hit

    est_llm_cost = _estimate_llm_cost(llm_model)
    est_verifier_cost = _estimate_verifier_cost(verifier_model)

    if should_fire_llm:
        triager = llm_triager or LLMTriager(model=llm_model)
        try:
            llm_result = triager.triage(env, kb)
            layers_fired.append("llm")
            final_result = llm_result
        except Exception as e:
            # Live LLM call may fail (no API key, network, etc.) — mark as simulated
            # so the report still tells the user what would have happened.
            layers_simulated.append(f"llm ({type(e).__name__}: {e})")
    else:
        layers_simulated.append("llm (KB hit short-circuited)")

    should_fire_verify = llm_result is not None and force_verify
    if should_fire_verify:
        verifier = llm_verifier or LLMVerifier(model=verifier_model)
        try:
            verified_result = verifier.verify(env, llm_result)
            layers_fired.append("verifier")
            final_result = verified_result
        except Exception as e:
            layers_simulated.append(f"verifier ({type(e).__name__}: {e})")
    else:
        if llm_result is None:
            layers_simulated.append("verifier (LLM did not fire)")
        else:
            layers_simulated.append("verifier (verify=False)")

    return ExplainReport(
        envelope=env,
        kb_result=kb_result,
        llm_result=llm_result,
        verified_result=verified_result,
        final_result=final_result,
        layers_fired=layers_fired,
        layers_simulated=layers_simulated,
        estimated_llm_cost_usd=est_llm_cost if "llm" not in layers_fired else 0.0,
        estimated_verifier_cost_usd=est_verifier_cost if "verifier" not in layers_fired else 0.0,
        llm_model=llm_model,
        verifier_model=verifier_model,
    )


def _estimate_llm_cost(model: str) -> float:
    price = PRICING_PER_MTOK.get(model)
    if price is None:
        return 0.0
    t = LLM_TRIAGER_TOKENS_CACHED
    return (
        t["input"] / 1_000_000 * price["input"]
        + t["output"] / 1_000_000 * price["output"]
        + t["cache_read"] / 1_000_000 * price["cache_read"]
    )


def _estimate_verifier_cost(model: str) -> float:
    price = PRICING_PER_MTOK.get(model)
    if price is None:
        return 0.0
    return (
        VERIFIER_TOKENS["input"] / 1_000_000 * price["input"]
        + VERIFIER_TOKENS["output"] / 1_000_000 * price["output"]
    )


# --- formatting -----------------------------------------------------------


def format_explain(report: ExplainReport, console: Optional[Console] = None) -> None:
    console = console or Console()
    env = report.envelope

    console.rule("[bold]payflow explain — reasoning trace")
    _print_envelope(console, env)
    console.print()

    _print_kb_layer(console, report)
    console.print()

    _print_llm_layer(console, report)
    console.print()

    _print_verifier_layer(console, report)
    console.print()

    _print_verdict(console, report)
    console.print()

    _print_cost_accounting(console, report)


def _print_envelope(console: Console, env: Envelope) -> None:
    grid = Table.grid(padding=(0, 2))
    grid.add_column(style="bold")
    grid.add_column()
    grid.add_row("Source", env.source)
    grid.add_row("Dialect", env.dialect.value if env.dialect else "[red]<none>[/red]")
    grid.add_row("Method", env.method or "[dim]<none>[/dim]")
    grid.add_row("Session ID", env.session_id or "[dim]<none>[/dim]")
    grid.add_row("Response code", env.response_code or "[dim]<none>[/dim]")
    grid.add_row("Response message", env.response_message or "[dim]<none>[/dim]")
    if env.amount is not None:
        grid.add_row("Amount", str(env.amount))
    console.print(Panel(grid, title="[cyan]Envelope[/cyan]", expand=False))


def _print_kb_layer(console: Console, report: ExplainReport) -> None:
    kb = report.kb_result
    hit = kb.confidence == "high"
    header = (
        "[green]KB HIT[/green] — deterministic verdict wins"
        if hit
        else "[yellow]KB MISS[/yellow] — fall through to LLM"
    )
    lines = [
        header,
        f"[bold]Confidence:[/bold] {kb.confidence}",
        f"[bold]Retry strategy:[/bold] [magenta]{kb.retry_strategy.value}[/magenta]",
        f"[bold]Cause:[/bold] {kb.cause}",
        f"[bold]Action:[/bold] {kb.action}",
    ]
    if kb.evidence:
        lines.append("[bold]Evidence:[/bold]")
        lines.extend(f"  · {e}" for e in kb.evidence)
    console.print(Panel("\n".join(lines), title="[cyan]Layer 1 — Deterministic KB[/cyan]", expand=False))


def _print_llm_layer(console: Console, report: ExplainReport) -> None:
    if report.llm_result is not None:
        r = report.llm_result
        lines = [
            "[green]LLM FIRED[/green]",
            f"[bold]Model:[/bold] {report.llm_model}",
            f"[bold]Confidence:[/bold] {r.confidence}",
            f"[bold]Retry strategy:[/bold] [magenta]{r.retry_strategy.value}[/magenta]",
            f"[bold]Cause:[/bold] {r.cause}",
        ]
        if r.evidence:
            lines.append("[bold]Evidence:[/bold]")
            lines.extend(f"  · {e}" for e in r.evidence)
        console.print(Panel("\n".join(lines), title="[cyan]Layer 2 — LLM triager[/cyan]", expand=False))
        return

    # Layer didn't fire — explain why + hypothetical cost
    reason = next(
        (s for s in report.layers_simulated if s.startswith("llm")),
        "llm (not attempted)",
    )
    lines = [
        f"[yellow]SIMULATED[/yellow] — {reason}",
        f"[bold]Model that would fire:[/bold] {report.llm_model}",
        f"[bold]Est. cost if fired:[/bold] ${report.estimated_llm_cost_usd:.6f} per envelope",
    ]
    console.print(Panel("\n".join(lines), title="[cyan]Layer 2 — LLM triager[/cyan]", expand=False))


def _print_verifier_layer(console: Console, report: ExplainReport) -> None:
    if report.verified_result is not None:
        r = report.verified_result
        downgraded = (
            report.llm_result is not None
            and r.retry_strategy == Retryability.STATUS_QUERY
            and r.retry_strategy != report.llm_result.retry_strategy
        )
        header = (
            "[red]DOWNGRADED[/red] — verifier flagged proposal as unsafe/ungrounded"
            if downgraded
            else "[green]APPROVED[/green] — verifier confirmed proposal"
        )
        lines = [
            header,
            f"[bold]Model:[/bold] {report.verifier_model}",
            f"[bold]Final retry strategy:[/bold] [magenta]{r.retry_strategy.value}[/magenta]",
            f"[bold]Final confidence:[/bold] {r.confidence}",
        ]
        console.print(Panel("\n".join(lines), title="[cyan]Layer 3 — Adversarial verifier[/cyan]", expand=False))
        return

    reason = next(
        (s for s in report.layers_simulated if s.startswith("verifier")),
        "verifier (not attempted)",
    )
    lines = [
        f"[yellow]SIMULATED[/yellow] — {reason}",
        f"[bold]Model that would fire:[/bold] {report.verifier_model}",
        f"[bold]Est. cost if fired:[/bold] ${report.estimated_verifier_cost_usd:.6f} per envelope",
    ]
    console.print(Panel("\n".join(lines), title="[cyan]Layer 3 — Adversarial verifier[/cyan]", expand=False))


def _print_verdict(console: Console, report: ExplainReport) -> None:
    r = report.final_result
    lines = [
        f"[bold]Cause:[/bold] {r.cause}",
        f"[bold]Ops action:[/bold] {r.action}",
        f"[bold]Retry strategy:[/bold] [magenta]{r.retry_strategy.value}[/magenta]"
        f" ({'retryable' if r.retryable else 'terminal'})",
        f"[bold]Confidence:[/bold] {r.confidence}",
    ]
    if r.matched_code:
        lines.append(f"[bold]Customer-safe:[/bold] {r.matched_code.customer_message}")
    console.print(Panel("\n".join(lines), title="[bold green]Final verdict[/bold green]", expand=False))


def _print_cost_accounting(console: Console, report: ExplainReport) -> None:
    tab = Table(title="Layer accounting")
    tab.add_column("Layer", style="cyan")
    tab.add_column("Fired?")
    tab.add_column("Cost per envelope", justify="right")
    tab.add_row("Deterministic KB", "[green]yes[/green]", "$0.00")
    llm_fired = "[green]yes[/green]" if "llm" in report.layers_fired else "[dim]no (est.)[/dim]"
    tab.add_row(
        f"LLM ({report.llm_model})",
        llm_fired,
        f"${_estimate_llm_cost(report.llm_model):.6f}",
    )
    verifier_fired = "[green]yes[/green]" if "verifier" in report.layers_fired else "[dim]no (est.)[/dim]"
    tab.add_row(
        f"Verifier ({report.verifier_model})",
        verifier_fired,
        f"${_estimate_verifier_cost(report.verifier_model):.6f}",
    )
    console.print(tab)
