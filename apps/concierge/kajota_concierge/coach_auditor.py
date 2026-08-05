"""KH workflow auditor — the second-opinion tool for web3/write-contract steps.

Coach reads a KeeperHub workflow (via the KH REST API given an id, or
directly from a JSON body) and runs it through a rules engine that
catches the exact trap classes we documented in PR #1857 to KH's docs.
The report card lists each issue with severity, the offending path, a
one-line explanation, and a suggested fix.

Design invariant, same as the CFO module: **deterministic decides,
narration explains**. The auditor emits a machine-readable list of
issues plus a plain-English summary. Nothing here signs a transaction
or writes to KH — it's purely diagnostic. A follow-up ``apply``
endpoint (out of scope for the hackathon MVP) would take the list of
suggested edits and PATCH the workflow via KH's own API.

The trap catalogue below tracks the state of PR #1857 after joel's
review: `functionName` is an accepted legacy alias so we only WARN on
it (not FAIL), while `function` / `method` / `contract` remain hard
FAILs. The silently-ignored `integrationId` is a hard FAIL because
it's the subtlest of the traps — no error surfaces at create time, no
error surfaces at execute time, the write just goes out on the wrong
wallet.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


# ---- issue model --------------------------------------------------

# Severity ladder:
#   error   — will silently mis-route, silently drop a field, or fail
#             at execution. Must fix before running the workflow.
#   warn    — accepted by the API but non-canonical / not future-proof.
#             Legacy alias, missing recommended field, etc.
#   info    — style nudge, docs pointer, no runtime consequence.
SEVERITY_ERROR = "error"
SEVERITY_WARN = "warn"
SEVERITY_INFO = "info"


@dataclass(frozen=True)
class Issue:
    trap: str            # short kebab-case id — "silently-ignored-integration-id" etc.
    severity: str        # SEVERITY_*
    path: str            # jsonpath-ish location in the workflow tree
    detail: str          # what's wrong, in plain English
    fix: str             # suggested replacement (may be a code snippet)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trap": self.trap,
            "severity": self.severity,
            "path": self.path,
            "detail": self.detail,
            "fix": self.fix,
        }


# ---- constants ----------------------------------------------------

# Field names the strict-mode validator genuinely rejects (per joel's
# review of PR #1857). functionName intentionally not in this list —
# it's an accepted legacy alias, so we warn on it but do not fail.
REJECTED_FUNCTION_ALIASES = {"function", "method", "contract"}

# The legacy alias for abiFunction. Accepted; we warn on it so devs
# migrate to the canonical form.
LEGACY_FUNCTION_ALIASES = {"functionName"}

# The reserved-but-ignored routing key. This is the meanest trap
# because it accepts, saves, then silently ignores at execute time.
SILENTLY_IGNORED_ROUTING_KEYS = {"integrationId"}

# The correct routing key + accepted value shapes.
CANONICAL_ROUTING_KEY = "web3Connection"
CANONICAL_ROUTING_VALUES = ("default", "eoa")  # plus safe:<safeWalletId> prefix

# Correct HTTP-trigger template pattern: {{@<nodeId>:<Label>.<field>}}.
STORED_TEMPLATE_RE = re.compile(r"\{\{\s*@([a-zA-Z0-9_-]+):([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\s*\}\}")

# The intuitive-but-broken template pattern devs try first.
BROKEN_TEMPLATE_RE = re.compile(r"\{\{\s*@trigger\.body\.([A-Za-z0-9_]+)\s*\}\}")

# The write-contract action type slug.
WRITE_CONTRACT_ACTION = "web3/write-contract"


# ---- inspectors ---------------------------------------------------

def _is_json_encoded_string(value: Any) -> bool:
    """Return True iff `value` is a str that parses as JSON."""
    if not isinstance(value, str):
        return False
    try:
        json.loads(value)
        return True
    except (json.JSONDecodeError, ValueError):
        return False


def _iter_action_nodes(workflow: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Yield (path, node_dict) for every action node in the workflow."""
    out: list[tuple[str, dict[str, Any]]] = []
    nodes = workflow.get("nodes") or []
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        outer_type = node.get("type") or ""
        data = node.get("data") or {}
        config = data.get("config") or {}
        action_type = config.get("actionType") or ""
        # Accept both {type:'action', data.config.actionType:'web3/...'}
        # and the shorthand {type:'web3/write-contract', ...}
        is_action = outer_type == "action" or "/" in outer_type
        looks_like_write_contract = (
            action_type == WRITE_CONTRACT_ACTION
            or outer_type == WRITE_CONTRACT_ACTION
        )
        if is_action and looks_like_write_contract:
            out.append((f"nodes[{i}]", node))
    return out


# ---- individual rules ---------------------------------------------

def _check_function_key(path: str, config: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    has_canonical = "abiFunction" in config
    for alias in LEGACY_FUNCTION_ALIASES:
        if alias in config and not has_canonical:
            issues.append(Issue(
                trap="legacy-function-alias",
                severity=SEVERITY_WARN,
                path=f"{path}.data.config.{alias}",
                detail=(
                    f"`{alias}` is an accepted legacy alias for `abiFunction`, "
                    "but the canonical field is `abiFunction`. New code should "
                    "use the canonical form."
                ),
                fix=f'rename "{alias}" to "abiFunction"',
            ))
    for bad in REJECTED_FUNCTION_ALIASES:
        if bad in config:
            issues.append(Issue(
                trap="rejected-function-alias",
                severity=SEVERITY_ERROR,
                path=f"{path}.data.config.{bad}",
                detail=(
                    f"`{bad}` is rejected by the strict-mode validator as "
                    "UNKNOWN_FIELD. Use `abiFunction`."
                ),
                fix=f'rename "{bad}" to "abiFunction"',
            ))
    if not has_canonical and not any(a in config for a in LEGACY_FUNCTION_ALIASES):
        issues.append(Issue(
            trap="missing-abi-function",
            severity=SEVERITY_ERROR,
            path=f"{path}.data.config",
            detail="write-contract step is missing `abiFunction` (the function name to call).",
            fix='add `"abiFunction": "<yourFunctionName>"`',
        ))
    return issues


def _check_function_args(path: str, config: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    if "functionArgs" not in config:
        return issues
    args = config["functionArgs"]
    if isinstance(args, list):
        issues.append(Issue(
            trap="function-args-raw-array",
            severity=SEVERITY_ERROR,
            path=f"{path}.data.config.functionArgs",
            detail=(
                "`functionArgs` is a raw array. The API accepts it, but the "
                "runtime throws `Invalid function arguments JSON` at execute "
                "time — this fails silently until you fire the workflow."
            ),
            fix=(
                "wrap in a JSON-encoded string, e.g. "
                f'{json.dumps(json.dumps(args))}'
            ),
        ))
    elif not _is_json_encoded_string(args):
        issues.append(Issue(
            trap="function-args-not-json-string",
            severity=SEVERITY_ERROR,
            path=f"{path}.data.config.functionArgs",
            detail="`functionArgs` must be a JSON-encoded array string like `\"[\\\"0xabc…\\\"]\"`.",
            fix='wrap the arguments as JSON: JSON.stringify(["…", "…"])',
        ))
    return issues


def _check_abi(path: str, config: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    if "abi" not in config:
        return issues
    abi = config["abi"]
    if isinstance(abi, list):
        issues.append(Issue(
            trap="abi-raw-array",
            severity=SEVERITY_ERROR,
            path=f"{path}.data.config.abi",
            detail="`abi` is a raw array. Like `functionArgs`, it must be JSON-encoded to a string.",
            fix="wrap as JSON: JSON.stringify(abiFragment)",
        ))
    elif not _is_json_encoded_string(abi):
        issues.append(Issue(
            trap="abi-not-json-string",
            severity=SEVERITY_ERROR,
            path=f"{path}.data.config.abi",
            detail="`abi` must be a JSON-encoded array string.",
            fix="wrap as JSON: JSON.stringify(abiFragment)",
        ))
    return issues


def _check_web3_connection(path: str, config: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for silent in SILENTLY_IGNORED_ROUTING_KEYS:
        if silent in config:
            issues.append(Issue(
                trap="silently-ignored-integration-id",
                severity=SEVERITY_ERROR,
                path=f"{path}.data.config.{silent}",
                detail=(
                    f"`{silent}` is a reserved config key that the validator "
                    "accepts but the write-contract action ignores. The signing "
                    "wallet is routed by `web3Connection` instead."
                ),
                fix=(
                    f'replace `"{silent}": "…"` with '
                    '`"web3Connection": "default"` (or "eoa" / "safe:<id>")'
                ),
            ))
    if CANONICAL_ROUTING_KEY in config:
        val = config[CANONICAL_ROUTING_KEY]
        ok = (
            isinstance(val, str)
            and (val in CANONICAL_ROUTING_VALUES or val.startswith("safe:"))
        )
        if not ok:
            issues.append(Issue(
                trap="invalid-web3-connection-value",
                severity=SEVERITY_ERROR,
                path=f"{path}.data.config.{CANONICAL_ROUTING_KEY}",
                detail=(
                    f"`{CANONICAL_ROUTING_KEY}` must be one of "
                    '`"default"`, `"eoa"`, or `"safe:<safeWalletId>"`.'
                ),
                fix='set to "default" (org policy) unless you need EOA or a specific Safe',
            ))
    return issues


def _check_network(path: str, config: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    if "network" not in config:
        return issues
    net = config["network"]
    if isinstance(net, int):
        issues.append(Issue(
            trap="network-numeric-not-string",
            severity=SEVERITY_WARN,
            path=f"{path}.data.config.network",
            detail=(
                "`network` is a JSON number; KH expects a numeric chain id as "
                "a STRING (e.g. `\"11155111\"`)."
            ),
            fix=f'wrap as a string: "{net}"',
        ))
    return issues


def _check_templates(path: str, config: dict[str, Any]) -> list[Issue]:
    """Scan the config values for broken vs stored template syntax."""
    issues: list[Issue] = []
    for key, value in config.items():
        if not isinstance(value, str):
            continue
        for match in BROKEN_TEMPLATE_RE.finditer(value):
            field_name = match.group(1)
            issues.append(Issue(
                trap="broken-trigger-template",
                severity=SEVERITY_ERROR,
                path=f"{path}.data.config.{key}",
                detail=(
                    f"`{{{{@trigger.body.{field_name}}}}}` is the intuitive "
                    "template pattern but resolves to an empty string in stored "
                    "workflows. HTTP triggers use the slot-scoped syntax "
                    f"`{{{{@<nodeId>:HTTP.{field_name}}}}}`."
                ),
                fix=(
                    f"replace `{{{{@trigger.body.{field_name}}}}}` with "
                    f"`{{{{@trigger-1:HTTP.{field_name}}}}}` "
                    "(match the HTTP trigger node id)"
                ),
            ))
    return issues


def _check_http_trigger_body_wrap(workflow: dict[str, Any]) -> list[Issue]:
    """Return an info-level nudge about the required `input` wrap.

    We can't verify the caller's POST body from here — this is a static
    reminder shown once per audit when the workflow has an HTTP trigger.
    """
    for node in workflow.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        data = node.get("data") or {}
        cfg = data.get("config") or {}
        trigger_type = cfg.get("triggerType") or ""
        outer = node.get("type") or ""
        if trigger_type == "HTTP" or outer == "trigger" and data.get("label") == "HTTP":
            return [Issue(
                trap="http-body-wrap-reminder",
                severity=SEVERITY_INFO,
                path="request body",
                detail=(
                    "HTTP triggers spread top-level fields of the request body "
                    "into the trigger output — but ONLY when the body is wrapped "
                    'under `input`. POST `{"input": {"depositId": "0x…"}}`, '
                    'not `{"depositId": "0x…"}`.'
                ),
                fix='wrap the POST body under `input`',
            )]
    return []


# ---- top-level ----------------------------------------------------

@dataclass(frozen=True)
class AuditReport:
    passed: bool
    error_count: int
    warn_count: int
    info_count: int
    issues: list[Issue]
    summary: str
    action_nodes_scanned: int
    workflow_ref: str  # workflow id, or "inline" when supplied as body

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "counts": {
                "error": self.error_count,
                "warn": self.warn_count,
                "info": self.info_count,
            },
            "issues": [i.to_dict() for i in self.issues],
            "summary": self.summary,
            "actionNodesScanned": self.action_nodes_scanned,
            "workflowRef": self.workflow_ref,
        }


def _summarise(
    passed: bool,
    action_nodes_scanned: int,
    errs: int,
    warns: int,
) -> str:
    if action_nodes_scanned == 0:
        return (
            "No `web3/write-contract` action nodes in this workflow — nothing "
            "to audit. The auditor only checks the write-contract action's "
            "field-name traps; other action types are out of scope."
        )
    if passed:
        soft = f" {warns} warning{'s' if warns != 1 else ''} logged." if warns else ""
        return (
            f"Clean audit across {action_nodes_scanned} write-contract "
            f"action{'s' if action_nodes_scanned != 1 else ''}.{soft} "
            "Safe to execute — no traps from PR #1857 detected."
        )
    return (
        f"Audit failed: {errs} error{'s' if errs != 1 else ''} "
        f"(+ {warns} warning{'s' if warns != 1 else ''}) across "
        f"{action_nodes_scanned} write-contract "
        f"action{'s' if action_nodes_scanned != 1 else ''}. "
        "Fix errors before executing — the traps below either mis-route "
        "the signing wallet or fail silently at execute time."
    )


def audit_workflow(workflow: dict[str, Any], *, workflow_ref: str = "inline") -> AuditReport:
    """Run every rule against a workflow definition and return an audit report.

    Pure function of its input — same workflow always yields the same
    report. That's what makes the auditor safe to expose over an HTTP
    endpoint that agents can hit before firing a release.
    """
    issues: list[Issue] = []
    action_nodes = _iter_action_nodes(workflow)
    for path, node in action_nodes:
        cfg = ((node.get("data") or {}).get("config") or {})
        issues.extend(_check_function_key(path, cfg))
        issues.extend(_check_function_args(path, cfg))
        issues.extend(_check_abi(path, cfg))
        issues.extend(_check_web3_connection(path, cfg))
        issues.extend(_check_network(path, cfg))
        issues.extend(_check_templates(path, cfg))
    issues.extend(_check_http_trigger_body_wrap(workflow))

    errs = sum(1 for i in issues if i.severity == SEVERITY_ERROR)
    warns = sum(1 for i in issues if i.severity == SEVERITY_WARN)
    infos = sum(1 for i in issues if i.severity == SEVERITY_INFO)
    passed = errs == 0

    return AuditReport(
        passed=passed,
        error_count=errs,
        warn_count=warns,
        info_count=infos,
        issues=issues,
        summary=_summarise(passed, len(action_nodes), errs, warns),
        action_nodes_scanned=len(action_nodes),
        workflow_ref=workflow_ref,
    )
