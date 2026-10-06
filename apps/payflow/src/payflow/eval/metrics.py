from collections import Counter
from typing import Iterable, Optional

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from payflow.eval.fixture import Fixture, FixtureKind, Prediction
from payflow.models import Retryability

# Predicting these two "risks retry" when the truth is "do not retry" is what causes double-debits.
_RISKS_RETRY = {Retryability.IMMEDIATE, Retryability.BACKOFF}
# Predicting NEVER when the truth is STATUS_QUERY loses recoverable money.
_TERMINAL = Retryability.NEVER


class PerStrategyMetrics(BaseModel):
    strategy: Retryability
    support: int = Field(..., description="How many fixtures had this as ground truth.")
    predicted: int = Field(..., description="How many predictions used this strategy.")
    tp: int
    fp: int
    fn: int
    precision: float
    recall: float
    f1: float


class Metrics(BaseModel):
    mode: str
    total: int
    correct: int
    accuracy: float
    errors: int
    per_strategy: list[PerStrategyMetrics]
    per_kind_accuracy: dict[str, float]
    confusion: dict[str, dict[str, int]] = Field(
        ..., description="Rows = actual, cols = predicted."
    )
    false_immediate_retry_rate: float = Field(
        ...,
        description="Predicted immediate/backoff when actual was status_query/never. "
        "This IS the double-debit risk metric. Target = 0.",
    )
    false_terminal_rate: float = Field(
        ...,
        description="Predicted never when actual was status_query. False negative that "
        "loses recoverable customer money. Target = 0.",
    )
    unknown_predictions: int = Field(
        0, description="Predictions where confidence was 'low' — routed to human ops."
    )


def _index_fixtures(fixtures: Iterable[Fixture]) -> dict[str, Fixture]:
    return {fx.id: fx for fx in fixtures}


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    prec = tp / (tp + fp) if (tp + fp) else 0.0
    rec = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) else 0.0
    return prec, rec, f1


def compute_metrics(
    fixtures: list[Fixture],
    predictions: list[Prediction],
    mode: Optional[str] = None,
) -> Metrics:
    by_id = _index_fixtures(fixtures)
    matched: list[tuple[Fixture, Prediction]] = []
    for p in predictions:
        fx = by_id.get(p.fixture_id)
        if fx is None:
            continue
        # Unlabelled fixtures cannot be scored — silently skip. `payflow ingest stats`
        # is the tool for inspecting them; `payflow ingest label` is the tool for labelling.
        if not fx.is_labelled or fx.expected_retry_strategy is None:
            continue
        matched.append((fx, p))

    total = len(matched)
    errors = sum(1 for _, p in matched if p.error is not None)
    correct = sum(1 for fx, p in matched if fx.expected_retry_strategy == p.predicted_retry_strategy)
    accuracy = correct / total if total else 0.0

    # Confusion matrix (actual → predicted counts)
    strategies = [s for s in Retryability]
    confusion = {a.value: {b.value: 0 for b in strategies} for a in strategies}
    for fx, p in matched:
        confusion[fx.expected_retry_strategy.value][p.predicted_retry_strategy.value] += 1

    per_strategy: list[PerStrategyMetrics] = []
    for s in strategies:
        support = sum(1 for fx, _ in matched if fx.expected_retry_strategy == s)
        predicted = sum(1 for _, p in matched if p.predicted_retry_strategy == s)
        tp = sum(
            1
            for fx, p in matched
            if fx.expected_retry_strategy == s and p.predicted_retry_strategy == s
        )
        fp = predicted - tp
        fn = support - tp
        prec, rec, f1 = _prf(tp, fp, fn)
        per_strategy.append(PerStrategyMetrics(
            strategy=s, support=support, predicted=predicted,
            tp=tp, fp=fp, fn=fn, precision=prec, recall=rec, f1=f1,
        ))

    # Per-kind accuracy: how well does the pipeline do on each fixture archetype?
    per_kind: dict[str, tuple[int, int]] = {}
    for fx, p in matched:
        c, t = per_kind.get(fx.kind.value, (0, 0))
        per_kind[fx.kind.value] = (
            c + int(fx.expected_retry_strategy == p.predicted_retry_strategy),
            t + 1,
        )
    per_kind_accuracy = {k: (c / t if t else 0.0) for k, (c, t) in per_kind.items()}

    # The two safety metrics.
    conservative_expected = sum(
        1
        for fx, _ in matched
        if fx.expected_retry_strategy in (Retryability.STATUS_QUERY, Retryability.NEVER)
    )
    false_retries = sum(
        1
        for fx, p in matched
        if fx.expected_retry_strategy in (Retryability.STATUS_QUERY, Retryability.NEVER)
        and p.predicted_retry_strategy in _RISKS_RETRY
    )
    fir = false_retries / conservative_expected if conservative_expected else 0.0

    status_query_expected = sum(
        1 for fx, _ in matched if fx.expected_retry_strategy == Retryability.STATUS_QUERY
    )
    false_terminals = sum(
        1
        for fx, p in matched
        if fx.expected_retry_strategy == Retryability.STATUS_QUERY
        and p.predicted_retry_strategy == _TERMINAL
    )
    fter = false_terminals / status_query_expected if status_query_expected else 0.0

    unknown = sum(1 for _, p in matched if p.predicted_confidence == "low")

    resolved_mode = mode or (matched[0][1].mode if matched else "unknown")
    return Metrics(
        mode=resolved_mode,
        total=total,
        correct=correct,
        accuracy=accuracy,
        errors=errors,
        per_strategy=per_strategy,
        per_kind_accuracy=per_kind_accuracy,
        confusion=confusion,
        false_immediate_retry_rate=fir,
        false_terminal_rate=fter,
        unknown_predictions=unknown,
    )


def format_report(m: Metrics, console: Optional[Console] = None) -> None:
    console = console or Console()
    console.rule(f"[bold]Payflow eval — mode: [cyan]{m.mode}[/cyan]")

    top = Table.grid(padding=(0, 2))
    top.add_column(style="bold")
    top.add_column()
    top.add_row("Total fixtures:", str(m.total))
    top.add_row("Correct:", f"{m.correct} ({m.accuracy:.1%})")
    top.add_row("Errors:", str(m.errors))
    top.add_row("Low-confidence (routed to ops):", str(m.unknown_predictions))
    top.add_row(
        "[red]False-immediate-retry rate:[/red]",
        f"[red bold]{m.false_immediate_retry_rate:.2%}[/red bold]  ← double-debit risk. Target = 0.",
    )
    top.add_row(
        "[yellow]False-terminal rate:[/yellow]",
        f"[yellow bold]{m.false_terminal_rate:.2%}[/yellow bold]  ← lost-recovery risk. Target = 0.",
    )
    console.print(top)

    tk = Table(title="Accuracy by fixture kind")
    tk.add_column("Kind", style="cyan")
    tk.add_column("Accuracy", justify="right")
    for k in [FixtureKind.IN_KB, FixtureKind.OUT_OF_KB, FixtureKind.ADVERSARIAL, FixtureKind.MALFORMED]:
        if k.value in m.per_kind_accuracy:
            tk.add_row(k.value, f"{m.per_kind_accuracy[k.value]:.1%}")
    console.print(tk)

    ts = Table(title="Per-strategy P/R/F1")
    ts.add_column("Strategy", style="cyan")
    ts.add_column("Support", justify="right")
    ts.add_column("Precision", justify="right")
    ts.add_column("Recall", justify="right")
    ts.add_column("F1", justify="right")
    for s in m.per_strategy:
        if s.support == 0 and s.predicted == 0:
            continue
        ts.add_row(
            s.strategy.value, str(s.support),
            f"{s.precision:.2f}", f"{s.recall:.2f}", f"{s.f1:.2f}",
        )
    console.print(ts)

    tc = Table(title="Confusion matrix (rows=actual, cols=predicted)")
    tc.add_column("actual ↓ / pred →", style="cyan")
    strategies = [s.value for s in Retryability]
    for s in strategies:
        tc.add_column(s, justify="right")
    for a in strategies:
        row = [a]
        for p in strategies:
            v = m.confusion[a][p]
            if a == p and v > 0:
                row.append(f"[green]{v}[/green]")
            elif a != p and v > 0:
                row.append(f"[red]{v}[/red]")
            else:
                row.append("·")
        tc.add_row(*row)
    console.print(tc)


def summarize_kinds(fixtures: list[Fixture]) -> str:
    counts = Counter(fx.kind.value for fx in fixtures)
    parts = [f"{k}={counts.get(k, 0)}" for k in ["in_kb", "out_of_kb", "adversarial", "malformed"]]
    return f"{len(fixtures)} fixtures ({', '.join(parts)})"
