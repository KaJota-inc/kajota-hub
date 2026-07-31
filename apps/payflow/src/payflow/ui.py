"""Local demo UI — one page, one form, live triage.

Runs at `payflow ui` on localhost. Designed for pilot pitch screenshares where a
terminal + rich tables doesn't play as well to a non-technical decision-maker.
Single self-contained HTML page, no template engine dep, no client-side framework.

Deliberately minimal: paste an envelope, pick a dialect, hit Triage. The page
re-renders with the same private-note markdown that would land on a real ticket,
plus a small dashboard card with the baseline eval numbers.
"""
import base64
import csv
import io
from collections import Counter
from typing import Optional

from payflow.ingest.csv_reader import read_csv_envelopes_from_stream
from payflow.integrations._shared.format import format_triage_note
from payflow.kb import load_kb
from payflow.models import Dialect, TriageResult
from payflow.parser import parse_json, parse_soap
from payflow.triage import triage as _triage

_SAMPLE_IN_KB = """<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://nibss.com/nip/">
  <soap:Body>
    <ns:FundsTransferResponse>
      <SessionID>099999123456789012345678900</SessionID>
      <BeneficiaryAccountNumber>0123456789</BeneficiaryAccountNumber>
      <Amount>150000.00</Amount>
      <ResponseCode>7704</ResponseCode>
      <ResponseMessage>Insufficient Funds</ResponseMessage>
    </ns:FundsTransferResponse>
  </soap:Body>
</soap:Envelope>"""

_SAMPLE_TIMEOUT = """<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://nibss.com/nip/">
  <soap:Body>
    <ns:FundsTransferResponse>
      <SessionID>099999888777666555444333222</SessionID>
      <Amount>50000.00</Amount>
      <ResponseCode>X03B</ResponseCode>
      <ResponseMessage>Response Wait Timeout</ResponseMessage>
    </ns:FundsTransferResponse>
  </soap:Body>
</soap:Envelope>"""

_SAMPLE_OUT_OF_KB = """<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://nibss.com/nip/">
  <soap:Body>
    <ns:FundsTransferResponse>
      <SessionID>099998888777666555444333111</SessionID>
      <Amount>25000.00</Amount>
      <ResponseCode>ZZ99</ResponseCode>
      <ResponseMessage>Unknown Bank Response</ResponseMessage>
    </ns:FundsTransferResponse>
  </soap:Body>
</soap:Envelope>"""


def build_app():
    """Build the FastAPI app. Kept lazy so importing this module doesn't need FastAPI."""
    try:
        from fastapi import FastAPI, File, Form, UploadFile
        from fastapi.responses import HTMLResponse
    except ImportError as e:
        raise ImportError(
            "FastAPI required for UI. Install with: uv sync --extra webhook"
        ) from e

    kb = load_kb()
    app = FastAPI(title="Payflow — NIP Triage Demo", version="0.1")

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return _render_page(result=None, error=None, envelope="", dialect=Dialect.CORE)

    @app.post("/triage", response_class=HTMLResponse)
    async def triage_action(
        envelope: str = Form(...),
        dialect: str = Form(...),
    ) -> str:
        try:
            dialect_enum = Dialect(dialect)
        except ValueError:
            return _render_page(
                result=None, error=f"Invalid dialect: {dialect}",
                envelope=envelope, dialect=Dialect.CORE,
            )
        try:
            env = _parse_envelope(envelope)
        except Exception as e:
            return _render_page(
                result=None, error=f"Parse error: {e}",
                envelope=envelope, dialect=dialect_enum,
            )
        env.dialect = dialect_enum
        result = _triage(env, kb)
        return _render_page(result=result, error=None, envelope=envelope, dialect=dialect_enum)

    @app.get("/batch", response_class=HTMLResponse)
    def batch_page() -> str:
        return _render_batch_page(rows=None, summary=None, error=None, dialect=Dialect.CORE)

    @app.post("/batch", response_class=HTMLResponse)
    async def batch_action(
        csv: UploadFile = File(...),
        dialect: str = Form(...),
    ) -> str:
        try:
            dialect_enum = Dialect(dialect)
        except ValueError:
            return _render_batch_page(rows=None, summary=None,
                                      error=f"Invalid dialect: {dialect}", dialect=Dialect.CORE)
        try:
            raw = await csv.read()
            text = raw.decode("utf-8", errors="replace")
            envelopes = list(read_csv_envelopes_from_stream(io.StringIO(text)))
        except Exception as e:
            return _render_batch_page(rows=None, summary=None,
                                      error=f"CSV parse error: {e}", dialect=dialect_enum)

        rows, summary = _triage_batch(envelopes, dialect_enum, kb)
        return _render_batch_page(rows=rows, summary=summary, error=None, dialect=dialect_enum)

    return app


def _triage_batch(envelopes, dialect: Dialect, kb) -> tuple[list[dict], dict]:
    """Triage each envelope with the given dialect. Returns (rows, summary)."""
    rows: list[dict] = []
    strategy_counts: Counter = Counter()
    confidence_counts: Counter = Counter()
    kb_hits = 0
    for env in envelopes:
        env.dialect = dialect
        try:
            result = _triage(env, kb)
        except Exception as e:
            rows.append({
                "session_short": _short_session(env.session_id),
                "session_full": env.session_id or "",
                "code": env.response_code or "—",
                "strategy": "error",
                "confidence": "error",
                "cause": f"triage failed: {e}",
                "action": f"triage failed: {e}",
                "customer_message": "",
                "kb_hit": False,
            })
            continue
        kb_hit = result.matched_code is not None
        if kb_hit:
            kb_hits += 1
        strategy_counts[result.retry_strategy.value] += 1
        confidence_counts[result.confidence] += 1
        rows.append({
            "session_short": _short_session(env.session_id),
            "session_full": env.session_id or "",
            "code": env.response_code or "—",
            "strategy": result.retry_strategy.value,
            "confidence": result.confidence,
            "cause": result.cause,
            "action": result.action,
            "customer_message": result.matched_code.customer_message if result.matched_code else "",
            "kb_hit": kb_hit,
        })
    total = len(rows) or 1  # avoid /0
    summary = {
        "total": len(rows),
        "kb_hits": kb_hits,
        "kb_hit_pct": f"{kb_hits / total * 100:.1f}%",
        "by_strategy": dict(strategy_counts),
        "by_confidence": dict(confidence_counts),
    }
    return rows, summary


def _rows_to_csv_data_url(rows: list[dict]) -> str:
    """Produce a data: URL the browser downloads on click."""
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=[
        "session", "code", "layer", "retry_strategy", "confidence",
        "cause", "action", "customer_message",
    ])
    writer.writeheader()
    for r in rows:
        writer.writerow({
            "session": r.get("session_full", ""),
            "code": r.get("code", ""),
            "layer": "KB" if r.get("kb_hit") else "",
            "retry_strategy": r.get("strategy", ""),
            "confidence": r.get("confidence", ""),
            "cause": r.get("cause", ""),
            "action": r.get("action", ""),
            "customer_message": r.get("customer_message", ""),
        })
    b64 = base64.b64encode(buf.getvalue().encode()).decode()
    return f"data:text/csv;base64,{b64}"


def _short_session(s: Optional[str]) -> str:
    """Show only the last 6 chars — session IDs are transaction IDs, not PII, but
    truncating avoids cluttering the UI with 25-digit strings."""
    if not s:
        return "—"
    return f"…{s[-6:]}" if len(s) > 6 else s


def _parse_envelope(text: str):
    stripped = text.strip()
    if not stripped:
        raise ValueError("envelope is empty")
    if stripped.startswith("<"):
        return parse_soap(stripped)
    if stripped.startswith("{"):
        return parse_json(stripped)
    raise ValueError("envelope must be XML (start with <) or JSON (start with {)")


def _render_page(
    result: Optional[TriageResult],
    error: Optional[str],
    envelope: str,
    dialect: Dialect,
) -> str:
    result_html = _render_result(result) if result else ""
    error_html = f'<div class="error">{_escape(error)}</div>' if error else ""
    envelope_escaped = _escape(envelope)
    dialect_options = _render_dialect_options(dialect)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Payflow — NIP Triage Demo</title>
  <style>{_CSS}</style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>Payflow</h1>
      <p class="tagline">NIP payment-ops triage · deterministic KB → LLM fallback → adversarial verifier</p>
    </div>
    <aside class="stats">
      <div class="stat"><div class="num">96.1%</div><div class="lbl">Accuracy<br><span>380 fixtures</span></div></div>
      <div class="stat"><div class="num">0.00%</div><div class="lbl">False-immediate<br><span>retry rate</span></div></div>
      <div class="stat"><div class="num">0.03ms</div><div class="lbl">p50 latency<br><span>deterministic</span></div></div>
      <div class="stat"><div class="num">$0.14/1k</div><div class="lbl">Gemini cached<br><span>LLM tail cost</span></div></div>
    </aside>
  </header>
  <nav class="tabs">
    <a href="/" class="tab active">Single envelope</a>
    <a href="/batch" class="tab">Batch CSV</a>
  </nav>
  <main>
    <section class="pane input">
      <div class="pane-head">
        <h2>1. Paste envelope</h2>
        <div class="samples">
          <span>Try:</span>
          <button type="button" class="sample-btn" data-sample="in-kb">Insufficient funds (7704)</button>
          <button type="button" class="sample-btn" data-sample="timeout">Timeout (X03B)</button>
          <button type="button" class="sample-btn" data-sample="out-of-kb">Unknown code</button>
        </div>
      </div>
      {error_html}
      <form method="post" action="/triage">
        <div class="row">
          <label>Dialect
            <select name="dialect">{dialect_options}</select>
          </label>
        </div>
        <textarea name="envelope" placeholder="Paste SOAP XML or JSON envelope here..." required>{envelope_escaped}</textarea>
        <button type="submit" class="primary">Triage envelope</button>
      </form>
    </section>
    <section class="pane result">
      <div class="pane-head">
        <h2>2. Triage result</h2>
      </div>
      {result_html or _empty_result_placeholder()}
    </section>
  </main>
  <footer>
    <span>payflow · deterministic decides, LLM explains</span>
  </footer>
  <script>{_JS}</script>
</body>
</html>"""


def _render_dialect_options(selected: Dialect) -> str:
    labels = {
        Dialect.CORE: "core — Remita STPv3",
        Dialect.FINACLE: "finacle",
        Dialect.FLEXCUBE: "flexcube",
        Dialect.GTB: "gtb",
        Dialect.POSTILION: "postilion",
        Dialect.UBN: "ubn",
    }
    return "".join(
        f'<option value="{d.value}"{" selected" if d == selected else ""}>{labels[d]}</option>'
        for d in Dialect
    )


def _render_result(result: TriageResult) -> str:
    r = result
    env = r.envelope
    conf_class = {
        "high": "high", "medium": "medium", "low": "low",
    }.get(r.confidence, "medium")
    conf_label = {
        "high": "HIGH CONFIDENCE",
        "medium": "MEDIUM CONFIDENCE",
        "low": "LOW CONFIDENCE — ROUTE TO HUMAN OPS",
    }.get(r.confidence, r.confidence.upper())
    strategy_class = f"strategy-{r.retry_strategy.value}"
    retryable_label = "retryable" if r.retryable else "terminal — do not retry"

    matched_html = ""
    if r.matched_code:
        matched_html = f"""
      <div class="field">
        <div class="label">Category</div>
        <div class="value"><code>{_escape(r.matched_code.category.value)}</code></div>
      </div>
      <div class="field">
        <div class="label">Customer-safe message</div>
        <div class="value">{_escape(r.matched_code.customer_message)}</div>
      </div>"""

    evidence_html = ""
    if r.evidence:
        items = "\n".join(f"<li>{_escape(e)}</li>" for e in r.evidence)
        evidence_html = f"""
      <div class="field evidence">
        <div class="label">Evidence</div>
        <ul>{items}</ul>
      </div>"""

    return f"""
      <div class="confidence {conf_class}">{conf_label}</div>
      <div class="field">
        <div class="label">Cause</div>
        <div class="value">{_escape(r.cause)}</div>
      </div>
      <div class="field">
        <div class="label">Ops action</div>
        <div class="value">{_escape(r.action)}</div>
      </div>
      <div class="field">
        <div class="label">Retry strategy</div>
        <div class="value">
          <code class="strategy {strategy_class}">{r.retry_strategy.value}</code>
          <span class="muted">· {retryable_label}</span>
        </div>
      </div>
      {matched_html}
      {evidence_html}
      <div class="footer-meta">
        dialect={_escape(env.dialect.value if env.dialect else 'n/a')}
        · method={_escape(env.method or 'n/a')}
        · session={_escape(env.session_id or 'n/a')}
        · confidence={_escape(r.confidence)}
      </div>"""


def _empty_result_placeholder() -> str:
    return '<div class="placeholder">Paste an envelope on the left and hit <b>Triage envelope</b>.</div>'


def _render_batch_page(
    rows: Optional[list[dict]],
    summary: Optional[dict],
    error: Optional[str],
    dialect: Dialect,
) -> str:
    error_html = f'<div class="error">{_escape(error)}</div>' if error else ""
    dialect_options = _render_dialect_options(dialect)
    results_html = _render_batch_results(rows, summary) if rows is not None else _render_batch_placeholder()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Payflow — Batch triage</title>
  <style>{_CSS}</style>
</head>
<body>
  <header>
    <div class="brand">
      <h1>Payflow</h1>
      <p class="tagline">Batch triage · upload a CSV, see per-envelope verdicts in real time</p>
    </div>
    <aside class="stats">
      <div class="stat"><div class="num">96.1%</div><div class="lbl">Accuracy<br><span>380 fixtures</span></div></div>
      <div class="stat"><div class="num">0.00%</div><div class="lbl">False-immediate<br><span>retry rate</span></div></div>
      <div class="stat"><div class="num">0.03ms</div><div class="lbl">p50 latency<br><span>deterministic</span></div></div>
      <div class="stat"><div class="num">$0.14/1k</div><div class="lbl">Gemini cached<br><span>LLM tail cost</span></div></div>
    </aside>
  </header>
  <nav class="tabs">
    <a href="/" class="tab">Single envelope</a>
    <a href="/batch" class="tab active">Batch CSV</a>
  </nav>
  <main class="main-single">
    <section class="pane input full-width">
      <div class="pane-head">
        <h2>1. Upload audit-trail CSV</h2>
      </div>
      <div class="note">
        CSV needs a <code>raw_request</code> or <code>raw_response</code> column
        with SOAP XML or JSON envelope content. Column names auto-detected.
        Envelope content stays in memory — nothing is written to disk.
      </div>
      {error_html}
      <form method="post" action="/batch" enctype="multipart/form-data">
        <div class="row">
          <label>Dialect
            <select name="dialect">{dialect_options}</select>
          </label>
          <label>CSV file
            <input type="file" name="csv" accept=".csv" required>
          </label>
        </div>
        <button type="submit" class="primary">Triage batch</button>
      </form>
    </section>
    <section class="pane result full-width">
      <div class="pane-head">
        <h2>2. Per-envelope verdicts</h2>
      </div>
      {results_html}
    </section>
  </main>
  <footer>
    <span>payflow · deterministic decides, LLM explains</span>
  </footer>
</body>
</html>"""


def _render_batch_placeholder() -> str:
    return '<div class="placeholder">Upload a CSV above to see per-envelope triage.</div>'


def _render_batch_results(rows: list[dict], summary: dict) -> str:
    if not rows:
        return '<div class="placeholder">CSV parsed but contained zero envelopes.</div>'

    strategy_chips = " ".join(
        f'<div class="chip strategy-{s}">{s}: {n}</div>'
        for s, n in summary["by_strategy"].items()
    )
    confidence_chips = " ".join(
        f'<div class="chip conf-{c}">{c}: {n}</div>'
        for c, n in summary["by_confidence"].items()
    )

    body_rows = []
    for i, r in enumerate(rows, 1):
        strategy_class = f"strategy-{r['strategy']}"
        confidence_class = f"conf-{r['confidence']}"
        kb_badge = '<span class="kb-hit">KB</span>' if r["kb_hit"] else '<span class="kb-miss">—</span>'
        body_rows.append(
            f"<tr>"
            f"<td class='num'>{i}</td>"
            f"<td class='mono'>{_escape(r['session_short'])}</td>"
            f"<td class='mono'>{_escape(r['code'])}</td>"
            f"<td>{kb_badge}</td>"
            f"<td><code class='strategy {strategy_class}'>{_escape(r['strategy'])}</code></td>"
            f"<td class='conf {confidence_class}'>{_escape(r['confidence'])}</td>"
            f"<td class='action-cell'>{_escape(_truncate(r['action'], 100))}</td>"
            f"</tr>"
        )

    csv_data_url = _rows_to_csv_data_url(rows)

    return f"""
      <div class="summary">
        <div class="chip total"><b>{summary['total']}</b> envelopes</div>
        <div class="chip">KB hits: <b>{summary['kb_hits']}</b> ({summary['kb_hit_pct']})</div>
        {strategy_chips}
        {confidence_chips}
        <a class="chip download" href="{csv_data_url}" download="payflow-batch-results.csv">
          ↓ Download CSV
        </a>
      </div>
      <div class="table-wrap">
        <table class="batch-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Session</th>
              <th>Code</th>
              <th>Layer</th>
              <th>Retry strategy</th>
              <th>Confidence</th>
              <th>Ops action</th>
            </tr>
          </thead>
          <tbody>
            {''.join(body_rows)}
          </tbody>
        </table>
      </div>"""


def _truncate(s: str, n: int) -> str:
    if len(s) <= n:
        return s
    return s[: n - 1] + "…"


def _escape(s: Optional[str]) -> str:
    if s is None:
        return ""
    return (
        s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        .replace('"', "&quot;").replace("'", "&#39;")
    )


_CSS = """
:root {
  --bg: #0b0d10;
  --bg-elev: #12151a;
  --bg-elev-2: #191d23;
  --border: #262b33;
  --fg: #e6e9ef;
  --fg-dim: #8a92a0;
  --accent: #a48cff;
  --accent-hi: #c4b0ff;
  --green: #4ade80;
  --yellow: #facc15;
  --red: #f87171;
  --mono: ui-monospace, SFMono-Regular, Menlo, monospace;
}
* { box-sizing: border-box }
body {
  font: 14px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
  background: var(--bg);
  color: var(--fg);
  margin: 0;
  min-height: 100vh;
  display: flex; flex-direction: column;
}
header {
  padding: 24px 32px;
  border-bottom: 1px solid var(--border);
  background: var(--bg-elev);
  display: flex; justify-content: space-between; align-items: center; gap: 32px;
  flex-wrap: wrap;
}
h1 { margin: 0; font-size: 24px; font-weight: 700; letter-spacing: -0.02em }
h2 { margin: 0; font-size: 15px; font-weight: 600; color: var(--fg-dim); text-transform: uppercase; letter-spacing: 0.05em }
.tagline { margin: 4px 0 0; color: var(--fg-dim); font-size: 13px }
.stats { display: flex; gap: 12px }
.stat {
  background: var(--bg-elev-2);
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 10px 14px;
  min-width: 88px;
}
.stat .num { font-family: var(--mono); font-size: 18px; font-weight: 700; color: var(--accent-hi) }
.stat .lbl { font-size: 10px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: 0.05em; margin-top: 2px; line-height: 1.4 }
.stat .lbl span { color: var(--fg-dim); opacity: 0.7 }
main {
  flex: 1;
  padding: 24px 32px;
  display: grid; grid-template-columns: 1fr 1fr; gap: 24px;
  max-width: 1400px; width: 100%; margin: 0 auto;
}
@media (max-width: 900px) { main { grid-template-columns: 1fr } }
.pane {
  background: var(--bg-elev);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 20px;
  display: flex; flex-direction: column; gap: 14px;
}
.pane-head { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px }
.samples { display: flex; gap: 6px; align-items: center; flex-wrap: wrap }
.samples span { font-size: 12px; color: var(--fg-dim); margin-right: 4px }
button {
  cursor: pointer;
  font: inherit;
  background: var(--bg-elev-2);
  color: var(--fg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 12px;
  font-size: 12px;
  transition: all 120ms ease;
}
button:hover { border-color: var(--accent); color: var(--accent-hi) }
button.primary {
  background: var(--accent);
  color: #14101f;
  border-color: var(--accent);
  font-weight: 600;
  font-size: 14px;
  padding: 10px 18px;
  align-self: flex-start;
}
button.primary:hover { background: var(--accent-hi); color: #14101f }
form { display: flex; flex-direction: column; gap: 12px }
.row { display: flex; gap: 12px; align-items: center }
label { display: flex; flex-direction: column; gap: 4px; font-size: 12px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: 0.05em }
select, textarea, input {
  background: var(--bg);
  color: var(--fg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px 10px;
  font-family: var(--mono);
  font-size: 13px;
}
select { min-width: 180px; text-transform: none; letter-spacing: 0 }
select:focus, textarea:focus { outline: 2px solid var(--accent); outline-offset: -1px }
textarea { min-height: 260px; resize: vertical; line-height: 1.5 }
.confidence {
  display: inline-block;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.05em;
  border: 1px solid;
}
.confidence.high { background: rgba(74, 222, 128, 0.1); color: var(--green); border-color: var(--green) }
.confidence.medium { background: rgba(250, 204, 21, 0.1); color: var(--yellow); border-color: var(--yellow) }
.confidence.low { background: rgba(248, 113, 113, 0.1); color: var(--red); border-color: var(--red) }
.field { display: flex; flex-direction: column; gap: 4px }
.field .label { font-size: 11px; color: var(--fg-dim); text-transform: uppercase; letter-spacing: 0.05em }
.field .value { font-size: 14px; line-height: 1.5 }
.field.evidence ul { margin: 0; padding-left: 18px; font-family: var(--mono); font-size: 12px; color: var(--fg-dim) }
.field.evidence li { margin: 2px 0 }
.strategy { font-family: var(--mono); padding: 2px 8px; border-radius: 4px; background: var(--bg-elev-2); font-size: 13px }
.strategy-never { color: var(--red) }
.strategy-status_query { color: var(--yellow) }
.strategy-backoff { color: var(--accent) }
.strategy-immediate { color: var(--green) }
.strategy-reversal { color: var(--red) }
.muted { color: var(--fg-dim); font-size: 12px; margin-left: 8px }
.footer-meta { font-family: var(--mono); font-size: 11px; color: var(--fg-dim); border-top: 1px solid var(--border); padding-top: 12px; margin-top: 4px }
.placeholder { color: var(--fg-dim); text-align: center; padding: 40px 20px; font-size: 13px }
.placeholder b { color: var(--fg) }
.error { background: rgba(248, 113, 113, 0.1); color: var(--red); border: 1px solid var(--red); border-radius: 6px; padding: 10px 12px; font-size: 13px }
footer { padding: 16px 32px; border-top: 1px solid var(--border); color: var(--fg-dim); font-size: 12px; text-align: center; font-family: var(--mono) }

/* nav tabs */
.tabs { display: flex; gap: 4px; padding: 0 32px; border-bottom: 1px solid var(--border); background: var(--bg-elev) }
.tab { padding: 12px 20px; color: var(--fg-dim); text-decoration: none; font-size: 13px; border-bottom: 2px solid transparent; margin-bottom: -1px }
.tab:hover { color: var(--fg) }
.tab.active { color: var(--accent-hi); border-bottom-color: var(--accent) }

/* batch page — single column, wide */
main.main-single { grid-template-columns: 1fr }
.pane.full-width { width: 100% }
.note { color: var(--fg-dim); font-size: 12px; padding: 8px 12px; background: var(--bg); border-radius: 6px; border-left: 3px solid var(--accent) }
.note code { font-family: var(--mono); color: var(--accent-hi); background: var(--bg-elev-2); padding: 1px 5px; border-radius: 3px }
input[type=file] { padding: 6px 8px; font-family: var(--mono); font-size: 12px }
.summary { display: flex; gap: 8px; flex-wrap: wrap; padding: 12px 0 }
.chip { background: var(--bg-elev-2); border: 1px solid var(--border); padding: 6px 10px; border-radius: 6px; font-size: 12px; color: var(--fg-dim); font-family: var(--mono) }
.chip b { color: var(--fg) }
.chip.total { background: var(--accent); color: #14101f; border-color: var(--accent) }
.chip.total b { color: #14101f }
.chip.strategy-never { color: var(--red); border-color: var(--red) }
.chip.strategy-status_query { color: var(--yellow); border-color: var(--yellow) }
.chip.strategy-backoff { color: var(--accent) }
.chip.strategy-immediate { color: var(--green) }
.chip.conf-high { color: var(--green); border-color: var(--green) }
.chip.conf-medium { color: var(--yellow); border-color: var(--yellow) }
.chip.conf-low { color: var(--red); border-color: var(--red) }
.chip.download { background: var(--bg-elev); color: var(--accent); border-color: var(--accent); text-decoration: none; cursor: pointer; margin-left: auto }
.chip.download:hover { background: var(--accent); color: #14101f }

/* batch table */
.table-wrap { overflow-x: auto; margin-top: 8px; border: 1px solid var(--border); border-radius: 8px }
.batch-table { width: 100%; border-collapse: collapse; font-size: 12px }
.batch-table th { background: var(--bg-elev-2); color: var(--fg-dim); text-align: left; padding: 10px 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; font-size: 11px; border-bottom: 1px solid var(--border); position: sticky; top: 0 }
.batch-table td { padding: 8px 12px; border-bottom: 1px solid var(--border); vertical-align: top }
.batch-table tr:last-child td { border-bottom: none }
.batch-table tr:hover td { background: var(--bg-elev-2) }
.batch-table td.num { color: var(--fg-dim); font-family: var(--mono); font-size: 11px }
.batch-table td.mono { font-family: var(--mono) }
.batch-table td.action-cell { color: var(--fg-dim); max-width: 400px }
.batch-table .conf { font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em; font-weight: 600 }
.batch-table .conf-high { color: var(--green) }
.batch-table .conf-medium { color: var(--yellow) }
.batch-table .conf-low { color: var(--red) }
.kb-hit { color: var(--green); font-family: var(--mono); font-size: 11px; font-weight: 700; letter-spacing: 0.05em }
.kb-miss { color: var(--fg-dim); font-family: var(--mono) }
"""

_JS = """
const samples = {
  "in-kb": document.getElementById("_sample_in_kb")?.textContent || "",
  "timeout": document.getElementById("_sample_timeout")?.textContent || "",
  "out-of-kb": document.getElementById("_sample_out_of_kb")?.textContent || "",
};
document.querySelectorAll(".sample-btn").forEach(btn => {
  btn.addEventListener("click", (e) => {
    e.preventDefault();
    const key = btn.getAttribute("data-sample");
    const src = SAMPLES[key];
    if (src) document.querySelector('textarea[name="envelope"]').value = src;
  });
});
"""


# Inject the samples as a JS object at page-render time. Cleaner than reading them
# from hidden DOM nodes (avoids HTML escaping issues around the XML content).
def _samples_js_literal() -> str:
    def _js_escape(s: str) -> str:
        return s.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    return (
        "const SAMPLES = {\n"
        f"  \"in-kb\": `{_js_escape(_SAMPLE_IN_KB)}`,\n"
        f"  \"timeout\": `{_js_escape(_SAMPLE_TIMEOUT)}`,\n"
        f"  \"out-of-kb\": `{_js_escape(_SAMPLE_OUT_OF_KB)}`,\n"
        "};\n"
    )


# Rebuild _JS with the samples object injected (module import time is fine)
_JS = _samples_js_literal() + _JS
