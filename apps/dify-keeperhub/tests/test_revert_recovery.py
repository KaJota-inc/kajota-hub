"""A simulation that reverts is a result, not a failure.

KeeperHub answers a would-revert dry run with HTTP 400, and the MCP kernel
turns any non-200 into an exception. Left alone, that makes the single most
useful outcome of simulating — "this would have failed, here is why" — look
to a Dify author like a broken tool. These tests pin the recovery, and just
as importantly pin what must STILL raise.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools._kh import _recover_simulation_revert  # noqa: E402

# Shape copied from a real 400 returned by app.keeperhub.com, including the
# human guidance KeeperHub appends AFTER the JSON — which is what broke the
# first end-anchored version of the parser.
SIM_BODY = (
    'KeeperHub tool error (execute_contract_call): API call failed: 400 Bad Request - '
    '{"success":false,"status":"simulated","from":"0x4c62","to":"0x5998",'
    '"failureKind":"revert","wouldRevert":true,'
    '"revertReason":"Simulation reverted: unknown custom error",'
    '"undecodedRevertData":"0x9cd29bc9e713d5a3"}\n\n'
    "Simulation reverted. Nothing was signed or broadcast.\n"
    "Next step:\n  - Fix the cause, then re-run.\n"
)


def test_simulated_revert_is_returned_as_data():
    body = _recover_simulation_revert(Exception(SIM_BODY), {})
    assert body is not None
    assert body["wouldRevert"] is True
    assert body["simulationCompleted"] is True


def test_trailing_prose_after_json_still_parses():
    """The first implementation anchored to end-of-string and never matched."""
    assert _recover_simulation_revert(Exception(SIM_BODY), {}) is not None


def test_selector_and_hint_when_abi_lacks_error_defs():
    body = _recover_simulation_revert(Exception(SIM_BODY), {"abi": []})
    assert body["revertSelector"] == "0x9cd29bc9"
    assert "error" in body["revertReasonHint"].lower()


def test_a_broadcast_failure_must_still_raise():
    """Only a dry run may be downgraded from error to data."""
    broadcast = SIM_BODY.replace('"status":"simulated"', '"status":"broadcast"')
    assert _recover_simulation_revert(Exception(broadcast), {}) is None


def test_unrelated_error_still_raises():
    assert _recover_simulation_revert(Exception("401 Unauthorized"), {}) is None


def test_malformed_json_still_raises():
    bad = 'API call failed: 400 - {"status":"simulated", truncated'
    assert _recover_simulation_revert(Exception(bad), {}) is None


def test_non_dict_json_still_raises():
    assert _recover_simulation_revert(Exception('400 - ["simulated"]'), {}) is None


def test_call_surfaces_recovery_instead_of_raising(monkeypatch):
    """End to end through `call`, with the kernel stubbed to raise a 400."""
    import tools._kh as kh

    class FakeClient:
        def call_tool(self, name, arguments=None):
            raise RuntimeError(SIM_BODY)

        def close(self):
            pass

    monkeypatch.setattr(kh, "client_from", lambda creds: FakeClient())
    out = kh.call({"api_key": "kh_x"}, "execute_contract_call", {"abi": []})
    assert out["wouldRevert"] is True


def test_call_still_raises_for_a_real_failure(monkeypatch):
    import tools._kh as kh

    class FakeClient:
        def call_tool(self, name, arguments=None):
            raise RuntimeError("API call failed: 401 Unauthorized")

        def close(self):
            pass

    monkeypatch.setattr(kh, "client_from", lambda creds: FakeClient())
    with pytest.raises(kh.KeeperHubToolError):
        kh.call({"api_key": "kh_x"}, "execute_contract_call", {})
