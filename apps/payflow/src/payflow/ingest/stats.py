from collections import Counter
from typing import Optional

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

from payflow.eval.fixture import Fixture
from payflow.kb import KB, load_kb, lookup


class IngestStats(BaseModel):
    total: int
    labelled: int
    unlabelled: int
    per_dialect: dict[str, int]
    per_kind: dict[str, int]
    top_response_codes: list[tuple[str, int]]
    kb_hit_rate: float
    kb_misses_top: list[tuple[str, int]]
    missing_response_code: int
    missing_dialect: int


def compute_ingest_stats(
    fixtures: list[Fixture],
    kb: Optional[KB] = None,
) -> IngestStats:
    kb = kb or load_kb()

    per_dialect = Counter(fx.dialect.value if fx.dialect else "<none>" for fx in fixtures)
    per_kind = Counter(fx.kind.value for fx in fixtures)

    codes = Counter(fx.source_code for fx in fixtures if fx.source_code)
    top_codes = codes.most_common(20)

    kb_hits = 0
    kb_misses: Counter = Counter()
    for fx in fixtures:
        if fx.dialect is None or fx.source_code is None:
            continue
        if lookup(kb, fx.dialect, fx.source_code) is not None:
            kb_hits += 1
        else:
            kb_misses[(fx.dialect.value, fx.source_code)] += 1

    triageable = sum(1 for fx in fixtures if fx.dialect and fx.source_code)
    kb_hit_rate = kb_hits / triageable if triageable else 0.0
    top_misses = [(f"{d},{c}", n) for (d, c), n in kb_misses.most_common(20)]

    return IngestStats(
        total=len(fixtures),
        labelled=sum(1 for fx in fixtures if fx.is_labelled and fx.expected_retry_strategy is not None),
        unlabelled=sum(1 for fx in fixtures if not fx.is_labelled or fx.expected_retry_strategy is None),
        per_dialect=dict(per_dialect),
        per_kind=dict(per_kind),
        top_response_codes=top_codes,
        kb_hit_rate=kb_hit_rate,
        kb_misses_top=top_misses,
        missing_response_code=sum(1 for fx in fixtures if not fx.source_code),
        missing_dialect=sum(1 for fx in fixtures if fx.dialect is None),
    )


def print_ingest_stats(stats: IngestStats, console: Optional[Console] = None) -> None:
    console = console or Console()
    console.rule("[bold]Ingest stats")

    top = Table.grid(padding=(0, 2))
    top.add_column(style="bold")
    top.add_column()
    top.add_row("Total fixtures:", str(stats.total))
    top.add_row("Labelled:", str(stats.labelled))
    top.add_row("Unlabelled:", str(stats.unlabelled))
    top.add_row("KB hit rate:", f"{stats.kb_hit_rate:.1%}  (deterministic-triage coverage before LLM)")
    top.add_row("Missing response code:", str(stats.missing_response_code))
    top.add_row("Missing dialect:", str(stats.missing_dialect))
    console.print(top)

    td = Table(title="Per dialect")
    td.add_column("Dialect", style="cyan")
    td.add_column("Count", justify="right")
    for d, n in sorted(stats.per_dialect.items(), key=lambda x: -x[1]):
        td.add_row(d, str(n))
    console.print(td)

    tk = Table(title="Per kind")
    tk.add_column("Kind", style="cyan")
    tk.add_column("Count", justify="right")
    for k, n in sorted(stats.per_kind.items(), key=lambda x: -x[1]):
        tk.add_row(k, str(n))
    console.print(tk)

    if stats.top_response_codes:
        tc = Table(title="Top 20 response codes seen")
        tc.add_column("Code", style="cyan")
        tc.add_column("Count", justify="right")
        for code, n in stats.top_response_codes:
            tc.add_row(code, str(n))
        console.print(tc)

    if stats.kb_misses_top:
        tm = Table(title="Top 20 KB misses (dialect,code) — priority list for KB curation")
        tm.add_column("(dialect,code)", style="yellow")
        tm.add_column("Count", justify="right")
        for k, n in stats.kb_misses_top:
            tm.add_row(k, str(n))
        console.print(tm)
