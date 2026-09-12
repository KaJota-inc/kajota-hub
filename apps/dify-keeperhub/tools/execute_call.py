from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._kh import KeeperHubToolError, call
from tools.simulate_call import _build_call_args


class ExecuteCallTool(Tool):
    """Execute a contract call through KeeperHub. This one moves value.

    Guarded by an explicit acknowledgement rather than a confirmation dialog,
    because a tool call has no UI to show one. The guard is not decoration: a
    model that reaches for this tool without setting the flag gets a refusal
    and a simulation, so the default outcome of an ambiguous decision is that
    nothing irreversible happens.
    """

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        acknowledged = _truthy(tool_parameters.get("acknowledge_moves_value"))

        try:
            args = _build_call_args(tool_parameters)
        except KeeperHubToolError as exc:
            yield self.create_text_message(str(exc))
            return

        if not acknowledged:
            # Refuse, but do something useful: simulate instead, so the caller
            # sees the outcome it was about to sign for.
            try:
                args["simulate"] = True
                preview = call(
                    self.runtime.credentials, "execute_contract_call", args
                )
            except KeeperHubToolError as exc:
                yield self.create_text_message(str(exc))
                return

            yield self.create_json_message(
                {
                    "executed": False,
                    "reason": "acknowledge_moves_value was not set to true",
                    "simulated_instead": True,
                    "result": preview,
                }
            )
            yield self.create_text_message(
                "Refused to execute: this call moves value onchain and "
                "`acknowledge_moves_value` was not true. Simulated it instead — "
                "the outcome is above. Set the flag to execute this exact call."
            )
            return

        args["simulate"] = False
        try:
            result = call(self.runtime.credentials, "execute_contract_call", args)
        except KeeperHubToolError as exc:
            yield self.create_text_message(str(exc))
            return

        tx = _find_tx_hash(result)
        yield self.create_json_message(
            {"executed": True, "simulated": False, "transactionHash": tx, "result": result}
        )
        yield self.create_text_message(
            f"Executed through KeeperHub. Transaction: {tx}"
            if tx
            else "Executed through KeeperHub; no transaction hash returned yet — "
            "KeeperHub submits asynchronously, so check the run in its audit trail."
        )


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in {"true", "1", "yes", "y"}


def _find_tx_hash(result: Any) -> str | None:
    """Pull a tx hash out of the response without assuming its shape."""
    if isinstance(result, dict):
        for key in ("transactionHash", "transaction_hash", "transaction", "txHash"):
            v = result.get(key)
            if isinstance(v, str) and v.startswith("0x"):
                return v
        for v in result.values():
            found = _find_tx_hash(v)
            if found:
                return found
    elif isinstance(result, list):
        for item in result:
            found = _find_tx_hash(item)
            if found:
                return found
    return None
