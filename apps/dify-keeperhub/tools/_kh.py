"""Shared KeeperHub access for every tool in this plugin.

Built on `keeperhub-mcp`, KeeperHub's own published MCP kernel, rather than
a hand-rolled transport. Their SDK strategy is explicit about this: a shared
framework-agnostic kernel, with per-framework adapters importing it. The
kernel already handles session bootstrap, re-init on 401/404, kh_ vs wfb_
key disambiguation, and unwrapping the single JSON result — so this module
only has to turn its output into something a Dify workflow can read.
"""

from __future__ import annotations

from typing import Any

from keeperhub_mcp import (
    KeeperHubMcpClient,
    get_api_key_kind_warning,
    is_org_api_key,
    mask_api_key,
)

# Ethereum Sepolia. The plugin defaults to a testnet on purpose: a tool an
# LLM can reach should not have mainnet as its path of least resistance.
DEFAULT_CHAIN_ID = 11155111


class KeeperHubToolError(RuntimeError):
    """A failure worth showing the workflow author verbatim."""


def client_from(credentials: dict[str, Any]) -> KeeperHubMcpClient:
    """Build a client, failing with a readable reason rather than a 401.

    A `wfb_` workflow-builder key is the common mistake — it is a valid
    KeeperHub key that simply does not authenticate against the MCP surface.
    The kernel can tell the two apart, so say so.
    """
    api_key = (credentials or {}).get("api_key", "").strip()
    if not api_key:
        raise KeeperHubToolError("No KeeperHub API key configured for this provider.")

    if not is_org_api_key(api_key):
        warning = get_api_key_kind_warning(api_key) or (
            "This key is not organisation-scoped, so it cannot be used against "
            "KeeperHub's MCP surface. Use a kh_ key from Settings → API keys."
        )
        raise KeeperHubToolError(f"{warning} (key: {mask_api_key(api_key)})")

    return KeeperHubMcpClient(
        api_key,
        client_name="dify-plugin-keeperhub",
        client_version="0.1.0",
    )


def call(credentials: dict[str, Any], tool: str, arguments: dict[str, Any]) -> Any:
    """Invoke one KeeperHub MCP tool and return its unwrapped result.

    A simulation that reverts is NOT an error. KeeperHub answers a
    would-revert dry run with HTTP 400 and a body describing the revert, and
    the kernel turns any non-200 into an exception — so a successful
    simulation of a failing transaction would otherwise surface to the
    workflow author as "the tool broke". It didn't: it did its job, and the
    answer is "this would have failed, and here is why". That distinction is
    the entire value of simulating first, so it is recovered here.
    """
    kh = client_from(credentials)
    try:
        return kh.call_tool(tool, arguments)
    except Exception as exc:  # noqa: BLE001 — surfaced to the workflow author
        recovered = _recover_simulation_revert(exc, arguments)
        if recovered is not None:
            return recovered
        raise KeeperHubToolError(f"KeeperHub call `{tool}` failed: {exc}") from exc
    finally:
        kh.close()


def _recover_simulation_revert(
    exc: Exception, arguments: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    """Pull the simulation body out of a 400 and return it as data.

    Matches on the payload rather than the status line: the body is what says
    `status: simulated`, and keying off that means an unrelated 400 (a bad
    argument, a revoked key) still raises like the failure it is.
    """
    import json as _json
    import re as _re

    text = str(exc)
    # Not anchored to the end of the string: KeeperHub appends human guidance
    # ("Next step: ...") after the JSON, so an end-anchored match never fires.
    # Greedy from the first brace to the last captures the outer object even
    # though the body nests one.
    match = _re.search(r"\{.*\}", text, _re.DOTALL)
    if not match:
        return None
    try:
        body = _json.loads(match.group(0))
    except ValueError:
        return None
    if not isinstance(body, dict):
        return None

    # Only a dry run is safe to downgrade from error to data. If KeeperHub
    # ever reports a broadcast failure this way, it must keep raising.
    if body.get("status") != "simulated":
        return None

    body["simulationCompleted"] = True

    # KeeperHub decodes a custom error into `revertReason` when the caller's
    # ABI carries that error's definition, and otherwise reports "unknown
    # custom error" with raw bytes. An agent composing a call from a prompt
    # sends the function fragment and nothing else, so it lands in the second
    # case by default — and a raw selector is not something a model can act
    # on. We cannot decode it for them (the definition is the missing input,
    # not the computation), so say precisely what to add instead.
    raw = body.get("undecodedRevertData") or ""
    if isinstance(raw, str) and raw.startswith("0x"):
        body["revertSelector"] = raw[:10]
        body["revertReasonHint"] = (
            "This revert is a custom error KeeperHub could not name, because "
            "the ABI you sent describes only the function. Add the error "
            'definitions — {"type":"error","name":"YourError","inputs":[...]} '
            "— and the same simulation returns the decoded reason with its "
            "arguments instead of raw bytes."
        )
    return body


def parse_json_field(raw: str | None, field: str) -> Any:
    """Parse a JSON-typed tool parameter that arrives as a string.

    Dify passes tool parameters as strings, but KeeperHub wants real JSON for
    `abi` and `function_args`. Parsing here means the failure is named after
    the field the author actually typed into.
    """
    import json

    if raw is None or str(raw).strip() == "":
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise KeeperHubToolError(
            f"`{field}` is not valid JSON: {exc.msg} (at position {exc.pos})"
        ) from exc
