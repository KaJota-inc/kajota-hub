"""Coach as the merchant's autonomous CFO — deterministic release decisions.

The reframe of the escrow story: Coach doesn't just relay releases through
KeeperHub, it DECIDES. A small rules engine evaluates signals about the
deposit (escrow state, buyer/seller behaviour, dispute status, reputation,
amount bounds) and returns one of three verdicts:

    "release"  — every hard rule passed; safe to fire the KH workflow
    "hold"     — a hard rule failed; wait for the situation to change
    "reject"   — a hard rule failed in a way that will not resolve

The narration is separate: it turns the rule outcomes into plain English
for the merchant. Design invariant — **deterministic decides, LLM
explains**. The narrator never gets to override the verdict; it only
describes why the verdict was what it was.

Signals arrive from two places:
    1. On-chain state (escrow_state, buyer, seller, amount, timestamps) —
       read live via an RPC eth_call in production. For the hackathon
       demo the caller may supply them in the request body to keep the
       loop fast + deterministic during recording.
    2. Off-chain confirmations (buyer_confirmed, seller_shipped, prior
       reputation counts) — arrive via webhooks / marketplace signals.
       In production these are stored in the concierge's MongoDB. For
       the demo they're overridable via the request body too.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---- signals ------------------------------------------------------

@dataclass(frozen=True)
class ReleaseSignals:
    """Every input the rules engine needs to produce a verdict.

    Frozen because the rules engine must be a pure function of its
    inputs — no mutation, no hidden state. A given signal set always
    yields the same verdict; that's what makes the deterministic
    layer auditable.
    """

    deposit_id: str
    escrow_state: str            # "held" | "released" | "disputed" | "refunded"
    buyer: str                   # 0x-address
    seller: str                  # 0x-address
    gross_amount_raw: int        # USDC atomic units (6 decimals)
    listing_id: str
    deposited_at: int            # unix seconds
    now: int                     # unix seconds
    buyer_confirmed: bool        # buyer signalled "goods received"
    seller_shipped: bool         # seller signalled "shipped" or on-chain proof
    active_dispute: bool         # escrow contract's dispute flag
    prior_successful_releases_for_seller: int = 0
    prior_disputes_against_seller: int = 0
    max_amount_raw: int = 10_000_000_000   # 10 000 USDC default cap

    @property
    def days_since_deposit(self) -> float:
        return max(0, self.now - self.deposited_at) / 86400.0

    @property
    def seller_success_rate(self) -> float:
        total = (
            self.prior_successful_releases_for_seller
            + self.prior_disputes_against_seller
        )
        if total == 0:
            return 0.0
        return self.prior_successful_releases_for_seller / total

    def to_dict(self) -> dict[str, Any]:
        return {
            "depositId": self.deposit_id,
            "escrowState": self.escrow_state,
            "buyer": self.buyer,
            "seller": self.seller,
            "grossAmountRaw": str(self.gross_amount_raw),
            "grossAmountHuman": f"{self.gross_amount_raw / 1_000_000:.2f} USDC",
            "listingId": self.listing_id,
            "depositedAt": self.deposited_at,
            "now": self.now,
            "daysSinceDeposit": round(self.days_since_deposit, 2),
            "buyerConfirmed": self.buyer_confirmed,
            "sellerShipped": self.seller_shipped,
            "activeDispute": self.active_dispute,
            "sellerPriorSuccesses": self.prior_successful_releases_for_seller,
            "sellerPriorDisputes": self.prior_disputes_against_seller,
            "sellerSuccessRate": round(self.seller_success_rate, 3),
            "maxAmountRaw": str(self.max_amount_raw),
        }


# ---- rules --------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    """One evaluated rule. `weight` decides whether a failure is fatal."""

    name: str
    passed: bool
    detail: str
    weight: str  # "hard" | "soft"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "passed": self.passed,
            "detail": self.detail,
            "weight": self.weight,
        }


# Timeout after which a silent buyer is assumed to have accepted delivery.
# Long enough to give real disputes room to surface; short enough that a
# vanished buyer doesn't strand seller funds forever.
BUYER_TIMEOUT_DAYS = 7


def evaluate_rules(s: ReleaseSignals) -> list[Rule]:
    """Deterministic evaluation. Every branch is auditable."""

    rules: list[Rule] = []

    # ---- hard rules — any failure blocks release --------------------
    rules.append(Rule(
        name="escrow_held",
        passed=(s.escrow_state == "held"),
        detail=f"escrow state = '{s.escrow_state}' (expected 'held')",
        weight="hard",
    ))

    rules.append(Rule(
        name="no_active_dispute",
        passed=(not s.active_dispute),
        detail=(
            "an active dispute is on record — resolve it before releasing"
            if s.active_dispute
            else "no active dispute on this deposit"
        ),
        weight="hard",
    ))

    buyer_ok = s.buyer_confirmed or s.days_since_deposit > BUYER_TIMEOUT_DAYS
    if s.buyer_confirmed:
        buyer_detail = "buyer explicitly confirmed receipt"
    elif s.days_since_deposit > BUYER_TIMEOUT_DAYS:
        buyer_detail = (
            f"buyer silent for {s.days_since_deposit:.1f} days — past the "
            f"{BUYER_TIMEOUT_DAYS}-day acceptance window"
        )
    else:
        buyer_detail = (
            f"buyer has not confirmed and only {s.days_since_deposit:.1f} of "
            f"{BUYER_TIMEOUT_DAYS} days elapsed — need explicit confirmation "
            f"or the timeout to expire"
        )
    rules.append(Rule(
        name="buyer_confirmed_or_timeout",
        passed=buyer_ok,
        detail=buyer_detail,
        weight="hard",
    ))

    rules.append(Rule(
        name="seller_shipped",
        passed=s.seller_shipped,
        detail=(
            "seller has recorded a shipment signal"
            if s.seller_shipped
            else "no shipment signal yet — buyer has nothing to accept"
        ),
        weight="hard",
    ))

    within_cap = 0 < s.gross_amount_raw <= s.max_amount_raw
    rules.append(Rule(
        name="amount_within_bounds",
        passed=within_cap,
        detail=(
            f"{s.gross_amount_raw / 1_000_000:.2f} USDC is within the "
            f"per-release cap of {s.max_amount_raw / 1_000_000:.2f} USDC"
            if within_cap
            else f"{s.gross_amount_raw / 1_000_000:.2f} USDC exceeds the "
                 f"per-release cap of {s.max_amount_raw / 1_000_000:.2f} USDC"
        ),
        weight="hard",
    ))

    # ---- soft rules — logged, not blocking --------------------------
    total_prior = (
        s.prior_successful_releases_for_seller + s.prior_disputes_against_seller
    )
    if total_prior == 0:
        rep_ok = True
        rep_detail = "no prior history for this seller — first release"
    else:
        rep_ok = s.seller_success_rate >= 0.85 or s.prior_disputes_against_seller <= 2
        rep_detail = (
            f"seller has {s.prior_successful_releases_for_seller} successful "
            f"releases and {s.prior_disputes_against_seller} disputes "
            f"({s.seller_success_rate:.0%} success rate)"
        )
    rules.append(Rule(
        name="seller_reputation_ok",
        passed=rep_ok,
        detail=rep_detail,
        weight="soft",
    ))

    return rules


def decide(rules: list[Rule]) -> str:
    """Verdict from rule outcomes. Pure function of the rules list."""

    hard_fails = [r for r in rules if not r.passed and r.weight == "hard"]
    if not hard_fails:
        return "release"

    # If the escrow state itself is already terminal (released/refunded),
    # the situation won't resolve — reject rather than hold.
    for r in hard_fails:
        if r.name == "escrow_held" and "released" in r.detail:
            return "reject"
        if r.name == "escrow_held" and "refunded" in r.detail:
            return "reject"

    # Active dispute or amount-over-cap don't resolve on their own —
    # merchant needs to act. Reject to force attention.
    for r in hard_fails:
        if r.name == "no_active_dispute":
            return "reject"
        if r.name == "amount_within_bounds":
            return "reject"

    # Everything else is time-based: hold and re-check later.
    return "hold"


# ---- narration ----------------------------------------------------

def template_narration(
    signals: ReleaseSignals,
    rules: list[Rule],
    decision: str,
) -> str:
    """Plain-English explanation without any LLM call.

    Ships in production because it's deterministic, cheap, and never
    hallucinates. The LLM narrator (see ``llm_narration``) is optional
    polish on top of this baseline.
    """

    hard_fails = [r for r in rules if not r.passed and r.weight == "hard"]
    soft_fails = [r for r in rules if not r.passed and r.weight == "soft"]
    amount = f"{signals.gross_amount_raw / 1_000_000:.2f} USDC"

    if decision == "release":
        parts = [
            f"Releasing {amount} on deposit {_short(signals.deposit_id)}.",
        ]
        for r in rules:
            if r.name == "buyer_confirmed_or_timeout" and r.passed:
                parts.append(r.detail.capitalize() + ".")
                break
        if soft_fails:
            parts.append(
                "One soft concern noted: " + soft_fails[0].detail + "."
            )
        else:
            for r in rules:
                if r.name == "seller_reputation_ok":
                    parts.append(r.detail.capitalize() + ".")
                    break
        return " ".join(parts)

    if decision == "hold":
        parts = [
            f"Holding {amount} on deposit {_short(signals.deposit_id)}.",
        ]
        for r in hard_fails:
            parts.append(r.detail.capitalize() + ".")
        parts.append("Re-check when this changes.")
        return " ".join(parts)

    # reject
    parts = [
        f"Rejecting release for {amount} on deposit {_short(signals.deposit_id)} — merchant action required.",
    ]
    for r in hard_fails:
        parts.append(r.detail.capitalize() + ".")
    return " ".join(parts)


def _short(hex_or_str: str, n: int = 8) -> str:
    if hex_or_str.startswith("0x") and len(hex_or_str) > 2 * n + 4:
        return f"{hex_or_str[:n + 2]}…{hex_or_str[-n:]}"
    return hex_or_str


async def llm_narration(
    signals: ReleaseSignals,
    rules: list[Rule],
    decision: str,
) -> str | None:
    """LLM narration via Gemini. Returns None if Gemini is unavailable.

    Kept behind a try/except so a mis-configured Vertex environment
    downgrades cleanly to the template narration rather than 500ing.
    """
    try:
        from google import genai
        from google.genai import types as gen_types

        client = genai.Client()
        rule_lines = [
            f"- [{r.weight}] {r.name}: {'PASS' if r.passed else 'FAIL'} — {r.detail}"
            for r in rules
        ]
        prompt = (
            "You are Kajota Coach, the merchant's autonomous CFO. A deterministic "
            "rules engine has already made the release decision. Your job is to "
            "explain the decision to the merchant in TWO SHORT SENTENCES, plain "
            "English, no jargon.\n\n"
            "Do NOT contradict the decision. Do NOT invent facts not in the rules. "
            "Address the merchant directly (\"You…\").\n\n"
            f"Decision: {decision.upper()}\n"
            f"Deposit: {signals.deposit_id}\n"
            f"Amount: {signals.gross_amount_raw / 1_000_000:.2f} USDC\n"
            f"Rules evaluated:\n" + "\n".join(rule_lines)
        )
        # gemini-2.5-pro is a THINKING model: reasoning tokens are drawn
        # from max_output_tokens before any prose is emitted. At 180 the
        # budget was exhausted mid-thought and callers got fragments like
        # "We've released the 0". Disable thinking — this is a two-sentence
        # restatement of an already-made decision, not a reasoning task —
        # and leave real headroom.
        cfg = gen_types.GenerateContentConfig(
            temperature=0.2,
            max_output_tokens=400,
        )
        try:
            cfg.thinking_config = gen_types.ThinkingConfig(thinking_budget=0)
        except Exception:
            # Older SDKs / non-thinking models reject the field; the raised
            # ceiling alone is enough for them.
            pass

        result = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", "gemini-2.5-pro"),
            contents=prompt,
            config=cfg,
        )
        text = (result.text or "").strip()
        if not text:
            return None

        # Never ship a truncated narration. If the model still ran out of
        # room, the deterministic template is strictly better than half a
        # sentence: it's complete, and it states the same facts.
        if not text.endswith((".", "!", "?")):
            return None
        return text
    except Exception:
        return None


# ---- verdict ------------------------------------------------------

@dataclass(frozen=True)
class ReleaseVerdict:
    decision: str
    rules: list[Rule]
    why: str
    narrator: str  # "llm" | "template"
    signals: ReleaseSignals = field(repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision": self.decision,
            "why": self.why,
            "narrator": self.narrator,
            "rules": [r.to_dict() for r in self.rules],
            "signals": self.signals.to_dict(),
        }


async def evaluate(signals: ReleaseSignals, *, prefer_llm: bool = True) -> ReleaseVerdict:
    """End-to-end: rules → decision → narration."""

    rules = evaluate_rules(signals)
    decision = decide(rules)

    why: str | None = None
    narrator = "template"
    if prefer_llm:
        why = await llm_narration(signals, rules, decision)
        if why:
            narrator = "llm"
    if not why:
        why = template_narration(signals, rules, decision)

    return ReleaseVerdict(
        decision=decision,
        rules=rules,
        why=why,
        narrator=narrator,
        signals=signals,
    )


import os  # noqa: E402  keep bottom to avoid top-level side effects
