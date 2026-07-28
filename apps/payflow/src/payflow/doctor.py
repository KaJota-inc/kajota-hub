"""Pre-flight readiness check.

`payflow doctor` walks through every subsystem and reports PASS / FAIL / SKIP with
enough context to fix. Designed to be the FIRST command the ops team runs on a
new deploy — well before the bank's Freshdesk starts firing webhooks at us.
"""
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from rich.console import Console
from rich.table import Table

from payflow.kb import load_kb
from payflow.models import Dialect, Envelope
from payflow.parser import parse_json, parse_soap
from payflow.triage import triage_deterministic


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"


@dataclass
class CheckResult:
    name: str
    status: Status
    detail: str = ""
    fix: str = ""


@dataclass
class DoctorReport:
    checks: list[CheckResult] = field(default_factory=list)

    @property
    def failed(self) -> int:
        return sum(1 for c in self.checks if c.status is Status.FAIL)

    @property
    def passed(self) -> int:
        return sum(1 for c in self.checks if c.status is Status.PASS)

    @property
    def skipped(self) -> int:
        return sum(1 for c in self.checks if c.status is Status.SKIP)


# --- individual checks ------------------------------------------------------

_ALL_DIALECTS = list(Dialect)


def _check_kb_loads() -> CheckResult:
    try:
        kb = load_kb()
    except Exception as e:
        return CheckResult("kb.load", Status.FAIL, f"load_kb() raised: {e!r}",
                           fix="Inspect src/payflow/kb/*.yaml for parse errors.")
    if not kb:
        return CheckResult("kb.load", Status.FAIL, "KB is empty",
                           fix="Check src/payflow/kb/*.yaml files exist and have `codes:` entries.")
    return CheckResult(
        "kb.load", Status.PASS,
        f"{len(kb)} (dialect,code) entries loaded across {len({d for d, _ in kb.keys()})} dialects",
    )


def _check_all_dialects_present() -> CheckResult:
    try:
        kb = load_kb()
    except Exception:
        return CheckResult("kb.dialects_present", Status.SKIP, "KB failed to load")
    present = {d for (d, _) in kb.keys()}
    missing = [d.value for d in _ALL_DIALECTS if d not in present]
    if missing:
        return CheckResult(
            "kb.dialects_present", Status.FAIL,
            f"missing dialect YAMLs: {', '.join(missing)}",
            fix="Add the missing dialect YAML(s) under src/payflow/kb/.",
        )
    return CheckResult(
        "kb.dialects_present", Status.PASS,
        f"all {len(_ALL_DIALECTS)} dialects present: {', '.join(sorted(d.value for d in present))}",
    )


_SAMPLE_SOAP = """<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ns="http://nibss.com/nip/">
  <soap:Body>
    <ns:FundsTransferResponse>
      <SessionID>099999123456789012345678900</SessionID>
      <ResponseCode>7704</ResponseCode>
      <ResponseMessage>Insufficient Funds</ResponseMessage>
    </ns:FundsTransferResponse>
  </soap:Body>
</soap:Envelope>"""

_SAMPLE_JSON = '{"sessionId":"099999123","responseCode":"7704","responseMessage":"Insufficient Funds","method":"FundsTransfer"}'


def _check_parsers() -> CheckResult:
    try:
        soap_env = parse_soap(_SAMPLE_SOAP)
        json_env = parse_json(_SAMPLE_JSON)
    except Exception as e:
        return CheckResult("parser.smoke", Status.FAIL, f"parser raised: {e!r}",
                           fix="Inspect src/payflow/parser/*.py — soap/json parsers are broken.")
    if soap_env.response_code != "7704" or json_env.response_code != "7704":
        return CheckResult("parser.smoke", Status.FAIL,
                           f"parsed response_code mismatch (soap={soap_env.response_code!r}, "
                           f"json={json_env.response_code!r})")
    return CheckResult("parser.smoke", Status.PASS, "SOAP + JSON parsers extract response_code correctly")


def _check_deterministic_triage() -> CheckResult:
    try:
        kb = load_kb()
    except Exception:
        return CheckResult("triage.deterministic", Status.SKIP, "KB failed to load")
    env = Envelope(source="soap", dialect=Dialect.CORE, response_code="7704")
    result = triage_deterministic(env, kb)
    if result.confidence != "high" or result.retry_strategy.value != "never":
        return CheckResult(
            "triage.deterministic", Status.FAIL,
            f"expected high/never for (core,7704), got {result.confidence}/{result.retry_strategy.value}",
        )
    return CheckResult("triage.deterministic", Status.PASS,
                       "KB hit (core,7704) → never, high confidence")


def _check_env_group(name: str, required: dict[str, str], optional: dict[str, str] = None) -> CheckResult:
    """Check a group of env vars: PASS if all required present, SKIP if none set, FAIL if partial."""
    optional = optional or {}
    present_req = {k for k in required if os.environ.get(k)}
    present_opt = {k for k in optional if os.environ.get(k)}
    if not present_req and not present_opt:
        return CheckResult(f"env.{name}", Status.SKIP, "no env vars set — integration not deployed here")
    missing_req = [k for k in required if k not in present_req]
    if missing_req:
        return CheckResult(
            f"env.{name}", Status.FAIL,
            f"partially configured; missing: {', '.join(missing_req)}",
            fix=f"Set the missing vars: {', '.join(missing_req)}",
        )
    detail = f"all required present ({', '.join(sorted(present_req))})"
    if optional:
        opt_status = ", ".join(f"{k}={'set' if k in present_opt else 'unset'}" for k in optional)
        detail += f" | optional: {opt_status}"
    return CheckResult(f"env.{name}", Status.PASS, detail)


def _check_freshdesk_env() -> CheckResult:
    return _check_env_group(
        "freshdesk",
        required={
            "FRESHDESK_DOMAIN": "hostname",
            "FRESHDESK_API_KEY": "API key",
            "FRESHDESK_WEBHOOK_SECRET": "HMAC secret",
        },
        optional={"FRESHDESK_DEFAULT_DIALECT": "dialect fallback"},
    )


def _check_zendesk_env() -> CheckResult:
    return _check_env_group(
        "zendesk",
        required={
            "ZENDESK_SUBDOMAIN": "subdomain",
            "ZENDESK_EMAIL": "email",
            "ZENDESK_API_TOKEN": "API token",
            "ZENDESK_WEBHOOK_SECRET": "HMAC secret",
        },
        optional={"ZENDESK_DEFAULT_DIALECT": "dialect fallback"},
    )


def _check_llm_keys() -> CheckResult:
    """Check LLM keys presence. If USE_LLM=true, at least one provider key required."""
    use_llm = (os.environ.get("PAYFLOW_USE_LLM", "false").lower() in ("1", "true", "yes", "on"))
    provider = os.environ.get("PAYFLOW_PROVIDER", "anthropic").lower()
    ant = bool(os.environ.get("ANTHROPIC_API_KEY"))
    gem = bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"))

    if not use_llm:
        return CheckResult(
            "env.llm_keys", Status.SKIP,
            f"PAYFLOW_USE_LLM=false — LLM path disabled (anthropic_key={ant}, gemini_key={gem})",
        )
    if provider == "anthropic" and not ant:
        return CheckResult(
            "env.llm_keys", Status.FAIL,
            "PAYFLOW_PROVIDER=anthropic but ANTHROPIC_API_KEY unset",
            fix="Set ANTHROPIC_API_KEY, or switch PAYFLOW_PROVIDER=gemini.",
        )
    if provider == "gemini" and not gem:
        return CheckResult(
            "env.llm_keys", Status.FAIL,
            "PAYFLOW_PROVIDER=gemini but GEMINI_API_KEY/GOOGLE_API_KEY unset",
            fix="Set GEMINI_API_KEY or GOOGLE_API_KEY.",
        )
    return CheckResult(
        "env.llm_keys", Status.PASS,
        f"provider={provider}, key present; verifier=Sonnet 5 requires ANTHROPIC_API_KEY (set={ant})",
    )


# --- live checks (require --live flag; may hit network) ---------------------

def _check_anthropic_live() -> CheckResult:
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return CheckResult("live.anthropic", Status.SKIP, "no ANTHROPIC_API_KEY")
    try:
        from anthropic import Anthropic
        client = Anthropic(api_key=key)
        model = os.environ.get("PAYFLOW_LLM_MODEL", "claude-haiku-4-5-20251001")
        resp = client.messages.create(
            model=model, max_tokens=8,
            messages=[{"role": "user", "content": "ping"}],
        )
    except Exception as e:
        return CheckResult(
            "live.anthropic", Status.FAIL,
            f"API call failed: {type(e).__name__}: {e}",
            fix="Verify ANTHROPIC_API_KEY, network access to api.anthropic.com, and PAYFLOW_LLM_MODEL is valid.",
        )
    return CheckResult("live.anthropic", Status.PASS,
                       f"model={model} reachable, {resp.usage.output_tokens} output tokens returned")


def _check_gemini_live() -> CheckResult:
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        return CheckResult("live.gemini", Status.SKIP, "no GEMINI_API_KEY/GOOGLE_API_KEY")
    try:
        from google import genai
        client = genai.Client(api_key=key)
        model = os.environ.get("PAYFLOW_GEMINI_MODEL", "gemini-2.5-flash-lite")
        client.models.generate_content(
            model=model, contents="ping",
            config={"max_output_tokens": 8},
        )
    except Exception as e:
        return CheckResult(
            "live.gemini", Status.FAIL,
            f"API call failed: {type(e).__name__}: {e}",
            fix="Verify GEMINI_API_KEY, network to generativelanguage.googleapis.com, model name.",
        )
    return CheckResult("live.gemini", Status.PASS, f"model={model} reachable")


def _check_freshdesk_live() -> CheckResult:
    domain = os.environ.get("FRESHDESK_DOMAIN")
    api_key = os.environ.get("FRESHDESK_API_KEY")
    if not (domain and api_key):
        return CheckResult("live.freshdesk", Status.SKIP, "FRESHDESK env incomplete")
    try:
        import base64

        import httpx
        auth = base64.b64encode(f"{api_key}:X".encode()).decode()
        r = httpx.get(
            f"https://{domain}/api/v2/agents/me",
            headers={"Authorization": f"Basic {auth}"},
            timeout=8.0,
        )
    except Exception as e:
        return CheckResult("live.freshdesk", Status.FAIL, f"request failed: {type(e).__name__}: {e}")
    if r.status_code >= 400:
        return CheckResult(
            "live.freshdesk", Status.FAIL,
            f"HTTP {r.status_code}: {r.text[:200]}",
            fix="Verify FRESHDESK_API_KEY and that this account has API access.",
        )
    return CheckResult("live.freshdesk", Status.PASS, f"authenticated as agent {r.json().get('contact', {}).get('email', '?')}")


def _check_zendesk_live() -> CheckResult:
    sub = os.environ.get("ZENDESK_SUBDOMAIN")
    email = os.environ.get("ZENDESK_EMAIL")
    token = os.environ.get("ZENDESK_API_TOKEN")
    if not (sub and email and token):
        return CheckResult("live.zendesk", Status.SKIP, "ZENDESK env incomplete")
    try:
        import base64

        import httpx
        auth = base64.b64encode(f"{email}/token:{token}".encode()).decode()
        r = httpx.get(
            f"https://{sub}.zendesk.com/api/v2/users/me.json",
            headers={"Authorization": f"Basic {auth}"},
            timeout=8.0,
        )
    except Exception as e:
        return CheckResult("live.zendesk", Status.FAIL, f"request failed: {type(e).__name__}: {e}")
    if r.status_code >= 400:
        return CheckResult(
            "live.zendesk", Status.FAIL,
            f"HTTP {r.status_code}: {r.text[:200]}",
            fix="Verify ZENDESK_EMAIL + ZENDESK_API_TOKEN combination.",
        )
    return CheckResult("live.zendesk", Status.PASS,
                       f"authenticated as {r.json().get('user', {}).get('email', '?')}")


# --- orchestration ----------------------------------------------------------

OFFLINE_CHECKS: list[Callable[[], CheckResult]] = [
    _check_kb_loads,
    _check_all_dialects_present,
    _check_parsers,
    _check_deterministic_triage,
    _check_freshdesk_env,
    _check_zendesk_env,
    _check_llm_keys,
]

LIVE_CHECKS: list[Callable[[], CheckResult]] = [
    _check_anthropic_live,
    _check_gemini_live,
    _check_freshdesk_live,
    _check_zendesk_live,
]


def run_doctor(live: bool = False) -> DoctorReport:
    """Run all offline checks; if `live=True`, also run network-touching checks."""
    report = DoctorReport()
    for check in OFFLINE_CHECKS:
        try:
            report.checks.append(check())
        except Exception as e:  # a check crashed = FAIL, don't crash the whole doctor
            report.checks.append(CheckResult(check.__name__, Status.FAIL, f"check raised: {e!r}"))
    if live:
        for check in LIVE_CHECKS:
            try:
                report.checks.append(check())
            except Exception as e:
                report.checks.append(CheckResult(check.__name__, Status.FAIL, f"check raised: {e!r}"))
    return report


_STATUS_STYLES = {
    Status.PASS: "green",
    Status.FAIL: "red bold",
    Status.SKIP: "yellow",
}


def format_doctor_report(report: DoctorReport, console: Optional[Console] = None) -> None:
    console = console or Console()
    tab = Table(title="payflow doctor — readiness check")
    tab.add_column("Check", style="cyan")
    tab.add_column("Status")
    tab.add_column("Detail")
    for c in report.checks:
        tab.add_row(c.name, f"[{_STATUS_STYLES[c.status]}]{c.status.value}[/]", c.detail)
    console.print(tab)
    fixes = [c for c in report.checks if c.status is Status.FAIL and c.fix]
    if fixes:
        console.print()
        console.print("[bold]Fixes:[/bold]")
        for c in fixes:
            console.print(f"  • [red]{c.name}[/red]: {c.fix}")
    console.print()
    console.print(
        f"[bold]Summary:[/bold] "
        f"[green]{report.passed} pass[/green], "
        f"[red]{report.failed} fail[/red], "
        f"[yellow]{report.skipped} skip[/yellow]"
    )
