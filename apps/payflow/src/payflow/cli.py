from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from payflow.eval import (
    EvalMode,
    compute_bench,
    compute_calibration_per_mode,
    compute_metrics,
    format_bench,
    format_bench_comparison,
    format_calibration,
    format_report,
    generate_all,
    load_fixtures,
    run_eval,
    save_fixtures,
    summarize_kinds,
)
from payflow.eval.fixture import load_predictions, save_fixtures as _save_fixtures, save_predictions
from payflow.ingest import (
    Redactor,
    compute_ingest_stats,
    envelopes_to_fixtures,
    label_fixtures,
    print_ingest_stats,
    read_csv_envelopes,
)
from payflow.kb import load_kb
from payflow.models import Dialect, TriageResult
from payflow.parser import parse_file
from payflow.triage import triage as _triage
from payflow.triage import triage_deterministic, triage_envelope  # noqa: F401 — public re-export

app = typer.Typer(no_args_is_help=True, add_completion=False, help="Payflow — NIP payment-ops triage.")
eval_app = typer.Typer(no_args_is_help=True, help="Fixture-based eval harness.")
ingest_app = typer.Typer(no_args_is_help=True, help="Real-pilot ingest (CSV / Postgres).")
fd_app = typer.Typer(no_args_is_help=True, help="Freshdesk integration (webhook + offline triage).")
zd_app = typer.Typer(no_args_is_help=True, help="Zendesk integration (webhook + offline triage).")
app.add_typer(eval_app, name="eval")
app.add_typer(ingest_app, name="ingest")
app.add_typer(fd_app, name="freshdesk")
app.add_typer(zd_app, name="zendesk")
console = Console()


@app.command()
def parse(path: Path) -> None:
    """Parse a NIP envelope (SOAP XML | JSON | Remita audit-trail row) and dump it."""
    env = parse_file(path)
    console.print_json(env.model_dump_json(indent=2))


@app.command()
def triage(
    path: Path,
    dialect: Dialect = typer.Option(Dialect.CORE, help="CBA dialect for the response code."),
    use_llm: bool = typer.Option(False, "--use-llm", help="Fall back to LLM when the KB misses."),
    verify: bool = typer.Option(False, "--verify", help="Run adversarial verifier over LLM output."),
) -> None:
    """Triage a NIP envelope. KB first, LLM fallback on misses if --use-llm."""
    env = parse_file(path)
    env.dialect = dialect
    result = _triage(env, load_kb(), use_llm=use_llm, verify=verify)
    _print_triage(result)


@app.command("kb-show")
def kb_show(dialect: Dialect = typer.Option(..., help="Which dialect to inspect.")) -> None:
    """Show all normalized entries for a dialect."""
    kb = load_kb()
    entries = sorted(
        (v for k, v in kb.items() if k[0] == dialect),
        key=lambda x: x.code,
    )
    table = Table(title=f"{dialect.value.upper()} response-code KB — {len(entries)} entries")
    table.add_column("Code", style="cyan")
    table.add_column("Category")
    table.add_column("Retry")
    table.add_column("Raw message")
    for e in entries:
        table.add_row(e.code, e.category.value, e.retry.value, e.raw_message)
    console.print(table)


@app.command("kb-stats")
def kb_stats() -> None:
    """Per-dialect entry counts and cross-dialect code collisions."""
    kb = load_kb()
    per_dialect: dict[Dialect, int] = {}
    per_code: dict[str, set[Dialect]] = {}
    for (dialect, code), _ in kb.items():
        per_dialect[dialect] = per_dialect.get(dialect, 0) + 1
        per_code.setdefault(code, set()).add(dialect)

    t1 = Table(title="Entries per dialect")
    t1.add_column("Dialect", style="cyan")
    t1.add_column("Entries", justify="right")
    for d, n in sorted(per_dialect.items(), key=lambda x: -x[1]):
        t1.add_row(d.value, str(n))
    console.print(t1)

    collisions = {c: ds for c, ds in per_code.items() if len(ds) > 1}
    t2 = Table(title=f"Cross-dialect code collisions ({len(collisions)} codes)")
    t2.add_column("Code", style="cyan")
    t2.add_column("Present in dialects")
    for code, ds in sorted(collisions.items()):
        t2.add_row(code, ", ".join(sorted(d.value for d in ds)))
    console.print(t2)


def _print_triage(r: TriageResult) -> None:
    console.rule(f"[bold]Triage: {r.envelope.method or 'unknown'} · session={r.envelope.session_id or '—'}")
    console.print(f"[bold]Cause:[/bold] {r.cause}")
    console.print(f"[bold]Ops action:[/bold] {r.action}")
    console.print(f"[bold]Retryable:[/bold] {r.retryable} ([magenta]{r.retry_strategy.value}[/magenta])")
    console.print(f"[bold]Confidence:[/bold] {r.confidence}")
    if r.matched_code:
        console.print(f"[bold]Customer-safe:[/bold] {r.matched_code.customer_message}")
        console.print(f"[bold]Category:[/bold] {r.matched_code.category.value}")
    if r.evidence:
        console.print("[bold]Evidence:[/bold]")
        for e in r.evidence:
            console.print(f"  · {e}")


@eval_app.command("generate")
def eval_generate(
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL path for fixtures."),
    per_code_variants: int = typer.Option(3, help="Fixtures per (dialect, code) KB entry."),
    out_of_kb_count: int = typer.Option(20, help="Fixtures with codes NOT in the KB."),
    adversarial_count: int = typer.Option(10, help="Ambiguous/contradictory fixtures."),
    malformed_count: int = typer.Option(5, help="Missing-dialect or missing-code fixtures."),
    seed: int = typer.Option(42, help="RNG seed for reproducibility."),
) -> None:
    """Generate a synthetic fixture set covering the four fixture archetypes."""
    fixtures = generate_all(
        per_code_variants=per_code_variants,
        out_of_kb_count=out_of_kb_count,
        adversarial_count=adversarial_count,
        malformed_count=malformed_count,
        seed=seed,
    )
    save_fixtures(fixtures, output)
    console.print(f"[green]✓[/green] {summarize_kinds(fixtures)} → {output}")


@eval_app.command("run")
def eval_run(
    fixtures_path: Path = typer.Argument(..., help="JSONL of fixtures."),
    mode: EvalMode = typer.Option(EvalMode.KB_ONLY, help="Eval mode."),
    predictions_out: Path = typer.Option(
        None, "--predictions-out",
        help="If set, save per-fixture predictions to this JSONL for later `eval report`.",
    ),
    sample: int = typer.Option(0, help="If >0, run only this many fixtures (useful for LLM cost)."),
) -> None:
    """Run the pipeline in a given mode over a fixture file and print metrics."""
    fixtures = load_fixtures(fixtures_path)
    if sample > 0:
        fixtures = fixtures[:sample]
    console.print(f"[dim]Running {mode.value} over {summarize_kinds(fixtures)}…[/dim]")
    predictions = run_eval(fixtures, mode)
    if predictions_out:
        save_predictions(predictions, predictions_out)
        console.print(f"[green]✓[/green] Predictions → {predictions_out}")
    metrics = compute_metrics(fixtures, predictions, mode=mode.value)
    format_report(metrics, console)


@eval_app.command("report")
def eval_report(
    fixtures_path: Path = typer.Argument(..., help="JSONL of fixtures."),
    predictions_path: Path = typer.Argument(..., help="JSONL of predictions from a prior `eval run`."),
) -> None:
    """Reprint metrics from a saved predictions file. Handy for regression tracking."""
    fixtures = load_fixtures(fixtures_path)
    predictions = load_predictions(predictions_path)
    metrics = compute_metrics(fixtures, predictions)
    format_report(metrics, console)


@eval_app.command("calibration")
def eval_calibration(
    fixtures_path: Path = typer.Argument(..., help="JSONL of fixtures."),
    predictions_path: Path = typer.Argument(..., help="JSONL of predictions."),
) -> None:
    """Confidence-calibration report per mode: ECE, Brier score, reliability diagram."""
    fixtures = load_fixtures(fixtures_path)
    predictions = load_predictions(predictions_path)
    reports = compute_calibration_per_mode(fixtures, predictions)
    if not reports:
        console.print("[yellow]No predictions found.[/yellow]")
        return
    for r in reports:
        format_calibration(r, console)


def _warn_if_llm_mode_but_no_api_key(mode: EvalMode) -> None:
    import os
    if mode != EvalMode.KB_ONLY and not os.environ.get("ANTHROPIC_API_KEY"):
        console.print(
            "[yellow]WARNING: ANTHROPIC_API_KEY not set. LLM calls will fail on non-KB "
            "fixtures during eval. Latency numbers below reflect KB-only + error-path "
            "timing, NOT real LLM API latency. Cost estimates are still valid — they "
            "use documented token counts, not measured usage.[/yellow]"
        )


@eval_app.command("bench")
def eval_bench(
    fixtures_path: Path = typer.Argument(..., help="JSONL of fixtures."),
    mode: EvalMode = typer.Option(EvalMode.KB_ONLY, help="Eval mode."),
    sample: int = typer.Option(0, help="If >0, run only this many fixtures."),
    llm_model: str = typer.Option("claude-haiku-4-5-20251001"),
    verifier_model: str = typer.Option("claude-sonnet-5"),
) -> None:
    """Measure latency (real) and estimated cost per envelope for one mode."""
    _warn_if_llm_mode_but_no_api_key(mode)
    fixtures = load_fixtures(fixtures_path)
    if sample > 0:
        fixtures = fixtures[:sample]
    predictions = run_eval(fixtures, mode)
    report = compute_bench(
        predictions, mode=mode.value, llm_model=llm_model, verifier_model=verifier_model,
    )
    format_bench(report, console)


@eval_app.command("bench-all")
def eval_bench_all(
    fixtures_path: Path = typer.Argument(..., help="JSONL of fixtures."),
    sample: int = typer.Option(0, help="If >0, run only this many fixtures."),
    llm_model: str = typer.Option("claude-haiku-4-5-20251001"),
    verifier_model: str = typer.Option("claude-sonnet-5"),
) -> None:
    """Bench across all three modes and print the comparison table. The pitch chart."""
    _warn_if_llm_mode_but_no_api_key(EvalMode.WITH_LLM)
    fixtures = load_fixtures(fixtures_path)
    if sample > 0:
        fixtures = fixtures[:sample]
    reports = []
    for m in [EvalMode.KB_ONLY, EvalMode.WITH_LLM, EvalMode.WITH_VERIFIER]:
        try:
            preds = run_eval(fixtures, m)
            reports.append(compute_bench(
                preds, mode=m.value,
                llm_model=llm_model, verifier_model=verifier_model,
            ))
        except Exception as e:
            console.print(f"[yellow]Skipped {m.value}:[/yellow] {e}")
    format_bench_comparison(reports, console)


@ingest_app.command("csv")
def ingest_csv(
    input_path: Path = typer.Argument(..., help="CSV export of audit-trail rows."),
    output: Path = typer.Option(..., "--output", "-o", help="Output JSONL of unlabelled fixtures."),
    dialect: Dialect = typer.Option(..., help="CBA dialect for all envelopes in this file."),
    request_column: str = typer.Option(None, help="Override auto-detected request column."),
    response_column: str = typer.Option(None, help="Override auto-detected response column."),
    method_column: str = typer.Option(None),
    session_column: str = typer.Option(None),
    bank_code_column: str = typer.Option(None),
    limit: int = typer.Option(0, help="Cap rows read (0 = no cap)."),
    redact: bool = typer.Option(True, help="Redact PII before writing fixtures. Requires PAYFLOW_REDACTION_SALT."),
    id_prefix: str = typer.Option("pilot", help="Fixture ID prefix."),
) -> None:
    """Ingest a bank CSV audit-trail export into unlabelled fixtures."""
    redactor = Redactor() if redact else None
    envelopes = list(read_csv_envelopes(
        input_path,
        request_column=request_column,
        response_column=response_column,
        method_column=method_column,
        session_column=session_column,
        bank_code_column=bank_code_column,
        limit=limit if limit > 0 else None,
    ))
    fixtures = envelopes_to_fixtures(
        envelopes, dialect=dialect, id_prefix=id_prefix, redactor=redactor,
    )
    _save_fixtures(fixtures, output)
    console.print(
        f"[green]✓[/green] Ingested {len(fixtures)} fixtures "
        f"({'redacted' if redact else '[red]UNREDACTED[/red]'}) → {output}"
    )


@ingest_app.command("stats")
def ingest_stats(
    fixtures_path: Path = typer.Argument(..., help="Fixture JSONL (labelled or unlabelled)."),
) -> None:
    """Show ingest stats — per-dialect counts, top codes, KB hit rate, top KB misses."""
    from payflow.eval.fixture import load_fixtures
    fixtures = load_fixtures(fixtures_path)
    stats = compute_ingest_stats(fixtures)
    print_ingest_stats(stats, console)


@ingest_app.command("label")
def ingest_label(
    input_path: Path = typer.Argument(..., help="Unlabelled fixtures JSONL."),
    output: Path = typer.Option(..., "--output", "-o", help="Labelled JSONL (resumable)."),
    auto_label_kb_hits: bool = typer.Option(
        True, help="Auto-label fixtures whose (dialect,code) is in the KB."
    ),
) -> None:
    """Interactively label unlabelled fixtures. Resumable across sessions."""
    labelled, remaining = label_fixtures(
        input_path, output, auto_label_kb_hits=auto_label_kb_hits, console=console,
    )
    console.print(
        f"[green]✓[/green] Labelled {labelled} this session; {remaining} still unlabelled in {output}."
    )


@fd_app.command("serve")
def freshdesk_serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8080, help="Bind port."),
) -> None:
    """Run the Freshdesk webhook receiver. Requires the [webhook] extra + env vars."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed. Run: uv sync --extra webhook[/red]")
        raise typer.Exit(1)
    from payflow.integrations.freshdesk.webhook import build_app
    uvicorn.run(build_app(), host=host, port=port)


@fd_app.command("triage")
def freshdesk_triage(
    ticket_path: Path = typer.Argument(..., help="Path to a saved Freshdesk ticket JSON."),
    dialect: Dialect = typer.Option(Dialect.CORE, help="Fallback dialect if no `dialect:` tag."),
    use_llm: bool = typer.Option(False, "--use-llm"),
    verify: bool = typer.Option(False, "--verify"),
) -> None:
    """Offline triage of a saved Freshdesk ticket. Never touches the Freshdesk API."""
    import json as _json

    from payflow.integrations.freshdesk.extract import extract_envelope_from_ticket
    from payflow.integrations.freshdesk.format import format_triage_note

    ticket = _json.loads(ticket_path.read_text())
    envelope = extract_envelope_from_ticket(ticket, default_dialect=dialect)
    if envelope is None:
        console.print("[red]No envelope found in ticket description.[/red]")
        raise typer.Exit(1)
    result = _triage(envelope, load_kb(), use_llm=use_llm, verify=verify)
    console.print(format_triage_note(result))


@zd_app.command("serve")
def zendesk_serve(
    host: str = typer.Option("127.0.0.1", help="Bind host."),
    port: int = typer.Option(8080, help="Bind port."),
) -> None:
    """Run the Zendesk webhook receiver. Requires the [webhook] extra + env vars."""
    try:
        import uvicorn
    except ImportError:
        console.print("[red]uvicorn not installed. Run: uv sync --extra webhook[/red]")
        raise typer.Exit(1)
    from payflow.integrations.zendesk.webhook import build_app
    uvicorn.run(build_app(), host=host, port=port)


@zd_app.command("triage")
def zendesk_triage(
    ticket_path: Path = typer.Argument(..., help="Path to a saved Zendesk ticket JSON."),
    dialect: Dialect = typer.Option(Dialect.CORE, help="Fallback dialect if no `dialect:` tag."),
    use_llm: bool = typer.Option(False, "--use-llm"),
    verify: bool = typer.Option(False, "--verify"),
) -> None:
    """Offline triage of a saved Zendesk ticket. Never touches the Zendesk API."""
    import json as _json

    from payflow.integrations._shared.extract import extract_envelope_from_ticket
    from payflow.integrations._shared.format import format_triage_note

    ticket = _json.loads(ticket_path.read_text())
    envelope = extract_envelope_from_ticket(ticket, default_dialect=dialect)
    if envelope is None:
        console.print("[red]No envelope found in ticket description.[/red]")
        raise typer.Exit(1)
    result = _triage(envelope, load_kb(), use_llm=use_llm, verify=verify)
    console.print(format_triage_note(result))


if __name__ == "__main__":
    app()
