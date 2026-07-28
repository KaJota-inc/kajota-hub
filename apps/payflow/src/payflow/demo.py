"""One-shot narrative demo — designed for the 15-min pilot pitch screenshare.

Two modes:

- `run_demo()` (no CSV) — synthetic fixtures, full accuracy + calibration numbers.
  The "let me show you what Payflow does" version.

- `run_pilot_demo(csv_path, dialect)` — real bank data, PII-redacted at ingest,
  no accuracy (no labels) but shows the coverage story + confidence distribution
  + top KB misses + sample triage notes. The "let me run this on YOUR data" moment.
"""
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.table import Table

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
from payflow.ingest import (
    Redactor,
    compute_ingest_stats,
    envelopes_to_fixtures,
    print_ingest_stats,
    read_csv_envelopes,
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


def run_pilot_demo(
    csv_path: Path,
    dialect: Dialect,
    output_dir: Optional[Path] = None,
    console: Optional[Console] = None,
    sample_note_count: int = 3,
) -> None:
    """Demo pipeline on a bank's real CSV export. PII is redacted at ingest.

    No accuracy/calibration (pilot data is unlabelled by definition). Instead:
    coverage story + confidence distribution + top KB misses + sample notes.

    Requires PAYFLOW_REDACTION_SALT env var so the deterministic PII hashing
    is reproducible per-bank. Refuses to run without it.
    """
    console = console or Console()
    output_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp(prefix="payflow-pilot-"))
    output_dir.mkdir(parents=True, exist_ok=True)

    console.rule(f"[bold]payflow pilot demo — {csv_path.name} (dialect={dialect.value})")
    console.print(f"[dim]artifacts → {output_dir}[/dim]")
    console.print()

    kb = load_kb()

    _step(console, 1, 5, "Ingesting pilot CSV with PII redaction")
    t0 = time.perf_counter()
    redactor = Redactor()  # raises if PAYFLOW_REDACTION_SALT unset — fail fast, no leak
    envelopes = list(read_csv_envelopes(csv_path))
    fixtures = envelopes_to_fixtures(envelopes, dialect=dialect, redactor=redactor)
    fixtures_path = output_dir / "pilot-fixtures.jsonl"
    save_fixtures(fixtures, fixtures_path)
    _ok(console, f"{len(fixtures)} envelopes ingested + redacted in {_ms(t0)}ms → {fixtures_path.name}")
    console.print()

    _step(console, 2, 5, "Ingest stats — per-dialect, top codes, KB hit rate")
    stats = compute_ingest_stats(fixtures, kb=kb)
    print_ingest_stats(stats, console)
    console.print()

    _step(console, 3, 5, "KB-only triage across all pilot envelopes")
    t0 = time.perf_counter()
    predictions = run_eval(fixtures, EvalMode.KB_ONLY, kb=kb)
    _ok(console, f"{len(predictions)} predictions in {_ms(t0)}ms")

    conf_dist = Counter(p.predicted_confidence for p in predictions)
    retry_dist = Counter(p.predicted_retry_strategy.value for p in predictions)
    _print_pilot_distributions(console, conf_dist, retry_dist, len(predictions))
    console.print()

    _step(console, 4, 5, "KB miss priority list — codes to normalize next (or send to LLM)")
    if stats.kb_misses_top:
        miss_table = Table(title="Top KB misses on your data")
        miss_table.add_column("(dialect,code)", style="yellow")
        miss_table.add_column("Count", justify="right")
        for k, n in stats.kb_misses_top[:10]:
            miss_table.add_row(k, str(n))
        console.print(miss_table)
    else:
        console.print("[green]  No KB misses — every code on your traffic is already normalized.[/green]")
    console.print()

    _step(console, 5, 5, f"Sample triage notes from your data ({sample_note_count} tickets)")
    _print_sample_notes(console, fixtures, predictions, kb, sample_note_count)
    console.print()

    console.rule("[bold]pilot demo complete")
    console.print(
        f"[dim]All artifacts in {output_dir}. "
        "Next step: hand the fixtures.jsonl to ops for `payflow ingest label` "
        "to bootstrap the eval-with-accuracy loop.[/dim]"
    )


def _print_pilot_distributions(
    console: Console,
    conf_dist: Counter,
    retry_dist: Counter,
    total: int,
) -> None:
    tab = Table.grid(padding=(0, 2))
    tab.add_column(style="bold")
    tab.add_column()
    conf_str = "  ".join(
        f"{level}={n} ({n / total:.0%})"
        for level, n in sorted(conf_dist.items(), key=lambda x: -x[1])
    )
    retry_str = "  ".join(
        f"{s}={n} ({n / total:.0%})"
        for s, n in sorted(retry_dist.items(), key=lambda x: -x[1])
    )
    tab.add_row("Confidence:", conf_str)
    tab.add_row("Retry strategy:", retry_str)
    console.print(tab)


def _print_sample_notes(
    console: Console,
    fixtures: list,
    predictions: list,
    kb,
    count: int,
) -> None:
    """Pick up to `count` diverse samples — prefer envelopes with useful codes."""
    by_id = {fx.id: fx for fx in fixtures}
    triageable = [
        p for p in predictions
        if by_id.get(p.fixture_id) and by_id[p.fixture_id].source_code
    ]
    if not triageable:
        console.print("[yellow]  No triageable envelopes in the CSV (missing response codes).[/yellow]")
        return

    # Take an evenly-spaced slice for diversity, not just the first N.
    step = max(1, len(triageable) // count)
    picks = triageable[::step][:count]

    for i, p in enumerate(picks, 1):
        fx = by_id[p.fixture_id]
        console.print(f"[dim cyan]── sample {i}/{len(picks)}  (fixture {fx.id}) ──[/dim cyan]")
        # Re-parse the envelope and re-triage so the note has the full context
        # (Prediction alone doesn't carry the envelope).
        from payflow.eval.runner import _parse_fixture
        env = _parse_fixture(fx)
        result = _triage(env, kb)
        console.print(format_triage_note(result))
        console.print()


def _step(console: Console, i: int, total: int, msg: str) -> None:
    console.print(f"[bold cyan]▶ Step {i}/{total}:[/bold cyan] {msg}")


def _ok(console: Console, msg: str) -> None:
    console.print(f"  [green]✓[/green] {msg}")


def _ms(t0: float) -> int:
    return round((time.perf_counter() - t0) * 1000)
