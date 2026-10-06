"""Validate the plugin's YAML against Dify's own models.

This is the check that matters before install: Dify parses manifest.yaml,
the provider spec and every tool spec through these exact pydantic models,
so if they construct here they will load there. Catches the failure mode a
unit test cannot — a plugin whose logic is perfect and whose manifest Dify
refuses.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dify_plugin.core.entities.plugin.setup import PluginConfiguration  # noqa: E402
from dify_plugin.entities.tool import (  # noqa: E402
    ToolConfiguration,
    ToolProviderConfiguration,
)

TOOLS = ("simulate_call", "execute_call", "run_workflow")


def _load(rel: str):
    return yaml.safe_load((ROOT / rel).read_text())


def test_manifest_is_valid():
    m = PluginConfiguration(**_load("manifest.yaml"))
    assert m.name == "keeperhub"
    assert m.meta.runner.language.value == "python"


def test_provider_is_valid_and_declares_one_credential():
    p = ToolProviderConfiguration(**_load("provider/keeperhub.yaml"))
    assert p.identity.name == "keeperhub"
    assert [c.name for c in p.credentials_schema] == ["api_key"]


def test_provider_declares_every_tool_that_exists():
    p = ToolProviderConfiguration(**_load("provider/keeperhub.yaml"))
    assert {t.identity.name for t in p.tools} == set(TOOLS)


def test_every_tool_spec_is_valid():
    for name in TOOLS:
        c = ToolConfiguration(**_load(f"tools/{name}.yaml"))
        assert c.identity.name == name
        assert c.extra.python.source == f"tools/{name}.py"


def test_declared_python_sources_all_exist_on_disk():
    p = ToolProviderConfiguration(**_load("provider/keeperhub.yaml"))
    assert (ROOT / p.extra.python.source).is_file()
    for name in TOOLS:
        c = ToolConfiguration(**_load(f"tools/{name}.yaml"))
        assert (ROOT / c.extra.python.source).is_file()


def test_the_guarded_flag_defaults_to_false_in_the_spec():
    """The spec must not ship a default that executes."""
    c = ToolConfiguration(**_load("tools/execute_call.yaml"))
    flag = next(p for p in c.parameters if p.name == "acknowledge_moves_value")
    assert flag.default in (False, "false", None)
    assert flag.required is False


def test_chain_id_defaults_to_sepolia_in_both_call_tools():
    for name in ("simulate_call", "execute_call"):
        c = ToolConfiguration(**_load(f"tools/{name}.yaml"))
        chain = next(p for p in c.parameters if p.name == "chain_id")
        assert str(chain.default) == "11155111"


def test_simulate_tool_exposes_no_execute_flag():
    """simulate_call must have no way for a caller to ask it to broadcast."""
    c = ToolConfiguration(**_load("tools/simulate_call.yaml"))
    names = {p.name for p in c.parameters}
    assert "acknowledge_moves_value" not in names
    assert "simulate" not in names
