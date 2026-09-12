"""The guardrail is the whole point of this plugin, so it is tested directly.

These tests never touch the network. They substitute the KeeperHub call with
a recorder and assert on what the tools *would* have sent — which is the only
way to prove "simulate cannot broadcast" without broadcasting something.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import _kh  # noqa: E402
from tools.simulate_call import _build_call_args  # noqa: E402

ABI = '[{"type":"function","name":"release","inputs":[{"name":"d","type":"bytes32"}],"outputs":[]}]'
BASE = {
    "contract_address": "0x599869cef2e4c52e2c9074caaf8f9fb0cb191776",
    "function_name": "release",
    "abi": ABI,
    "function_args": '["0xdead"]',
}


class Recorder:
    """Stands in for the KeeperHub MCP call and remembers the arguments."""

    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, _credentials, tool, arguments):
        self.calls.append((tool, dict(arguments)))
        return {"ok": True, "transactionHash": "0xabc123"}


def _tool(cls, monkeypatch, rec):
    """Instantiate a Dify Tool without the plugin runtime."""
    import tools.execute_call as ec
    import tools.simulate_call as sc

    monkeypatch.setattr(sc, "call", rec, raising=True)
    monkeypatch.setattr(ec, "call", rec, raising=True)

    t = cls.__new__(cls)  # bypass Tool.__init__, which wants a runtime
    class _RT:
        credentials = {"api_key": "kh_test"}
    t.runtime = _RT()
    t.create_text_message = lambda s: ("text", s)
    t.create_json_message = lambda d: ("json", d)
    return t


# ---------------------------------------------------------------- simulate
def test_simulate_always_sets_simulate_true(monkeypatch):
    from tools.simulate_call import SimulateCallTool

    rec = Recorder()
    t = _tool(SimulateCallTool, monkeypatch, rec)
    list(t._invoke(dict(BASE)))

    assert len(rec.calls) == 1
    tool, args = rec.calls[0]
    assert tool == "execute_contract_call"
    assert args["simulate"] is True


def test_simulate_cannot_be_overridden_by_caller(monkeypatch):
    """A caller passing simulate=false must still only simulate."""
    from tools.simulate_call import SimulateCallTool

    rec = Recorder()
    t = _tool(SimulateCallTool, monkeypatch, rec)
    list(t._invoke({**BASE, "simulate": False, "acknowledge_moves_value": True}))

    assert rec.calls[0][1]["simulate"] is True


# ---------------------------------------------------------------- execute
def test_execute_without_acknowledgement_does_not_broadcast(monkeypatch):
    from tools.execute_call import ExecuteCallTool

    rec = Recorder()
    t = _tool(ExecuteCallTool, monkeypatch, rec)
    out = list(t._invoke(dict(BASE)))  # flag absent

    assert all(args["simulate"] is True for _, args in rec.calls), (
        "an unacknowledged execute must never send simulate=false"
    )
    payload = next(v for kind, v in out if kind == "json")
    assert payload["executed"] is False
    assert payload["simulated_instead"] is True


@pytest.mark.parametrize("flag", [False, "false", "no", "", None, 0])
def test_execute_refuses_for_every_falsey_flag(monkeypatch, flag):
    from tools.execute_call import ExecuteCallTool

    rec = Recorder()
    t = _tool(ExecuteCallTool, monkeypatch, rec)
    list(t._invoke({**BASE, "acknowledge_moves_value": flag}))
    assert all(args["simulate"] is True for _, args in rec.calls)


@pytest.mark.parametrize("flag", [True, "true", "True", "yes", "1"])
def test_execute_broadcasts_only_when_acknowledged(monkeypatch, flag):
    from tools.execute_call import ExecuteCallTool

    rec = Recorder()
    t = _tool(ExecuteCallTool, monkeypatch, rec)
    out = list(t._invoke({**BASE, "acknowledge_moves_value": flag}))

    assert rec.calls[-1][1]["simulate"] is False
    payload = next(v for kind, v in out if kind == "json")
    assert payload["executed"] is True
    assert payload["transactionHash"] == "0xabc123"


# ---------------------------------------------------------------- arguments
def test_defaults_to_sepolia_not_mainnet():
    args = _build_call_args(dict(BASE))
    assert args["chain_id"] == 11155111


def test_missing_abi_names_the_field():
    with pytest.raises(_kh.KeeperHubToolError, match="abi"):
        _build_call_args({k: v for k, v in BASE.items() if k != "abi"})


def test_bad_json_names_the_field_the_author_typed():
    with pytest.raises(_kh.KeeperHubToolError, match="function_args"):
        _build_call_args({**BASE, "function_args": "[not json"})


def test_function_args_must_be_a_list():
    with pytest.raises(_kh.KeeperHubToolError, match="JSON array"):
        _build_call_args({**BASE, "function_args": '{"a":1}'})


# ---------------------------------------------------------------- credentials
def test_wfb_key_is_rejected_with_a_readable_reason():
    with pytest.raises(_kh.KeeperHubToolError) as exc:
        _kh.client_from({"api_key": "wfb_not_for_mcp"})
    assert "wfb" in str(exc.value).lower() or "organisation" in str(exc.value).lower()


def test_missing_key_is_rejected():
    with pytest.raises(_kh.KeeperHubToolError, match="No KeeperHub API key"):
        _kh.client_from({})


def test_error_never_leaks_the_key():
    try:
        _kh.client_from({"api_key": "wfb_SUPERSECRETVALUE123"})
    except _kh.KeeperHubToolError as exc:
        assert "SUPERSECRETVALUE123" not in str(exc)
