"""Slack Bolt (async) transport for the KaJota Concierge agent.

Mounts inside the same FastAPI process as the mobile /chat endpoint —
same ADK Runner, same session service, same MongoDB MCP + Fetch MCP
tool surface. Adds three surfaces:

    /slack/events               — event subscriptions (URL verification,
                                  app_mention, message.im)
    /slack/commands/kajota      — the /kajota slash command
    /slack/oauth/redirect       — (reserved; not wired for the hackathon)

Slash-command routing:

    /kajota watch <product>     → adds to the watchlist via a natural-
                                  language agent turn (the agent picks
                                  the MongoDB MCP insert-one)
    /kajota status              → fires the same proactive prompt as the
                                  mobile client's /proactive endpoint
    /kajota pay <listing> <amt> → calls kajota_concierge.mesh.build_deposit
                                  and posts a Block Kit settlement card
    /kajota help                → static help card

Every Slack user gets a per-workspace session:

    session_id = f"slack:{team_id}:{user_id}"

which lets the same Slack user hold a stateful conversation across
`/kajota status` calls and @-mentions.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shlex
from typing import Any, Callable

from slack_bolt.async_app import AsyncApp

from kajota_concierge import slack_blocks, slack_intents
from kajota_concierge.mesh import (
    MeshCallError,
    MeshConfigError,
    build_deposit,
    resolve_listing_id_display,
    send_approve,
    send_deposit,
)


_LOG = logging.getLogger("kajota_concierge.slack")


# The /proactive prompt is a copy of the one in server.py — we don't
# import it because that would create a circular import (server.py
# imports this module to mount the handler).
_STATUS_PROMPT = (
    "BEFORE producing any text, you MUST call the MongoDB `find` tool "
    "exactly three times, in this order:\n"
    "  1. find on `purchases` with {\"userId\":\"demo-user-1\"}, "
    "     sorted by `orderedAt: -1`, limit 1.\n"
    "  2. find on `wishlist` with {\"userId\":\"demo-user-1\"}, no "
    "     limit.\n"
    "  3. find on `products`, limit 3.\n"
    "\n"
    "After all three tool calls have returned, produce a 1-2 sentence "
    "personalised status summary that references the ACTUAL data you "
    "found — real item names, prices, and quote symbol (`NGNT` in this "
    "demo). End with the standard [CARDS] block built from the queried "
    "documents (one card per data point, max 3 cards). Do NOT fabricate "
    "any values. Do NOT ask what I want."
)


def build_slack_app(
    *,
    run_agent_turn: Callable[..., Any],
) -> AsyncApp | None:
    """Return a configured Bolt AsyncApp, or None if Slack creds missing.

    `run_agent_turn` is a callable with signature
    `async (user_id, session_id, message) -> ChatResponse` — passed in
    from server.py so we reuse its Runner + session service without
    reimporting them here (avoids a circular import).
    """
    bot_token = os.environ.get("SLACK_BOT_TOKEN")
    signing_secret = os.environ.get("SLACK_SIGNING_SECRET")
    if not bot_token or not signing_secret:
        _LOG.info(
            "SLACK_BOT_TOKEN or SLACK_SIGNING_SECRET missing — Slack "
            "transport disabled. Set both env vars to enable."
        )
        return None

    app = AsyncApp(
        token=bot_token,
        signing_secret=signing_secret,
        # We ack immediately and post the real reply asynchronously so
        # slow agent turns don't blow the Slack 3-second budget.
        process_before_response=False,
    )

    def _session_id(team_id: str | None, user_id: str) -> str:
        team = team_id or "T_unknown"
        return f"slack:{team}:{user_id}"

    def _slack_user_id(team_id: str | None, user_id: str) -> str:
        # ADK session lookup by (app_name, user_id, session_id). We fold
        # the workspace into user_id so cross-workspace sharing of a
        # display name doesn't leak state.
        team = team_id or "T_unknown"
        return f"slack:{team}:{user_id}"

    @app.command("/kajota")
    async def kajota_command(ack, command, respond, client):
        # Slack requires an ack within 3s. Send a fast "on it" so the
        # user sees the command was received; the real reply follows
        # via respond() once the agent turn finishes.
        await ack()

        raw_text = (command.get("text") or "").strip()
        team_id = command.get("team_id")
        user_id = command.get("user_id")
        channel_id = command.get("channel_id")

        try:
            parts = shlex.split(raw_text) if raw_text else []
        except ValueError:
            parts = raw_text.split()

        subcommand = (parts[0] if parts else "help").lower()
        args = parts[1:]

        try:
            if subcommand in ("help", ""):
                await respond(
                    blocks=slack_blocks.help_blocks(),
                    text="Kajota Coach in Slack",
                    response_type="ephemeral",
                )
                return

            if subcommand == "watch":
                if not args:
                    await respond(
                        blocks=slack_blocks.error_blocks(
                            "Missing product",
                            "Usage: `/kajota watch <product name>`",
                        ),
                        text="Missing product",
                        response_type="ephemeral",
                    )
                    return
                product = " ".join(args)
                await respond(
                    blocks=slack_blocks.watch_confirmation_blocks(product),
                    text=f"Watching {product}",
                    response_type="in_channel",
                )
                message = (
                    f"Add '{product}' to my watchlist. Use the MongoDB "
                    f"MCP `insert-one` on the `wishlist` collection with "
                    f"{{userId:'demo-user-1', itemName:'{product}'}}. "
                    "Then reply with a 1-sentence confirmation and a "
                    "[CARDS] block containing the new wishlist item."
                )
                reply = await run_agent_turn(
                    user_id=_slack_user_id(team_id, user_id),
                    session_id=_session_id(team_id, user_id),
                    message=message,
                )
                await client.chat_postMessage(
                    channel=channel_id,
                    blocks=slack_blocks.agent_reply_blocks(
                        reply.response, reply.events, header=f"Watching: {product}"
                    ),
                    text=f"Added {product} to watchlist",
                )
                return

            if subcommand == "status":
                await respond(
                    text=":hourglass_flowing_sand: Running the agent…",
                    response_type="ephemeral",
                )
                reply = await run_agent_turn(
                    user_id=_slack_user_id(team_id, user_id),
                    session_id=_session_id(team_id, user_id),
                    message=_STATUS_PROMPT,
                )
                await client.chat_postMessage(
                    channel=channel_id,
                    blocks=slack_blocks.agent_reply_blocks(
                        reply.response, reply.events, header="Kajota status"
                    ),
                    text="Kajota status",
                )
                return

            if subcommand == "pay":
                if len(args) < 2:
                    await respond(
                        blocks=slack_blocks.error_blocks(
                            "Missing arguments",
                            "Usage: `/kajota pay <listing-hint> <usdc-amount>` — "
                            "e.g. `/kajota pay yeezy-hoodie 100`",
                        ),
                        text="Missing arguments",
                        response_type="ephemeral",
                    )
                    return
                listing_hint = args[0]
                try:
                    amount = float(args[1])
                except ValueError:
                    await respond(
                        blocks=slack_blocks.error_blocks(
                            "Bad amount",
                            f"'{args[1]}' isn't a number.",
                        ),
                        text="Bad amount",
                        response_type="ephemeral",
                    )
                    return
                # Look up the on-chain listing id before we ask a
                # teammate to click Approve — a bad hint should fail
                # loudly HERE, not after a well-meaning colleague clicks
                # and the tx reverts.
                try:
                    listing_id_display = await asyncio.to_thread(
                        resolve_listing_id_display, listing_hint
                    )
                except MeshConfigError as exc:
                    await respond(
                        blocks=slack_blocks.error_blocks(
                            "Mesh config missing", str(exc)
                        ),
                        text="Mesh config missing",
                        response_type="ephemeral",
                    )
                    return
                except MeshCallError as exc:
                    await respond(
                        blocks=slack_blocks.error_blocks(
                            "Listing not registered", str(exc)
                        ),
                        text="Listing not registered",
                        response_type="ephemeral",
                    )
                    return

                intent = slack_intents.PendingDeposit(
                    intent_id=slack_intents.new_intent_id(),
                    listing_hint=listing_hint,
                    gross_amount_usdc=amount,
                    requested_by_user_id=user_id,
                    requested_by_display=command.get("user_name") or "someone",
                    team_id=team_id or "T_unknown",
                    channel_id=channel_id,
                    listing_id_display=listing_id_display,
                    created_at=__import__("time").time(),
                )
                slack_intents.put(intent)

                await respond(
                    text=(
                        ":ledger: Proposed on-chain escrow deposit for "
                        f"`{listing_hint}` — {amount:.2f} USDC. Waiting for "
                        "a teammate to approve."
                    ),
                    response_type="ephemeral",
                )
                await client.chat_postMessage(
                    channel=channel_id,
                    blocks=slack_blocks.pending_deposit_blocks(intent),
                    text=(
                        f"Escrow deposit proposed: {amount:.2f} USDC on "
                        f"{listing_hint} — awaiting approval"
                    ),
                )
                return

            # Unknown subcommand → route through the agent as a
            # free-form turn.
            message = raw_text
            reply = await run_agent_turn(
                user_id=_slack_user_id(team_id, user_id),
                session_id=_session_id(team_id, user_id),
                message=message,
            )
            await client.chat_postMessage(
                channel=channel_id,
                blocks=slack_blocks.agent_reply_blocks(
                    reply.response, reply.events, header="Kajota"
                ),
                text=raw_text,
            )
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("/kajota command failed")
            await client.chat_postMessage(
                channel=channel_id,
                blocks=slack_blocks.error_blocks(
                    "Command failed",
                    f"{type(exc).__name__}: {exc}",
                ),
                text="Command failed",
            )

    @app.action("kajota_approve")
    async def kajota_approve(ack, body, client):
        await ack()
        try:
            actions = body.get("actions") or []
            intent_id = actions[0].get("value") if actions else None
            approver_user_id = (body.get("user") or {}).get("id", "unknown")
            container = body.get("container") or {}
            channel_id = (
                container.get("channel_id")
                or (body.get("channel") or {}).get("id")
            )
            original_ts = container.get("message_ts") or (
                (body.get("message") or {}).get("ts")
            )

            intent = slack_intents.take(intent_id) if intent_id else None
            if intent is None:
                if channel_id and original_ts:
                    await client.chat_update(
                        channel=channel_id,
                        ts=original_ts,
                        blocks=slack_blocks.error_blocks(
                            "Intent expired",
                            "That escrow proposal expired or was already "
                            "acted on. Re-run `/kajota pay` to try again.",
                        ),
                        text="Intent expired",
                    )
                return

            # Update the original card — approvers can see the flow
            # started, buttons disappear so no double-click.
            if channel_id and original_ts:
                await client.chat_update(
                    channel=channel_id,
                    ts=original_ts,
                    blocks=slack_blocks.approving_card_blocks(
                        intent, approver_user_id
                    ),
                    text=(
                        f"Escrow deposit approved for {intent.listing_hint} "
                        f"— settling on-chain"
                    ),
                )

            # Post an anchor message; every progress update lives in
            # this thread so the channel stays scrollable.
            anchor = await client.chat_postMessage(
                channel=intent.channel_id,
                thread_ts=original_ts,
                text=(
                    f":hourglass_flowing_sand: Approve tx starting for "
                    f"{intent.gross_amount_usdc:.2f} USDC on "
                    f"{intent.listing_hint}"
                ),
                blocks=slack_blocks.progress_blocks(
                    "USDC.approve", "broadcasting"
                ),
            )
            thread_ts = original_ts or anchor.get("ts")

            # ── Approve tx ──
            try:
                approve_tx = await asyncio.to_thread(
                    send_approve,
                    listing_hint=intent.listing_hint,
                    gross_amount_usdc=intent.gross_amount_usdc,
                )
            except (MeshConfigError, MeshCallError) as exc:
                await client.chat_postMessage(
                    channel=intent.channel_id,
                    thread_ts=thread_ts,
                    blocks=slack_blocks.error_blocks(
                        "Approve tx failed", str(exc)
                    ),
                    text="Approve tx failed",
                )
                return
            await client.chat_postMessage(
                channel=intent.channel_id,
                thread_ts=thread_ts,
                blocks=slack_blocks.progress_blocks(
                    "USDC.approve", "confirmed", approve_tx
                ),
                text=f"USDC.approve confirmed {approve_tx.hash[:10]}…",
            )

            # ── Deposit tx ──
            await client.chat_postMessage(
                channel=intent.channel_id,
                thread_ts=thread_ts,
                blocks=slack_blocks.progress_blocks(
                    "CosellEscrow.deposit", "broadcasting"
                ),
                text="Deposit tx broadcasting…",
            )
            try:
                deposit_tx = await asyncio.to_thread(
                    send_deposit,
                    listing_hint=intent.listing_hint,
                    gross_amount_usdc=intent.gross_amount_usdc,
                )
            except (MeshConfigError, MeshCallError) as exc:
                await client.chat_postMessage(
                    channel=intent.channel_id,
                    thread_ts=thread_ts,
                    blocks=slack_blocks.error_blocks(
                        "Deposit tx failed", str(exc)
                    ),
                    text="Deposit tx failed",
                )
                return
            await client.chat_postMessage(
                channel=intent.channel_id,
                thread_ts=thread_ts,
                blocks=slack_blocks.progress_blocks(
                    "CosellEscrow.deposit", "confirmed", deposit_tx
                ),
                text=f"CosellEscrow.deposit confirmed {deposit_tx.hash[:10]}…",
            )

            # Final settled summary in the same thread.
            await client.chat_postMessage(
                channel=intent.channel_id,
                thread_ts=thread_ts,
                blocks=slack_blocks.settled_summary_blocks(
                    intent, approve_tx, deposit_tx
                ),
                text=(
                    f"Escrow settled — {intent.gross_amount_usdc:.2f} USDC "
                    f"locked for {intent.listing_hint}"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("kajota_approve failed")
            try:
                await client.chat_postMessage(
                    channel=body.get("channel", {}).get("id")
                    or (body.get("container") or {}).get("channel_id"),
                    blocks=slack_blocks.error_blocks(
                        "Approval flow crashed",
                        f"{type(exc).__name__}: {exc}",
                    ),
                    text="Approval flow crashed",
                )
            except Exception:  # noqa: BLE001
                pass

    @app.action("kajota_deny")
    async def kajota_deny(ack, body, client):
        await ack()
        try:
            actions = body.get("actions") or []
            intent_id = actions[0].get("value") if actions else None
            denier_user_id = (body.get("user") or {}).get("id", "unknown")
            container = body.get("container") or {}
            channel_id = container.get("channel_id") or (
                (body.get("channel") or {}).get("id")
            )
            original_ts = container.get("message_ts") or (
                (body.get("message") or {}).get("ts")
            )

            intent = slack_intents.take(intent_id) if intent_id else None
            if intent is None:
                return
            if channel_id and original_ts:
                await client.chat_update(
                    channel=channel_id,
                    ts=original_ts,
                    blocks=slack_blocks.denied_card_blocks(
                        intent, denier_user_id
                    ),
                    text=(
                        f"Escrow deposit denied for {intent.listing_hint}"
                    ),
                )
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("kajota_deny failed")

    @app.event("app_mention")
    async def handle_mention(event, say, client):
        text = event.get("text", "") or ""
        # Strip the bot mention token (e.g. "<@U012ABCDE> ")
        stripped = _strip_mention(text).strip()
        team_id = event.get("team")
        user_id = event.get("user")
        channel_id = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")

        if not stripped:
            await say(
                blocks=slack_blocks.help_blocks(),
                text="Kajota Coach in Slack",
                thread_ts=thread_ts,
            )
            return

        try:
            reply = await run_agent_turn(
                user_id=_slack_user_id(team_id, user_id),
                session_id=_session_id(team_id, user_id),
                message=stripped,
            )
            await client.chat_postMessage(
                channel=channel_id,
                blocks=slack_blocks.agent_reply_blocks(
                    reply.response, reply.events, header=None
                ),
                text=reply.response[:200] or "Kajota reply",
                thread_ts=thread_ts,
            )
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("app_mention failed")
            await client.chat_postMessage(
                channel=channel_id,
                blocks=slack_blocks.error_blocks(
                    "Agent turn failed",
                    f"{type(exc).__name__}: {exc}",
                ),
                text="Agent turn failed",
                thread_ts=thread_ts,
            )

    @app.event("message")
    async def handle_direct_message(event, client):
        # Only respond to 1:1 DMs, not channel messages (which would
        # duplicate the app_mention handler).
        if event.get("channel_type") != "im":
            return
        if event.get("bot_id") or event.get("subtype"):
            return
        text = (event.get("text") or "").strip()
        if not text:
            return
        team_id = event.get("team")
        user_id = event.get("user")
        channel_id = event.get("channel")
        try:
            reply = await run_agent_turn(
                user_id=_slack_user_id(team_id, user_id),
                session_id=_session_id(team_id, user_id),
                message=text,
            )
            await client.chat_postMessage(
                channel=channel_id,
                blocks=slack_blocks.agent_reply_blocks(
                    reply.response, reply.events, header=None
                ),
                text=reply.response[:200] or "Kajota reply",
            )
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("DM turn failed")
            await client.chat_postMessage(
                channel=channel_id,
                blocks=slack_blocks.error_blocks(
                    "Agent turn failed",
                    f"{type(exc).__name__}: {exc}",
                ),
                text="Agent turn failed",
            )

    return app


_MENTION_RE = None


def _strip_mention(text: str) -> str:
    """Drop the leading `<@Uxxx>` bot-mention token."""
    global _MENTION_RE
    if _MENTION_RE is None:
        import re

        _MENTION_RE = re.compile(r"<@[A-Z0-9]+>\s*")
    return _MENTION_RE.sub("", text, count=1)
