"""Coach's escrow tools — the bridge between the agent and the rules.

Until now the ADK agent (Gemini + MongoDB MCP) and the escrow decision
engine lived in the same process without ever speaking. The agent could
chat about purchases; the rules could decide releases; nothing connected
them. The submission claimed "Coach agent watches merchant catalogs" and
that was aspiration, not architecture.

These are plain Python functions with typed signatures and docstrings —
which is exactly what ADK turns into tool declarations. Handing them to
the agent means a merchant can write

    "someone paid for the Lagos order two weeks ago and has gone quiet —
     should I release it?"

and Coach will pick `should_release`, fill the signals from what it knows,
and come back with a verdict *and the rule that drove it*.

The division of labour is the whole point, and it is deliberate:

    the AGENT decides WHICH question to ask and with WHAT inputs
    the RULES decide WHAT THE ANSWER IS

An LLM choosing to call `should_release` is fine. An LLM deciding that a
release is warranted is not — so it cannot. Every tool here either
returns a rules-engine verdict or a classification that feeds one. None
of them move money; releasing still goes through the KeeperHub workflow,
which only the escrow's registered keeper can trigger.
"""

from __future__ import annotations

import time
from typing import Any

from kajota_concierge.coach_cfo import ReleaseSignals, evaluate as _evaluate
from kajota_concierge.coach_auditor import audit_workflow as _audit
from kajota_concierge.coach_triage import triage_message as _triage


async def should_release(
    deposit_id: str,
    gross_amount_usdc: float = 0.10,
    buyer_confirmed: bool = False,
    seller_shipped: bool = True,
    active_dispute: bool = False,
    days_since_deposit: float = 0.0,
    prior_successful_releases: int = 0,
    prior_disputes: int = 0,
) -> dict[str, Any]:
    """Decide whether an escrowed deposit should be released to the seller.

    Use this whenever someone asks if a payment can be released, paid out,
    settled, or sent to the seller. Returns a verdict of "release", "hold",
    or "reject", together with every rule that was evaluated and a
    plain-English explanation.

    You do not decide the outcome — this tool does. Report its verdict and
    its reasoning faithfully, including when it declines to release.

    Args:
        deposit_id: The escrow deposit id, 0x-prefixed 32-byte hex.
        gross_amount_usdc: Deposit size in USDC, e.g. 0.10.
        buyer_confirmed: True if the buyer has confirmed they received the goods.
        seller_shipped: True if the seller has recorded a shipment.
        active_dispute: True if a dispute is open on this deposit.
        days_since_deposit: How long the funds have been in escrow.
        prior_successful_releases: The seller's completed sales.
        prior_disputes: Disputes previously raised against this seller.

    Returns:
        decision, why, narrator, and the full list of evaluated rules.
    """
    now = int(time.time())
    verdict = await _evaluate(
        ReleaseSignals(
            deposit_id=deposit_id,
            escrow_state="held",
            buyer="0x" + "00" * 20,
            seller="0x" + "00" * 20,
            gross_amount_raw=int(round(gross_amount_usdc * 1_000_000)),
            listing_id="0x" + "00" * 32,
            deposited_at=now - int(days_since_deposit * 86400),
            now=now,
            buyer_confirmed=buyer_confirmed,
            seller_shipped=seller_shipped,
            active_dispute=active_dispute,
            prior_successful_releases_for_seller=prior_successful_releases,
            prior_disputes_against_seller=prior_disputes,
        ),
        prefer_llm=False,  # the agent does the talking; keep this deterministic
    )
    return {
        "decision": verdict.decision,
        "why": verdict.why,
        "rules": [r.to_dict() for r in verdict.rules],
        "failingRules": [r.name for r in verdict.rules if not r.passed],
    }


async def triage_buyer_message(message: str) -> dict[str, Any]:
    """Judge whether a free-text buyer message is a genuine dispute.

    Use this when a buyer has written something and you need to know
    whether it should block a release. Feed the `isDispute` result into
    `should_release` as `active_dispute`.

    Args:
        message: The buyer's message, verbatim.

    Returns:
        isDispute, severity, category, summary, classifier, confidence.
    """
    return (await _triage(message)).to_dict()


async def audit_keeperhub_workflow(workflow_json: dict[str, Any]) -> dict[str, Any]:
    """Check a KeeperHub workflow for the field-name traps that break it silently.

    Use this before anyone runs a `web3/write-contract` workflow, or when
    someone asks why their workflow isn't behaving. Catches the traps
    documented in KeeperHub/keeperhub#1857 — a reserved key that's accepted
    then ignored, JSON-string fields passed as raw arrays, and a template
    syntax that only resolves in stored workflows.

    Args:
        workflow_json: The workflow definition — name, nodes, edges.

    Returns:
        passed, counts by severity, and an issue list with a fix per issue.
    """
    return _audit(workflow_json, workflow_ref="agent-tool").to_dict()


# ADK reads this list to build the agent's toolset.
ESCROW_TOOLS = [should_release, triage_buyer_message, audit_keeperhub_workflow]
