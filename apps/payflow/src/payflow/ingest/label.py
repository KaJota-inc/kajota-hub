from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from payflow.eval.fixture import Fixture, load_fixtures
from payflow.kb import KB, load_kb, lookup
from payflow.models import Retryability

_KEY_TO_STRATEGY: dict[str, Retryability] = {
    "i": Retryability.IMMEDIATE,
    "b": Retryability.BACKOFF,
    "s": Retryability.STATUS_QUERY,
    "r": Retryability.REVERSAL,
    "n": Retryability.NEVER,
}

_SKIP = "/"
_QUIT = "q"


def label_fixtures(
    input_path: str | Path,
    output_path: str | Path,
    *,
    kb: Optional[KB] = None,
    console: Optional[Console] = None,
    auto_label_kb_hits: bool = True,
    prompt: Optional[Callable[[str], str]] = None,
) -> tuple[int, int]:
    """Interactively label an unlabelled fixture file, resumable across sessions.

    Reads input JSONL; writes labelled fixtures to output as we go (safe to Ctrl-C).
    Already-labelled IDs in the output file are skipped so you can pick up where you left off.

    Returns (labelled_this_session, remaining_unlabelled).
    """
    kb = kb or load_kb()
    console = console or Console()
    prompt = prompt or (lambda msg: Prompt.ask(msg, default=_SKIP))

    input_path = Path(input_path)
    output_path = Path(output_path)

    fixtures = load_fixtures(input_path)
    already_labelled_ids: set[str] = set()
    if output_path.exists():
        for fx in load_fixtures(output_path):
            if fx.is_labelled and fx.expected_retry_strategy is not None:
                already_labelled_ids.add(fx.id)
        console.print(f"[dim]Resuming — {len(already_labelled_ids)} already labelled in {output_path}[/dim]")

    labelled_count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if output_path.exists() else "w"

    with output_path.open(mode) as out:
        for fx in fixtures:
            if fx.id in already_labelled_ids:
                continue
            if fx.is_labelled and fx.expected_retry_strategy is not None:
                out.write(fx.model_dump_json() + "\n")
                out.flush()
                continue

            _render_fixture(fx, kb, console, auto_label_kb_hits)

            if auto_label_kb_hits and _kb_hit(fx, kb):
                entry = lookup(kb, fx.dialect, fx.source_code)
                assert entry is not None
                labelled = fx.model_copy(update={
                    "expected_retry_strategy": entry.retry,
                    "expected_category": entry.category,
                    "expected_retryable": entry.retry != Retryability.NEVER,
                    "is_labelled": True,
                    "notes": (fx.notes + " | auto-labelled from KB").strip(" |"),
                })
                out.write(labelled.model_dump_json() + "\n")
                out.flush()
                labelled_count += 1
                continue

            key = _ask_for_label(prompt)
            if key == _QUIT:
                console.print("[yellow]Quit — remaining unlabelled fixtures were left in the input file.[/yellow]")
                break
            if key == _SKIP:
                out.write(fx.model_dump_json() + "\n")
                out.flush()
                continue

            strategy = _KEY_TO_STRATEGY[key]
            labelled = fx.model_copy(update={
                "expected_retry_strategy": strategy,
                "expected_retryable": strategy != Retryability.NEVER,
                "is_labelled": True,
            })
            out.write(labelled.model_dump_json() + "\n")
            out.flush()
            labelled_count += 1

    remaining = sum(1 for fx in load_fixtures(output_path) if not fx.is_labelled)
    return labelled_count, remaining


def _kb_hit(fx: Fixture, kb: KB) -> bool:
    if fx.dialect is None or fx.source_code is None:
        return False
    return lookup(kb, fx.dialect, fx.source_code) is not None


def _render_fixture(fx: Fixture, kb: KB, console: Console, auto: bool) -> None:
    lines: list[str] = []
    lines.append(f"[bold]id:[/bold] {fx.id}")
    lines.append(f"[bold]kind:[/bold] {fx.kind.value}")
    lines.append(f"[bold]dialect:[/bold] {fx.dialect.value if fx.dialect else '[red]<none>[/red]'}")
    lines.append(f"[bold]source_code:[/bold] {fx.source_code or '[red]<none>[/red]'}")
    lines.append(f"[bold]notes:[/bold] {fx.notes}")
    if fx.dialect and fx.source_code:
        entry = lookup(kb, fx.dialect, fx.source_code)
        if entry is not None:
            hit_line = (
                f"[green]KB HIT:[/green] {entry.raw_message} → "
                f"category={entry.category.value}, retry={entry.retry.value}"
            )
            if auto:
                hit_line += " [dim](auto-labelling)[/dim]"
            lines.append(hit_line)
        else:
            lines.append(f"[yellow]KB MISS:[/yellow] {fx.dialect.value},{fx.source_code} not in KB")
    console.print(Panel("\n".join(lines), title=fx.id, expand=False))


def _ask_for_label(prompt: Callable[[str], str]) -> str:
    key = prompt(
        "Label? [i]mmediate [b]ackoff [s]tatus_query [r]eversal [n]ever [/]skip [q]uit"
    ).strip().lower()
    while key not in _KEY_TO_STRATEGY and key not in (_SKIP, _QUIT):
        key = prompt("Invalid. i/b/s/r/n/// (skip) /q (quit)").strip().lower()
    return key


def iterate_fixtures(fixtures: Iterable[Fixture], skip_labelled: bool = True) -> Iterable[Fixture]:
    for fx in fixtures:
        if skip_labelled and fx.is_labelled and fx.expected_retry_strategy is not None:
            continue
        yield fx
