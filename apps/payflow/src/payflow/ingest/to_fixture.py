from collections.abc import Iterable
from typing import Optional

from payflow.eval.fixture import Fixture, FixtureKind
from payflow.ingest.redact import Redactor
from payflow.models import Dialect, Envelope


def envelope_to_fixture(
    env: Envelope,
    *,
    idx: int,
    dialect: Optional[Dialect] = None,
    kind: FixtureKind = FixtureKind.OUT_OF_KB,
    id_prefix: str = "pilot",
    redactor: Optional[Redactor] = None,
) -> Fixture:
    """Convert a real (or synthetic) Envelope into an unlabelled Fixture.

    Ground truth is None — pilot data must be labelled through the ops flow
    (`payflow ingest label`) before it counts toward eval metrics.
    """
    content = env.raw_response or env.raw_request or ""
    fmt = "soap" if content.lstrip().startswith("<") else "json" if content.lstrip().startswith("{") else "audit_trail"

    if redactor is not None and content:
        content = redactor.envelope_content(content)

    return Fixture(
        id=f"{id_prefix}-{idx:06d}",
        kind=kind,
        envelope_format=fmt,
        envelope_content=content,
        dialect=dialect if dialect is not None else env.dialect,
        expected_retry_strategy=None,
        expected_category=None,
        expected_retryable=None,
        expected_confidence_min="low",
        is_labelled=False,
        source_code=env.response_code,
        notes=(
            f"Pilot ingest. method={env.method!r}, response_code={env.response_code!r}, "
            f"response_message={env.response_message!r}"
        ),
    )


def envelopes_to_fixtures(
    envelopes: Iterable[Envelope],
    *,
    dialect: Optional[Dialect] = None,
    kind: FixtureKind = FixtureKind.OUT_OF_KB,
    id_prefix: str = "pilot",
    redactor: Optional[Redactor] = None,
    start_idx: int = 0,
) -> list[Fixture]:
    return [
        envelope_to_fixture(
            env, idx=start_idx + i, dialect=dialect,
            kind=kind, id_prefix=id_prefix, redactor=redactor,
        )
        for i, env in enumerate(envelopes)
    ]
