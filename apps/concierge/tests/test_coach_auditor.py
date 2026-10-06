"""Tests for the KH workflow auditor.

Covers every trap in the catalogue plus the clean-workflow happy path.
Pure functions of their input — no HTTP, no I/O, deterministic.
"""

from __future__ import annotations

from kajota_concierge.coach_auditor import (
    SEVERITY_ERROR,
    SEVERITY_INFO,
    SEVERITY_WARN,
    audit_workflow,
)


def _clean_workflow() -> dict:
    """The minimal correct workflow that should audit clean."""
    return {
        "name": "Release escrow on Sepolia",
        "nodes": [
            {
                "id": "trigger-1",
                "type": "trigger",
                "data": {
                    "label": "HTTP",
                    "config": {"triggerType": "HTTP", "httpMethod": "POST"},
                },
            },
            {
                "id": "step-1",
                "type": "action",
                "data": {
                    "label": "Release Escrow",
                    "config": {
                        "actionType": "web3/write-contract",
                        "network": "11155111",
                        "web3Connection": "default",
                        "contractAddress": "0x599869cef2e4c52e2c9074caaf8f9fb0cb191776",
                        "abiFunction": "release",
                        "functionArgs": '["{{@trigger-1:HTTP.depositId}}"]',
                        "abi": '[{"type":"function","name":"release","stateMutability":"nonpayable","inputs":[{"name":"depositId","type":"bytes32"}],"outputs":[]}]',
                    },
                },
            },
        ],
        "edges": [{"id": "e", "source": "trigger-1", "target": "step-1"}],
    }


# ---- happy path ---------------------------------------------------

def test_clean_workflow_passes():
    r = audit_workflow(_clean_workflow())
    assert r.passed
    # We WILL always emit the HTTP-body-wrap info reminder when an HTTP
    # trigger is present — that's a design choice, not a failure.
    assert r.error_count == 0
    assert r.warn_count == 0
    assert r.info_count == 1  # the http-body-wrap-reminder
    assert "Clean audit" in r.summary


def test_action_nodes_count_is_reported():
    r = audit_workflow(_clean_workflow())
    assert r.action_nodes_scanned == 1


def test_no_action_nodes_returns_no_issues_but_helpful_summary():
    wf = {"name": "notify only", "nodes": [], "edges": []}
    r = audit_workflow(wf)
    assert r.passed
    assert r.action_nodes_scanned == 0
    assert "nothing to audit" in r.summary


# ---- trap 1 family: function key ----------------------------------

def test_error_when_function_key_is_rejected_alias_function():
    wf = _clean_workflow()
    cfg = wf["nodes"][1]["data"]["config"]
    del cfg["abiFunction"]
    cfg["function"] = "release"
    r = audit_workflow(wf)
    assert not r.passed
    traps = [i.trap for i in r.issues]
    assert "rejected-function-alias" in traps
    assert "missing-abi-function" in traps


def test_error_when_function_key_is_rejected_alias_method():
    wf = _clean_workflow()
    cfg = wf["nodes"][1]["data"]["config"]
    del cfg["abiFunction"]
    cfg["method"] = "release"
    r = audit_workflow(wf)
    assert not r.passed
    assert any(i.trap == "rejected-function-alias" and i.severity == SEVERITY_ERROR for i in r.issues)


def test_warn_but_not_fail_when_only_legacy_functionName_alias_is_used():
    wf = _clean_workflow()
    cfg = wf["nodes"][1]["data"]["config"]
    del cfg["abiFunction"]
    cfg["functionName"] = "release"
    r = audit_workflow(wf)
    # No hard error — functionName is accepted. But we warn.
    assert r.passed
    assert any(i.trap == "legacy-function-alias" and i.severity == SEVERITY_WARN for i in r.issues)


def test_error_when_neither_canonical_nor_alias_present():
    wf = _clean_workflow()
    del wf["nodes"][1]["data"]["config"]["abiFunction"]
    r = audit_workflow(wf)
    assert not r.passed
    assert any(i.trap == "missing-abi-function" for i in r.issues)


# ---- trap 2 family: functionArgs shape ---------------------------

def test_error_when_functionArgs_is_raw_array():
    wf = _clean_workflow()
    wf["nodes"][1]["data"]["config"]["functionArgs"] = ["{{@trigger-1:HTTP.depositId}}"]
    r = audit_workflow(wf)
    assert not r.passed
    hit = next(i for i in r.issues if i.trap == "function-args-raw-array")
    assert hit.severity == SEVERITY_ERROR
    assert "JSON-encoded string" in hit.fix or "wrap in a JSON-encoded" in hit.fix


def test_error_when_functionArgs_is_random_string_not_json():
    wf = _clean_workflow()
    wf["nodes"][1]["data"]["config"]["functionArgs"] = "not json here"
    r = audit_workflow(wf)
    assert any(i.trap == "function-args-not-json-string" for i in r.issues)


# ---- trap 3 family: abi shape -------------------------------------

def test_error_when_abi_is_raw_array():
    wf = _clean_workflow()
    wf["nodes"][1]["data"]["config"]["abi"] = [{"type": "function", "name": "release"}]
    r = audit_workflow(wf)
    assert any(i.trap == "abi-raw-array" for i in r.issues)


def test_error_when_abi_is_random_string():
    wf = _clean_workflow()
    wf["nodes"][1]["data"]["config"]["abi"] = "not-json"
    r = audit_workflow(wf)
    assert any(i.trap == "abi-not-json-string" for i in r.issues)


# ---- trap 4 family: web3Connection vs integrationId ---------------

def test_error_when_integrationId_is_used_instead_of_web3Connection():
    wf = _clean_workflow()
    cfg = wf["nodes"][1]["data"]["config"]
    del cfg["web3Connection"]
    cfg["integrationId"] = "int_your-keeper-here"
    r = audit_workflow(wf)
    assert not r.passed
    hit = next(i for i in r.issues if i.trap == "silently-ignored-integration-id")
    assert hit.severity == SEVERITY_ERROR
    assert "web3Connection" in hit.fix


def test_error_when_web3Connection_value_is_invalid():
    wf = _clean_workflow()
    wf["nodes"][1]["data"]["config"]["web3Connection"] = "arbitrary-value"
    r = audit_workflow(wf)
    assert any(i.trap == "invalid-web3-connection-value" for i in r.issues)


def test_safe_prefix_value_is_accepted():
    wf = _clean_workflow()
    wf["nodes"][1]["data"]["config"]["web3Connection"] = "safe:abc-123"
    r = audit_workflow(wf)
    assert r.passed


# ---- trap 5: network shape ----------------------------------------

def test_warn_when_network_is_a_number_not_a_string():
    wf = _clean_workflow()
    wf["nodes"][1]["data"]["config"]["network"] = 11155111
    r = audit_workflow(wf)
    hit = next(i for i in r.issues if i.trap == "network-numeric-not-string")
    assert hit.severity == SEVERITY_WARN
    # Warnings alone don't block
    assert r.passed


# ---- trap 6: broken trigger templates ------------------------------

def test_error_when_broken_trigger_body_template_is_used():
    wf = _clean_workflow()
    wf["nodes"][1]["data"]["config"]["functionArgs"] = '["{{@trigger.body.depositId}}"]'
    r = audit_workflow(wf)
    assert not r.passed
    hit = next(i for i in r.issues if i.trap == "broken-trigger-template")
    assert hit.severity == SEVERITY_ERROR
    assert "{{@trigger-1:HTTP.depositId}}" in hit.fix


# ---- HTTP body wrap info reminder ---------------------------------

def test_http_trigger_emits_body_wrap_info():
    r = audit_workflow(_clean_workflow())
    assert any(
        i.trap == "http-body-wrap-reminder" and i.severity == SEVERITY_INFO
        for i in r.issues
    )


def test_no_http_trigger_no_body_wrap_info():
    wf = _clean_workflow()
    wf["nodes"] = wf["nodes"][1:]  # drop the HTTP trigger
    r = audit_workflow(wf)
    assert not any(i.trap == "http-body-wrap-reminder" for i in r.issues)


# ---- multi-issue workflow -----------------------------------------

def test_workflow_with_every_trap_fails_and_reports_all():
    wf = {
        "name": "kitchen sink of wrong",
        "nodes": [
            {
                "id": "t",
                "type": "trigger",
                "data": {"label": "HTTP", "config": {"triggerType": "HTTP"}},
            },
            {
                "id": "s",
                "type": "action",
                "data": {
                    "label": "wrong",
                    "config": {
                        "actionType": "web3/write-contract",
                        "network": 11155111,                       # warn
                        "integrationId": "int_wrong",              # error
                        "contractAddress": "0xdead",
                        "function": "release",                     # error (rejected)
                        "abi": [{"raw": True}],                    # error (raw array)
                        "functionArgs": ["{{@trigger.body.x}}"],   # error (raw array + broken template)
                    },
                },
            },
        ],
        "edges": [],
    }
    r = audit_workflow(wf)
    assert not r.passed
    traps = {i.trap for i in r.issues}
    assert {
        "rejected-function-alias",
        "missing-abi-function",
        "function-args-raw-array",
        "abi-raw-array",
        "silently-ignored-integration-id",
        "network-numeric-not-string",
        "http-body-wrap-reminder",
    }.issubset(traps)
    assert r.error_count >= 4
    assert r.warn_count >= 1
    assert r.info_count >= 1
