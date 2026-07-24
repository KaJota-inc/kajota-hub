"""ASGI entrypoint for uvicorn / gunicorn / any ASGI runner.

Usage:
    uvicorn payflow.integrations.freshdesk.asgi:app --host 0.0.0.0 --port 8080

Configuration comes from env vars — see FreshdeskConfig.from_env().
"""
from payflow.integrations.freshdesk.webhook import build_app

app = build_app(configure_logging=True)
