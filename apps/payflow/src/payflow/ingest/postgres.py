"""Postgres reader for a bank's `request_audit_trail` table.

Requires the `ingest` optional dependency group:
    uv sync --extra ingest

Streams via SQLAlchemy Core with `yield_per` so we don't slurp 50GB of CLOBs into memory.
"""
from collections.abc import Iterator
from typing import Optional

from payflow.models import Envelope
from payflow.parser import parse_json, parse_soap


def read_postgres_envelopes(
    dsn: str,
    *,
    table: str = "request_audit_trail",
    request_column: str = "raw_request",
    response_column: str = "raw_response",
    method_column: Optional[str] = "method",
    session_column: Optional[str] = "session_id",
    where: Optional[str] = None,
    limit: Optional[int] = None,
    chunk_size: int = 500,
) -> Iterator[Envelope]:
    """Stream envelopes from Postgres. Yields one Envelope per row.

    `where` is a raw SQL predicate appended after WHERE, e.g. "created_at > '2026-06-01'".
    """
    try:
        from sqlalchemy import create_engine, text
    except ImportError as e:
        raise ImportError(
            "SQLAlchemy required for Postgres ingest. Install with: uv sync --extra ingest"
        ) from e

    cols: list[str] = [request_column, response_column]
    if method_column:
        cols.append(method_column)
    if session_column:
        cols.append(session_column)

    sql = f"SELECT {', '.join(cols)} FROM {table}"
    if where:
        sql += f" WHERE {where}"
    if limit:
        sql += f" LIMIT {limit}"

    engine = create_engine(dsn)
    with engine.connect() as conn:
        result = conn.execution_options(stream_results=True).execute(text(sql))
        for row in result.yield_per(chunk_size).mappings():
            env = Envelope(source="audit_trail")
            req = (row.get(request_column) or "").strip()
            res = (row.get(response_column) or "").strip()

            if req:
                parsed = parse_soap(req) if req.startswith("<") else parse_json(req)
                for f_ in ("session_id", "transaction_id", "method", "amount",
                           "source_account", "dest_account", "dest_bank_code", "narration"):
                    val = getattr(parsed, f_, None)
                    if val is not None:
                        setattr(env, f_, val)
                env.raw_request = req

            if res:
                parsed = parse_soap(res) if res.startswith("<") else parse_json(res)
                if parsed.response_code:
                    env.response_code = parsed.response_code
                if parsed.response_message:
                    env.response_message = parsed.response_message
                env.raw_response = res

            if method_column and (v := row.get(method_column)):
                env.method = env.method or str(v).strip()
            if session_column and (v := row.get(session_column)):
                env.session_id = env.session_id or str(v).strip()

            yield env
