"""Smoke test for the Witness integration.

Posts a single fake Coach turn to Witness — bypasses ADK/MongoDB/Gemini
entirely so we can verify the wire shape end-to-end without spinning
up the whole agent.

Usage:
    export WITNESS_URL=http://localhost:4022
    python -m scripts.witness_smoke

Expected: prints the new CID + 0G storagescan URL.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys

# Load witness_client.py as a standalone module — bypassing the
# kajota_concierge package __init__ keeps this smoke test runnable
# without installing the full agent dep tree (ADK, Vertex AI, MCP).
_MODULE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__), "..", "kajota_concierge", "witness_client.py"
    )
)
_spec = importlib.util.spec_from_file_location("witness_client", _MODULE_PATH)
assert _spec is not None and _spec.loader is not None
witness_client = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(witness_client)


SAMPLE_USER = "demo-user-witness-smoke"
SAMPLE_MESSAGE = (
    "Hi — do you still have the satin heels? I need them by Friday."
)
SAMPLE_RESPONSE = (
    "Yes! The white satin heels are in stock in sizes 38–42. "
    "₦12,000 with same-day Lagos delivery if you order before 4pm."
)


async def main() -> int:
    if not witness_client.is_enabled():
        print(
            "WITNESS_URL not set (or httpx not installed). "
            "Export WITNESS_URL=http://localhost:4022 and retry.",
            file=sys.stderr,
        )
        return 1

    print(f"[smoke] POSTing to {os.environ['WITNESS_URL']}/memory…")
    result = await witness_client._post_now(
        user_id=SAMPLE_USER,
        message=SAMPLE_MESSAGE,
        response=SAMPLE_RESPONSE,
    )
    if result is None:
        print("[smoke] FAILED — see [witness] log line above", file=sys.stderr)
        return 2

    cid = result.get("cid", "(missing)")
    print("[smoke] OK")
    print(f"  cid:        {cid}")
    print(f"  summary:    {result.get('summary', '')}")
    print(f"  scan:       {result.get('storageScanUrl', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
