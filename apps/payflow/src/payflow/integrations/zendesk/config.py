import os
from typing import Optional

from pydantic import BaseModel, Field

from payflow.models import Dialect


class ZendeskConfig(BaseModel):
    subdomain: str = Field(..., description="e.g. 'yourbank' (full host is yourbank.zendesk.com).")
    email: str = Field(..., description="Zendesk API user email.")
    api_token: str = Field(..., description="Zendesk API token.")
    webhook_secret: str = Field(..., description="Shared HMAC secret for webhook signature verification.")
    default_dialect: Dialect = Dialect.CORE
    use_llm: bool = False
    verify: bool = False
    dry_run: bool = False
    internal_token: Optional[str] = Field(
        None,
        description="Bearer for /internal/* endpoints (metrics). None = endpoints open (dev only).",
    )
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> "ZendeskConfig":
        return cls(
            subdomain=_required("ZENDESK_SUBDOMAIN"),
            email=_required("ZENDESK_EMAIL"),
            api_token=_required("ZENDESK_API_TOKEN"),
            webhook_secret=_required("ZENDESK_WEBHOOK_SECRET"),
            default_dialect=Dialect(os.environ.get("ZENDESK_DEFAULT_DIALECT", "core")),
            use_llm=_bool_env("PAYFLOW_USE_LLM"),
            verify=_bool_env("PAYFLOW_VERIFY"),
            dry_run=_bool_env("PAYFLOW_DRY_RUN"),
            internal_token=os.environ.get("PAYFLOW_INTERNAL_TOKEN") or None,
            log_level=os.environ.get("PAYFLOW_LOG_LEVEL", "INFO").upper(),
        )


def _required(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"{key} env var required")
    return val


def _bool_env(key: str, default: bool = False) -> bool:
    val = os.environ.get(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")
