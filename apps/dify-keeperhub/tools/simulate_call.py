from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._kh import DEFAULT_CHAIN_ID, KeeperHubToolError, call, parse_json_field


class SimulateCallTool(Tool):
    """Simulate a contract call through KeeperHub without signing it.

    This tool cannot move value. It passes `simulate: true` unconditionally,
    which KeeperHub honours by evaluating the call without signing or
    broadcasting. It is the tool an agent should reach for first, and the
    only one of the three that is safe to let a model call unsupervised.
    """

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        try:
            args = _build_call_args(tool_parameters)
            # Not configurable. A tool named "simulate" that could broadcast
            # would be the exact ambiguity this plugin exists to remove.
            args["simulate"] = True
            result = call(self.runtime.credentials, "execute_contract_call", args)
        except KeeperHubToolError as exc:
            yield self.create_text_message(str(exc))
            return

        yield self.create_json_message(
            {"simulated": True, "signed": False, "broadcast": False, "result": result}
        )
        yield self.create_text_message(
            "Simulated only — nothing was signed or broadcast. To execute this "
            "exact call, use `execute_call` with the same arguments and set "
            "`acknowledge_moves_value` to true."
        )


def _build_call_args(p: dict[str, Any]) -> dict[str, Any]:
    contract = (p.get("contract_address") or "").strip()
    function_name = (p.get("function_name") or "").strip()
    if not contract:
        raise KeeperHubToolError("`contract_address` is required.")
    if not function_name:
        raise KeeperHubToolError("`function_name` is required.")

    abi = parse_json_field(p.get("abi"), "abi")
    if abi is None:
        raise KeeperHubToolError(
            "`abi` is required — paste the JSON ABI fragment for just this "
            'function, e.g. [{"type":"function","name":"release",'
            '"inputs":[{"name":"depositId","type":"bytes32"}],"outputs":[]}]'
        )

    args: dict[str, Any] = {
        "contract_address": contract,
        "function_name": function_name,
        "abi": abi,
        "chain_id": int(p.get("chain_id") or DEFAULT_CHAIN_ID),
    }

    function_args = parse_json_field(p.get("function_args"), "function_args")
    if function_args is not None:
        if not isinstance(function_args, list):
            raise KeeperHubToolError(
                "`function_args` must be a JSON array, e.g. [\"0xabc…\"]"
            )
        args["function_args"] = function_args

    value = (p.get("value") or "").strip()
    if value:
        args["value"] = value
    return args
