"""ASGI entrypoint for the Zendesk webhook receiver.

Usage:
    uvicorn payflow.integrations.zendesk.asgi:app --host 0.0.0.0 --port 8080

Configuration comes from env vars — see ZendeskConfig.from_env().
"""
from payflow.integrations.zendesk.webhook import build_app

app = build_app(configure_logging=True)
