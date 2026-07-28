"""One-shot narrative demo — designed for the 15-min pilot pitch screenshare.

Runs the whole pipeline in sequence and prints each artifact as it goes:
  1. Generate synthetic fixtures (or use a pilot CSV if provided)
  2. KB-only baseline
  3. Cross-mode bench (kb / llm / verifier — cost + latency)
  4. Confidence calibration (reliability diagram + ECE + Brier)
  5. Sample triage note (as it would appear in Freshdesk / Zendesk)

Each step is timed. Zero flags for the happy path — `payflow demo` just works.
"""
import tempfile
import time
from pathlib import Path
from typing import Optional

from rich.console import Console

from payflow.eval import (
    EvalMode,
    compute_bench,
    compute_calibration_per_mode,
    compute_metrics,
    format_bench_comparison,
    format_calibration,
    format_report,
    generate_all,
    load_fixtures,
    run_eval,
    save_fixtures,
    summarize_kinds,
)
from payflow.integrations._shared.format import format_triage_note
from payflow.kb import load_kb
from payflow.models import Dialect
from payflow.parser import parse_soap
from payflow.triage import triage as _triage

_SAMPLE_TICKET_SOAP = """<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://nibss.com/nip/">
  <soap:Body>
    <ns:FundsTransferResponse>
      <SessionID>099999123456789012345678900</SessionID>
      <BeneficiaryAccountNumber>0123456789</BeneficiaryAccountNumber>
      <Amount>150000.00</Amount>
      <ResponseCode>X03B</ResponseCode>
      <ResponseMessage>Response Wait Timeout</ResponseMessage>
    </ns:FundsTransferResponse>
  </soap:Body>
</soap:Envelope>"""


def run_demo(
    output_dir: Optional[Path] = None,
    console: Optional[Console] = None,
) -> None:
    console = console or Console()
    output_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="payflow-demo-"))
    output_dir.mkdir(parents=True, exist_ok=True)

    console.rule("[bold]payflow demo — end-to-end pipeline in one pass")
    console.print(f"[dim]artifacts → {output_dir}[/dim]")
    console.print()

    kb = load_kb()

    _step(console, 1, 5, "Generating synthetic fixtures across 4 kinds")
    t0 = time.perf_counter()
    fixtures = generate_all(kb=kb)
    fixtures_path = output_dir / "fixtures.jsonl"
    save_fixtures(fixtures, fixtures_path)
    _ok(console, f"{summarize_kinds(fixtures)} in {_ms(t0)}ms → {fixtures_path.name}")
    console.print()

    _step(console, 2, 5, "KB-only baseline: deterministic triage on all fixtures")
    t0 = time.perf_counter()
    predictions = run_eval(fixtures, EvalMode.KB_ONLY, kb=kb)
    metrics = compute_metrics(fixtures, predictions, mode="kb_only")
    _ok(console, f"{metrics.total} predictions in {_ms(t0)}ms")
    format_report(metrics, console)
    console.print()

    _step(console, 3, 5, "Cross-mode bench: latency + estimated cost")
    console.print(
        "[dim]  LLM/verifier modes without ANTHROPIC_API_KEY hit the error path (fast + free);"
        " latency numbers below reflect that. Cost estimates use documented token counts.[/dim]"
    )
    reports = []
    for mode in [EvalMode.KB_ONLY, EvalMode.WITH_LLM, EvalMode.WITH_VERIFIER]:
        try:
            preds = run_eval(fixtures, mode, kb=kb)
            reports.append(compute_bench(preds, mode=mode.value))
        except Exception as e:
            console.print(f"[yellow]skipped {mode.value}: {e}[/yellow]")
    format_bench_comparison(reports, console)
    console.print()

    _step(console, 4, 5, "Confidence calibration: reliability diagram")
    calibration_reports = compute_calibration_per_mode(fixtures, predictions)
    for r in calibration_reports:
        format_calibration(r, console)
    console.print()

    _step(console, 5, 5, "Sample triage note (as it would appear on a ticket)")
    envelope = parse_soap(_SAMPLE_TICKET_SOAP)
    envelope.dialect = Dialect.CORE
    result = _triage(envelope, kb)
    console.print(format_triage_note(result))
    console.print()

    console.rule("[bold]demo complete")
    console.print(
        f"[dim]All artifacts saved to {output_dir}. "
        "Rerun any step with `payflow eval ...` or `payflow triage ...` for deeper drills.[/dim]"
    )


def _step(console: Console, i: int, total: int, msg: str) -> None:
    console.print(f"[bold cyan]▶ Step {i}/{total}:[/bold cyan] {msg}")


def _ok(console: Console, msg: str) -> None:
    console.print(f"  [green]✓[/green] {msg}")


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)
