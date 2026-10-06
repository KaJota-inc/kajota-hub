from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools._kh import KeeperHubToolError, call, parse_json_field


class RunWorkflowTool(Tool):
    """Trigger a stored KeeperHub workflow from a Dify workflow.

    The safer of the two execution paths, and worth preferring: a stored
    workflow was authored and reviewed in KeeperHub, so the agent chooses
    *which* reviewed thing to run rather than composing a contract call at
    runtime. That is the difference between an agent picking from a menu and
    an agent writing the recipe while the kitchen is on fire.
    """

    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        workflow_id = (tool_parameters.get("workflow_id") or "").strip()
        if not workflow_id:
            yield self.create_text_message("`workflow_id` is required.")
            return

        try:
            payload = parse_json_field(tool_parameters.get("input"), "input") or {}
            if not isinstance(payload, dict):
                raise KeeperHubToolError("`input` must be a JSON object.")

            args: dict[str, Any] = {"workflowId": workflow_id, "input": payload}
            idem = (tool_parameters.get("idempotency_key") or "").strip()
            if idem:
                # Without this, a retried Dify node fires the workflow twice.
                args["idempotency_key"] = idem

            result = call(self.runtime.credentials, "execute_workflow", args)
        except KeeperHubToolError as exc:
            yield self.create_text_message(str(exc))
            return

        yield self.create_json_message({"triggered": True, "result": result})
        yield self.create_text_message(
            "Workflow trigger accepted by KeeperHub. Note this confirms the "
            "trigger, not completion — the run continues server-side with "
            "retries and gas handling, and its outcome lives in the audit trail."
        )
