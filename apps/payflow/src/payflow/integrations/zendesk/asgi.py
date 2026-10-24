"""ASGI entrypoint for the Zendesk webhook receiver.

Usage:
    uvicorn payflow.integrations.zendesk.asgi:app --host 0.0.0.0 --port 8080

Configuration comes from env vars — see ZendeskConfig.from_env().

If ZENDESK_* envs are not yet wired (hub-first boot, pre-pilot), build_app()
raises during config.from_env() and the process would die on import — which
supervisord then loops on and Caddy fronts as a persistent 502. We catch that
once at module scope and serve a tiny stub app whose /healthz and / return 200
("configured: false, reason: ..."), while /webhook/zendesk returns 503 with
the same reason. Set the ZENDESK_* secrets in Render to activate the real app.
"""
try:
    from payflow.integrations.zendesk.webhook import build_app

    app = build_app(configure_logging=True)
except Exception as _init_err:  # noqa: BLE001 — any env/config error must not kill boot
    import logging

    from fastapi import FastAPI, HTTPException

    _reason = f"{type(_init_err).__name__}: {_init_err}"
    logging.getLogger("payflow.zendesk").warning(
        "payflow-zendesk: build_app failed (%s) — serving stub app", _reason
    )
    app = FastAPI(title="Payflow — Zendesk (stub)", version="0.1-stub")

    @app.get("/")
    def _stub_root() -> dict:
        return {
            "status": "stub",
            "configured": False,
            "reason": _reason,
            "note": "set ZENDESK_* envs in Render to activate the real webhook",
        }

    @app.get("/healthz")
    def _stub_healthz() -> dict:
        return {"status": "stub", "configured": False, "reason": _reason}

    @app.post("/webhook/zendesk")
    def _stub_webhook() -> None:
        raise HTTPException(
            status_code=503, detail=f"payflow-zendesk unconfigured: {_reason}"
        )
