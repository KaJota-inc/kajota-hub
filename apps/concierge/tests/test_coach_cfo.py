"""Tests for the CFO rules engine.

The rules engine is a pure function of its inputs; every branch is
tested here. Narration + LLM downgrade paths are tested at the
integration level in the endpoint tests.
"""

from __future__ import annotations

import pytest

from kajota_concierge.coach_cfo import (
    BUYER_TIMEOUT_DAYS,
    ReleaseSignals,
    decide,
    evaluate_rules,
    template_narration,
)


NOW = 1_754_000_000  # arbitrary fixed unix time used across tests
BUYER = "0xb0000000000000000000000000000000000000b0"
SELLER = "0x5e11e50000000000000000000000000000000000"
DEPOSIT = "0xd0a1d0a1d0a1d0a1d0a1d0a1d0a1d0a1d0a1d0a1d0a1d0a1d0a1d0a1d0a1d0a1"
LISTING = "0x1157" + "00" * 30


def _base_signals(**overrides) -> ReleaseSignals:
    defaults = dict(
        deposit_id=DEPOSIT,
        escrow_state="held",
        buyer=BUYER,
        seller=SELLER,
        gross_amount_raw=100_000,          # 0.10 USDC
        listing_id=LISTING,
        deposited_at=NOW - 3600,           # 1h ago
        now=NOW,
        buyer_confirmed=True,
        seller_shipped=True,
        active_dispute=False,
        prior_successful_releases_for_seller=10,
        prior_disputes_against_seller=0,
    )
    defaults.update(overrides)
    return ReleaseSignals(**defaults)


# ---- happy path ----------------------------------------------------

def test_happy_path_releases():
    verdict = decide(evaluate_rules(_base_signals()))
    assert verdict == "release"


def test_narration_release_mentions_amount_and_deposit():
    s = _base_signals()
    text = template_narration(s, evaluate_rules(s), "release")
    assert "0.10 USDC" in text
    # short deposit id in the narration
    assert DEPOSIT[:10] in text


# ---- hard-rule failures -------------------------------------------

def test_hold_when_seller_not_shipped():
    s = _base_signals(seller_shipped=False)
    assert decide(evaluate_rules(s)) == "hold"


def test_hold_when_buyer_silent_within_window():
    s = _base_signals(buyer_confirmed=False, deposited_at=NOW - 3600)
    assert decide(evaluate_rules(s)) == "hold"


def test_release_when_buyer_silent_past_timeout():
    past_timeout = NOW - int((BUYER_TIMEOUT_DAYS + 1) * 86400)
    s = _base_signals(buyer_confirmed=False, deposited_at=past_timeout)
    assert decide(evaluate_rules(s)) == "release"


def test_reject_when_active_dispute():
    s = _base_signals(active_dispute=True)
    assert decide(evaluate_rules(s)) == "reject"


def test_reject_when_amount_over_cap():
    s = _base_signals(
        gross_amount_raw=20_000_000_000,   # 20 000 USDC > 10 000 cap
    )
    assert decide(evaluate_rules(s)) == "reject"


def test_reject_when_escrow_already_released():
    s = _base_signals(escrow_state="released")
    assert decide(evaluate_rules(s)) == "reject"


def test_reject_when_escrow_already_refunded():
    s = _base_signals(escrow_state="refunded")
    assert decide(evaluate_rules(s)) == "reject"


def test_hold_when_escrow_in_unknown_pending_state():
    # An unrecognised state that isn't terminal → hold to be safe.
    s = _base_signals(escrow_state="pending")
    assert decide(evaluate_rules(s)) == "hold"


# ---- soft rules do not block --------------------------------------

def test_soft_reputation_failure_still_releases():
    # 5 successes / 10 disputes = 33% success rate, > 2 disputes.
    # Hard rules all pass ⇒ verdict is release; soft rule just logs.
    s = _base_signals(
        prior_successful_releases_for_seller=5,
        prior_disputes_against_seller=10,
    )
    rules = evaluate_rules(s)
    assert decide(rules) == "release"
    rep_rule = next(r for r in rules if r.name == "seller_reputation_ok")
    assert not rep_rule.passed


def test_new_seller_reputation_passes_by_default():
    s = _base_signals(
        prior_successful_releases_for_seller=0,
        prior_disputes_against_seller=0,
    )
    rules = evaluate_rules(s)
    rep_rule = next(r for r in rules if r.name == "seller_reputation_ok")
    assert rep_rule.passed
    assert "first release" in rep_rule.detail


# ---- narration content --------------------------------------------

def test_narration_hold_says_hold_and_lists_reason():
    s = _base_signals(seller_shipped=False)
    text = template_narration(s, evaluate_rules(s), "hold")
    assert text.startswith("Holding")
    assert "shipment" in text.lower()


def test_narration_reject_mentions_merchant_action():
    s = _base_signals(active_dispute=True)
    text = template_narration(s, evaluate_rules(s), "reject")
    assert text.startswith("Rejecting")
    assert "merchant action" in text.lower()


# ---- determinism guard --------------------------------------------

def test_same_signals_same_verdict():
    """Rules engine must be a pure function of its inputs."""
    s = _base_signals(seller_shipped=False)
    r1 = decide(evaluate_rules(s))
    r2 = decide(evaluate_rules(s))
    r3 = decide(evaluate_rules(_base_signals(seller_shipped=False)))
    assert r1 == r2 == r3
