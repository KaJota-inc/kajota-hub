"""Block Kit formatters for Slack replies.

The agent returns a plain-text reply optionally followed by a
`[CARDS]…[/CARDS]` JSON block (same convention as the mobile client).
This module converts that hybrid payload into Slack Block Kit so the
Slack UI renders product cards, tool traces, and settlement receipts
inline instead of dumping a wall of text.
"""

from __future__ import annotations

import json
import re
from typing import Any


CARDS_RE = re.compile(r"\[CARDS\](.*?)\[/CARDS\]", re.DOTALL)


def _split_cards(text: str) -> tuple[str, list[dict[str, Any]]]:
    """Return (prose, cards). Missing block → prose = text, cards = []."""
    match = CARDS_RE.search(text or "")
    if not match:
        return (text or "").strip(), []
    prose = (text[: match.start()] + text[match.end() :]).strip()
    raw = match.group(1).strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        return prose, []
    if isinstance(parsed, dict) and isinstance(parsed.get("cards"), list):
        cards = parsed["cards"]
    elif isinstance(parsed, list):
        cards = parsed
    else:
        cards = []
    return prose, cards


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _card_block(card: dict[str, Any]) -> list[dict[str, Any]]:
    """One product card → header + facts section."""
    title = str(
        card.get("itemName") or card.get("name") or card.get("title") or "Item"
    )
    price = card.get("pricePaidQuote") or card.get("priceQuote") or card.get(
        "currentPriceQuote"
    )
    symbol = card.get("quoteSymbol") or ""
    category = card.get("category") or ""
    status = card.get("status") or ""

    facts = []
    if price is not None:
        facts.append(f"*Price:* {price} {symbol}".strip())
    if category:
        facts.append(f"*Category:* {category}")
    if status:
        facts.append(f"*Status:* {status}")

    fields_pairs = [
        {"type": "mrkdwn", "text": _truncate(f, 2000)} for f in facts
    ]

    blocks: list[dict[str, Any]] = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{_truncate(title, 150)}*",
            },
        }
    ]
    if fields_pairs:
        # Block Kit fields must be 2–10 entries; single-entry falls back
        # to a plain section
        if len(fields_pairs) == 1:
            blocks.append({"type": "section", "text": fields_pairs[0]})
        else:
            blocks.append({"type": "section", "fields": fields_pairs[:10]})
    return blocks


def agent_reply_blocks(
    response_text: str,
    events: list[dict[str, Any]] | None = None,
    header: str | None = None,
) -> list[dict[str, Any]]:
    """Turn an agent turn into a Slack Block Kit block list."""
    prose, cards = _split_cards(response_text)
    blocks: list[dict[str, Any]] = []

    if header:
        blocks.append(
            {
                "type": "header",
                "text": {"type": "plain_text", "text": _truncate(header, 150)},
            }
        )

    if prose:
        # Slack section text max 3000 chars; chunk if needed
        chunks = [prose[i : i + 2800] for i in range(0, len(prose), 2800)] or [""]
        for chunk in chunks:
            blocks.append(
                {"type": "section", "text": {"type": "mrkdwn", "text": chunk}}
            )

    if cards:
        blocks.append({"type": "divider"})
        for card in cards[:6]:
            blocks.extend(_card_block(card))

    tool_calls = _tool_call_summary(events or [])
    if tool_calls:
        blocks.append({"type": "divider"})
        blocks.append(
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"_Used_ *{len(tool_calls)}* _MCP tool call(s):_ {', '.join(tool_calls[:6])}",
                    }
                ],
            }
        )

    if not blocks:
        blocks.append(
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": "_(empty agent reply)_"},
            }
        )
    return blocks


def _tool_call_summary(events: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for e in events:
        for p in e.get("parts", []) or []:
            call = p.get("tool_call") if isinstance(p, dict) else None
            if call and call.get("name"):
                names.append(str(call["name"]))
    return names


def watch_confirmation_blocks(product: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":eyes: *Watching* `{_truncate(product, 100)}`\n"
                    "I'll ping this channel when the price moves or stock updates."
                ),
            },
        }
    ]


def deposit_result_blocks(result: Any) -> list[dict[str, Any]]:
    """result: kajota_concierge.mesh.DepositResult"""
    signed = getattr(result, "signed", False)
    chain = getattr(result, "chain", "unknown")
    gross = getattr(result, "gross_amount_display", "")
    listing = getattr(result, "listing_id", "")
    approve = result.approve
    deposit = result.deposit

    if signed:
        headline = f":lock_with_ink_pen: *Escrow settled* — {gross} on {chain}"
        approve_line = (
            f"1. USDC.approve → <{approve.explorer_url}|`{approve.hash[:10]}…`> ✅"
        )
        deposit_line = (
            f"2. CosellEscrow.deposit → <{deposit.explorer_url}|`{deposit.hash[:10]}…`> ✅"
        )
    else:
        headline = f":ticket: *Unsigned escrow deposit prepared* — {gross} on {chain}"
        approve_line = f"1. USDC.approve → `{approve.raw.get('to')}`  _(unsigned; sign to broadcast)_"
        deposit_line = f"2. CosellEscrow.deposit → `{deposit.raw.get('to')}`  _(unsigned; sign to broadcast)_"

    return [
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": headline},
        },
        {
            "type": "context",
            "elements": [
                {"type": "mrkdwn", "text": f"Listing: `{listing}`"},
            ],
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": approve_line},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": deposit_line},
        },
    ]


def pending_deposit_blocks(intent: Any) -> list[dict[str, Any]]:
    """Card posted by /kajota pay before broadcasting.

    Shows the pending deposit and two buttons — Approve fires the
    on-chain send; Deny drops the intent. `intent` is a
    slack_intents.PendingDeposit.
    """
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Escrow deposit — awaiting approval",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"<@{intent.requested_by_user_id}> proposes to lock "
                    f"*{intent.gross_amount_usdc:.2f} USDC* in the "
                    f"CosellEscrow for `{intent.listing_hint}`.\n"
                    "A workspace teammate should approve before we broadcast."
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"Listing: `{intent.listing_id_display}`  ·  "
                        f"Chain: Mantle Sepolia (5003)"
                    ),
                },
            ],
        },
        {
            "type": "actions",
            "block_id": f"kajota_deposit_actions:{intent.intent_id}",
            "elements": [
                {
                    "type": "button",
                    "action_id": "kajota_approve",
                    "value": intent.intent_id,
                    "style": "primary",
                    "text": {
                        "type": "plain_text",
                        "text": "Approve + broadcast",
                    },
                },
                {
                    "type": "button",
                    "action_id": "kajota_deny",
                    "value": intent.intent_id,
                    "style": "danger",
                    "text": {"type": "plain_text", "text": "Deny"},
                },
            ],
        },
    ]


def approving_card_blocks(intent: Any, approver_user_id: str) -> list[dict[str, Any]]:
    """Replaces the pending card once someone clicks Approve — no buttons."""
    return [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Escrow deposit — approved, settling on-chain",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":white_check_mark: Approved by <@{approver_user_id}>. "
                    f"Locking *{intent.gross_amount_usdc:.2f} USDC* on "
                    f"`{intent.listing_hint}` — see the thread for on-chain "
                    "receipts as each tx confirms."
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"Requested by <@{intent.requested_by_user_id}>  ·  "
                        f"Listing: `{intent.listing_id_display}`"
                    ),
                },
            ],
        },
    ]


def denied_card_blocks(intent: Any, denier_user_id: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Escrow deposit — denied"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":no_entry_sign: <@{denier_user_id}> denied the "
                    f"{intent.gross_amount_usdc:.2f} USDC deposit on "
                    f"`{intent.listing_hint}`. No on-chain txs were broadcast."
                ),
            },
        },
    ]


def progress_blocks(step: str, status: str, tx: Any | None = None) -> list[dict[str, Any]]:
    """Threaded progress update. `tx` is a TxReceipt-like object once we have one."""
    if status == "broadcasting":
        icon = ":arrows_counterclockwise:"
        text = f"{icon} *{step}* — broadcasting…"
    elif status == "confirmed":
        icon = ":white_check_mark:"
        url = getattr(tx, "explorer_url", "") or ""
        h = getattr(tx, "hash", "") or ""
        short = f"`{h[:10]}…`" if h else ""
        if url and h:
            text = f"{icon} *{step}* confirmed — <{url}|{short}>"
        else:
            text = f"{icon} *{step}* confirmed"
    else:
        text = f"*{step}* — {status}"
    return [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]


def settled_summary_blocks(intent: Any, approve_tx: Any, deposit_tx: Any) -> list[dict[str, Any]]:
    """Final in-thread receipt summarising the two on-chain txs."""
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f":lock_with_ink_pen: *Escrow settled* — "
                    f"{intent.gross_amount_usdc:.2f} USDC locked for "
                    f"`{intent.listing_hint}`."
                ),
            },
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": (
                        f"USDC.approve <{approve_tx.explorer_url}|"
                        f"`{approve_tx.hash[:10]}…`>  ·  "
                        f"CosellEscrow.deposit <{deposit_tx.explorer_url}|"
                        f"`{deposit_tx.hash[:10]}…`>"
                    ),
                },
            ],
        },
    ]


def error_blocks(title: str, detail: str) -> list[dict[str, Any]]:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f":warning: *{_truncate(title, 120)}*\n{_truncate(detail, 1500)}",
            },
        }
    ]


def help_blocks() -> list[dict[str, Any]]:
    return [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": "Kajota Coach in Slack"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    "The co-seller's control room. Slash commands:\n"
                    "• `/kajota watch <product>` — add to the watchlist\n"
                    "• `/kajota status` — proactive agent turn (recent orders, wishlist deltas, drops)\n"
                    "• `/kajota pay <listing> <amount>` — prepare an on-chain USDC escrow deposit\n"
                    "• `/kajota help` — this card\n"
                    "You can also `@kajota` me anywhere I'm in-channel."
                ),
            },
        },
    ]
