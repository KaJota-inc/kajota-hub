from typing import Any

from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools._kh import KeeperHubToolError, call


class KeeperHubProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        """Prove the key works by making a real read-only MCP call.

        `list_integrations` is used deliberately: it needs a working session
        and org scope, but touches no chain and costs nothing — so validating
        a key can never move value.
        """
        try:
            call(credentials, "list_integrations", {})
        except KeeperHubToolError as exc:
            raise ToolProviderCredentialValidationError(str(exc)) from exc
        except Exception as exc:  # noqa: BLE001
            raise ToolProviderCredentialValidationError(
                f"Could not reach KeeperHub: {exc}"
            ) from exc
