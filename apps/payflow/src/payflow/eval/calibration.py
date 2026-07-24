from collections import defaultdict
from typing import Optional

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

from payflow.eval.fixture import Fixture, Prediction

# Default mapping from discrete confidence labels to prior probabilities.
# The pilot loop refines these against real ex-post ops labels.
DEFAULT_CONFIDENCE_PRIORS: dict[str, float] = {
    "high":   0.95,
    "medium": 0.80,
    "low":    0.50,
}

_BAR_WIDTH = 20


class CalibrationBucket(BaseModel):
    confidence: str
    predicted_probability: float = Field(..., description="Prior for this confidence label.")
    observed_accuracy: float
    support: int
    correct: int


class CalibrationReport(BaseModel):
    mode: str
    total: int
    total_correct: int
    buckets: list[CalibrationBucket]
    ece: float = Field(..., description="Expected Calibration Error. Lower is better; perfect = 0.")
    brier_score: float = Field(..., description="Mean squared error on 0/1 correctness. Lower is better.")
    overconfident: list[str] = Field(default_factory=list, description="Buckets where observed < predicted.")
    underconfident: list[str] = Field(default_factory=list, description="Buckets where observed > predicted.")


def compute_calibration(
    fixtures: list[Fixture],
    predictions: list[Prediction],
    *,
    mode: Optional[str] = None,
    confidence_priors: Optional[dict[str, float]] = None,
    overconfidence_threshold: float = 0.05,
) -> CalibrationReport:
    """Compute a calibration report over labelled (fixture, prediction) pairs.

    Unlabelled fixtures are skipped — same convention as `compute_metrics`.
    `mode` restricts to a single eval mode; if None, uses the mode from the first prediction.
    """
    priors = confidence_priors or DEFAULT_CONFIDENCE_PRIORS
    by_id = {fx.id: fx for fx in fixtures}

    per_bucket: dict[str, list[bool]] = defaultdict(list)
    resolved_mode = mode
    correctness_pairs: list[tuple[float, int]] = []

    for p in predictions:
        if mode is not None and p.mode != mode:
            continue
        if resolved_mode is None:
            resolved_mode = p.mode
        fx = by_id.get(p.fixture_id)
        if fx is None or not fx.is_labelled or fx.expected_retry_strategy is None:
            continue
        correct = fx.expected_retry_strategy == p.predicted_retry_strategy
        per_bucket[p.predicted_confidence].append(correct)
        correctness_pairs.append((priors.get(p.predicted_confidence, 0.5), 1 if correct else 0))

    buckets: list[CalibrationBucket] = []
    total = 0
    total_correct = 0
    weighted_gap = 0.0
    overconfident: list[str] = []
    underconfident: list[str] = []

    for confidence_label, hits in per_bucket.items():
        support = len(hits)
        correct = sum(hits)
        observed = correct / support if support else 0.0
        prior = priors.get(confidence_label, 0.5)
        buckets.append(CalibrationBucket(
            confidence=confidence_label,
            predicted_probability=prior,
            observed_accuracy=observed,
            support=support,
            correct=correct,
        ))
        total += support
        total_correct += correct
        weighted_gap += (support * abs(observed - prior))
        gap = observed - prior
        if gap < -overconfidence_threshold:
            overconfident.append(confidence_label)
        elif gap > overconfidence_threshold:
            underconfident.append(confidence_label)

    ece = (weighted_gap / total) if total else 0.0
    brier = (
        sum((prob - actual) ** 2 for prob, actual in correctness_pairs) / len(correctness_pairs)
        if correctness_pairs else 0.0
    )

    # Order buckets by prior probability descending for readability.
    buckets.sort(key=lambda b: -b.predicted_probability)

    return CalibrationReport(
        mode=resolved_mode or "unknown",
        total=total,
        total_correct=total_correct,
        buckets=buckets,
        ece=ece,
        brier_score=brier,
        overconfident=overconfident,
        underconfident=underconfident,
    )


def format_calibration(report: CalibrationReport, console: Optional[Console] = None) -> None:
    console = console or Console()
    console.rule(f"[bold]Calibration — mode: [cyan]{report.mode}[/cyan]")

    top = Table.grid(padding=(0, 2))
    top.add_column(style="bold")
    top.add_column()
    top.add_row("Total labelled predictions:", str(report.total))
    top.add_row("Correct:", f"{report.total_correct}")
    top.add_row(
        "Expected Calibration Error (ECE):",
        f"{report.ece:.4f}   [dim](lower is better; 0 = perfect)[/dim]",
    )
    top.add_row(
        "Brier score:",
        f"{report.brier_score:.4f}   [dim](0 = perfect, 0.25 = uninformed coin flip)[/dim]",
    )
    console.print(top)

    tab = Table(title="Reliability diagram")
    tab.add_column("Confidence", style="cyan")
    tab.add_column("Support", justify="right")
    tab.add_column("Correct", justify="right")
    tab.add_column("Predicted p", justify="right")
    tab.add_column("Observed acc.", justify="right")
    tab.add_column("Gap", justify="right")
    tab.add_column(f"Bar (observed, width={_BAR_WIDTH})")
    for b in report.buckets:
        gap = b.observed_accuracy - b.predicted_probability
        gap_str = f"{gap:+.2f}"
        if gap < -0.05:
            gap_str = f"[red]{gap_str}[/red] (overconf.)"
        elif gap > 0.05:
            gap_str = f"[yellow]{gap_str}[/yellow] (underconf.)"
        bar = _ascii_bar(b.observed_accuracy)
        tab.add_row(
            b.confidence,
            str(b.support),
            str(b.correct),
            f"{b.predicted_probability:.2f}",
            f"{b.observed_accuracy:.2f}",
            gap_str,
            bar,
        )
    console.print(tab)

    if report.overconfident:
        console.print(
            f"[red]Overconfident buckets:[/red] {', '.join(report.overconfident)} "
            "— predictions in these buckets are wrong more often than the prior claims. "
            "Consider lowering the prior or triggering a re-triage upstream."
        )
    if report.underconfident:
        console.print(
            f"[yellow]Underconfident buckets:[/yellow] {', '.join(report.underconfident)} "
            "— predictions are more accurate than the prior claims. "
            "You can safely act on these with less human review."
        )
    if not (report.overconfident or report.underconfident):
        console.print("[green]All buckets within ±0.05 of prior — well calibrated.[/green]")


def _ascii_bar(fraction: float, width: int = _BAR_WIDTH) -> str:
    filled = int(round(max(0.0, min(1.0, fraction)) * width))
    return f"{'█' * filled}{'░' * (width - filled)} {fraction * 100:5.1f}%"


def compute_calibration_per_mode(
    fixtures: list[Fixture],
    predictions: list[Prediction],
    *,
    confidence_priors: Optional[dict[str, float]] = None,
) -> list[CalibrationReport]:
    """Split predictions by mode and produce one CalibrationReport per unique mode."""
    modes = {p.mode for p in predictions}
    return [
        compute_calibration(fixtures, predictions, mode=m, confidence_priors=confidence_priors)
        for m in sorted(modes)
    ]
