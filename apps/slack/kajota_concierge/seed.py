"""MongoDB seed script for the KaJota Concierge demo.

Populates the four collections the agent reasons over with realistic
shopping data:

    - users      — one demo user with profile + wallet address
    - products   — 20 items across sneakers / hoodies / accessories
    - purchases  — 8 past orders for the demo user (mix of statuses)
    - wishlist   — 3 items the demo user has flagged

Idempotent: drops the `kajota` database before reseeding so reruns
produce the exact same fixture for demo continuity.

Run via:
    python -m kajota_concierge.seed
or:
    kajota-agent-seed  (after `pip install -e .`)
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(".env.rapid-agent")
load_dotenv(".env")

DB_NAME = "kajota"
DEMO_USER_ID = "demo-user-1"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _seed_products() -> list[dict[str, Any]]:
    """20 products across the categories the demo user has bought."""
    now = _now()
    return [
        # Sneakers (5)
        {
            "_id": "sneakers-yeezy-350-v2",
            "name": "Yeezy Boost 350 v2",
            "category": "sneakers",
            "priceQuote": "40000",
            "quoteSymbol": "NGNT",
            "stock": 12,
            "addedAt": now - timedelta(days=120),
        },
        {
            "_id": "sneakers-air-jordan-1",
            "name": "Air Jordan 1 Retro High",
            "category": "sneakers",
            "priceQuote": "32000",
            "quoteSymbol": "NGNT",
            "stock": 7,
            "addedAt": now - timedelta(days=200),
        },
        {
            "_id": "sneakers-nike-dunk-low",
            "name": "Nike Dunk Low Panda",
            "category": "sneakers",
            "priceQuote": "28000",
            "quoteSymbol": "NGNT",
            "stock": 0,
            "addedAt": now - timedelta(days=90),
        },
        {
            "_id": "sneakers-adidas-samba",
            "name": "Adidas Samba OG",
            "category": "sneakers",
            "priceQuote": "22000",
            "quoteSymbol": "NGNT",
            "stock": 25,
            "addedAt": now - timedelta(days=60),
        },
        {
            "_id": "sneakers-new-balance-550",
            "name": "New Balance 550 White Green",
            "category": "sneakers",
            "priceQuote": "26000",
            "quoteSymbol": "NGNT",
            "stock": 18,
            "addedAt": now - timedelta(days=45),
        },
        # Hoodies (4)
        {
            "_id": "hoodie-yeezy-gap",
            "name": "Yeezy Gap Round Jacket",
            "category": "hoodies",
            "priceQuote": "18000",
            "quoteSymbol": "NGNT",
            "stock": 8,
            "addedAt": now - timedelta(days=180),
        },
        {
            "_id": "hoodie-supreme-box",
            "name": "Supreme Box Logo Hoodie",
            "category": "hoodies",
            "priceQuote": "45000",
            "quoteSymbol": "NGNT",
            "stock": 3,
            "addedAt": now - timedelta(days=80),
        },
        {
            "_id": "hoodie-essentials-fog",
            "name": "Essentials Fear of God Hoodie",
            "category": "hoodies",
            "priceQuote": "12000",
            "quoteSymbol": "NGNT",
            "stock": 30,
            "addedAt": now - timedelta(days=30),
        },
        {
            "_id": "hoodie-stussy-basic",
            "name": "Stussy Basic Pigment Dyed Hoodie",
            "category": "hoodies",
            "priceQuote": "9500",
            "quoteSymbol": "NGNT",
            "stock": 15,
            "addedAt": now - timedelta(days=20),
        },
        # Accessories (6)
        {
            "_id": "watch-casio-gshock",
            "name": "Casio G-Shock GA-2100",
            "category": "watches",
            "priceQuote": "11000",
            "quoteSymbol": "NGNT",
            "stock": 22,
            "addedAt": now - timedelta(days=150),
        },
        {
            "_id": "watch-timex-q",
            "name": "Timex Q Reissue",
            "category": "watches",
            "priceQuote": "8500",
            "quoteSymbol": "NGNT",
            "stock": 11,
            "addedAt": now - timedelta(days=100),
        },
        {
            "_id": "bag-jansport-superbreak",
            "name": "JanSport SuperBreak Backpack",
            "category": "bags",
            "priceQuote": "3500",
            "quoteSymbol": "NGNT",
            "stock": 40,
            "addedAt": now - timedelta(days=70),
        },
        {
            "_id": "bag-northface-borealis",
            "name": "The North Face Borealis Backpack",
            "category": "bags",
            "priceQuote": "7800",
            "quoteSymbol": "NGNT",
            "stock": 19,
            "addedAt": now - timedelta(days=40),
        },
        {
            "_id": "cap-newera-yankees",
            "name": "New Era 9FIFTY Yankees Cap",
            "category": "caps",
            "priceQuote": "4200",
            "quoteSymbol": "NGNT",
            "stock": 32,
            "addedAt": now - timedelta(days=25),
        },
        {
            "_id": "cap-stussy-stock-low-pro",
            "name": "Stussy Stock Low Pro Cap",
            "category": "caps",
            "priceQuote": "5600",
            "quoteSymbol": "NGNT",
            "stock": 14,
            "addedAt": now - timedelta(days=15),
        },
        # Tech (5)
        {
            "_id": "tech-airpods-pro-2",
            "name": "AirPods Pro 2nd Gen",
            "category": "tech",
            "priceQuote": "24000",
            "quoteSymbol": "NGNT",
            "stock": 9,
            "addedAt": now - timedelta(days=110),
        },
        {
            "_id": "tech-anker-powercore",
            "name": "Anker PowerCore 26800 mAh",
            "category": "tech",
            "priceQuote": "6200",
            "quoteSymbol": "NGNT",
            "stock": 28,
            "addedAt": now - timedelta(days=85),
        },
        {
            "_id": "tech-rode-wireless-go",
            "name": "Rode Wireless GO II",
            "category": "tech",
            "priceQuote": "29000",
            "quoteSymbol": "NGNT",
            "stock": 5,
            "addedAt": now - timedelta(days=55),
        },
        {
            "_id": "tech-logitech-mx-master",
            "name": "Logitech MX Master 3S",
            "category": "tech",
            "priceQuote": "10500",
            "quoteSymbol": "NGNT",
            "stock": 17,
            "addedAt": now - timedelta(days=35),
        },
        {
            "_id": "tech-keychron-k2",
            "name": "Keychron K2 V2 Mechanical Keyboard",
            "category": "tech",
            "priceQuote": "8900",
            "quoteSymbol": "NGNT",
            "stock": 21,
            "addedAt": now - timedelta(days=10),
        },
    ]


def _seed_users() -> list[dict[str, Any]]:
    return [
        {
            "_id": DEMO_USER_ID,
            "displayName": "Bori",
            "walletAddress": "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266",
            "joinedAt": _now() - timedelta(days=250),
            "preferredQuoteCurrency": "NGNT",
        },
    ]


def _seed_purchases() -> list[dict[str, Any]]:
    """8 orders for the demo user. Mix of statuses + categories so the
    agent has signal for the 'what should I buy next?' aggregate."""
    now = _now()
    return [
        # Past, delivered — sneakers
        {
            "_id": "ord-001",
            "orderId": "ord-001",
            "userId": DEMO_USER_ID,
            "itemId": "sneakers-yeezy-350-v2",
            "itemName": "Yeezy Boost 350 v2",
            "category": "sneakers",
            "pricePaidQuote": "39000",
            "quoteSymbol": "NGNT",
            "status": "delivered",
            "orderedAt": now - timedelta(days=210),
            "shippedAt": now - timedelta(days=208),
            "deliveredAt": now - timedelta(days=205),
            "expectedDelivery": now - timedelta(days=205),
        },
        {
            "_id": "ord-002",
            "orderId": "ord-002",
            "userId": DEMO_USER_ID,
            "itemId": "sneakers-air-jordan-1",
            "itemName": "Air Jordan 1 Retro High",
            "category": "sneakers",
            "pricePaidQuote": "32000",
            "quoteSymbol": "NGNT",
            "status": "delivered",
            "orderedAt": now - timedelta(days=150),
            "shippedAt": now - timedelta(days=148),
            "deliveredAt": now - timedelta(days=145),
            "expectedDelivery": now - timedelta(days=145),
        },
        {
            "_id": "ord-003",
            "orderId": "ord-003",
            "userId": DEMO_USER_ID,
            "itemId": "sneakers-adidas-samba",
            "itemName": "Adidas Samba OG",
            "category": "sneakers",
            "pricePaidQuote": "22000",
            "quoteSymbol": "NGNT",
            "status": "delivered",
            "orderedAt": now - timedelta(days=58),
            "shippedAt": now - timedelta(days=56),
            "deliveredAt": now - timedelta(days=53),
            "expectedDelivery": now - timedelta(days=53),
        },
        # Hoodies
        {
            "_id": "ord-004",
            "orderId": "ord-004",
            "userId": DEMO_USER_ID,
            "itemId": "hoodie-essentials-fog",
            "itemName": "Essentials Fear of God Hoodie",
            "category": "hoodies",
            "pricePaidQuote": "11500",
            "quoteSymbol": "NGNT",
            "status": "delivered",
            "orderedAt": now - timedelta(days=29),
            "shippedAt": now - timedelta(days=27),
            "deliveredAt": now - timedelta(days=24),
            "expectedDelivery": now - timedelta(days=24),
        },
        # Tech
        {
            "_id": "ord-005",
            "orderId": "ord-005",
            "userId": DEMO_USER_ID,
            "itemId": "tech-airpods-pro-2",
            "itemName": "AirPods Pro 2nd Gen",
            "category": "tech",
            "pricePaidQuote": "24000",
            "quoteSymbol": "NGNT",
            "status": "delivered",
            "orderedAt": now - timedelta(days=100),
            "shippedAt": now - timedelta(days=98),
            "deliveredAt": now - timedelta(days=95),
            "expectedDelivery": now - timedelta(days=95),
        },
        # IN-FLIGHT order — the agent will pick this up when asked "where's my order"
        {
            "_id": "ord-006",
            "orderId": "ord-006",
            "userId": DEMO_USER_ID,
            "itemId": "tech-keychron-k2",
            "itemName": "Keychron K2 V2 Mechanical Keyboard",
            "category": "tech",
            "pricePaidQuote": "8900",
            "quoteSymbol": "NGNT",
            "status": "shipped",
            "orderedAt": now - timedelta(days=3),
            "shippedAt": now - timedelta(days=1),
            "deliveredAt": None,
            "expectedDelivery": now + timedelta(days=2),
            "trackingNumber": "1Z999AA10123456784",
        },
        # PROCESSING — not yet shipped
        {
            "_id": "ord-007",
            "orderId": "ord-007",
            "userId": DEMO_USER_ID,
            "itemId": "cap-newera-yankees",
            "itemName": "New Era 9FIFTY Yankees Cap",
            "category": "caps",
            "pricePaidQuote": "4200",
            "quoteSymbol": "NGNT",
            "status": "processing",
            "orderedAt": now - timedelta(hours=18),
            "shippedAt": None,
            "deliveredAt": None,
            "expectedDelivery": now + timedelta(days=4),
        },
        # Watches
        {
            "_id": "ord-008",
            "orderId": "ord-008",
            "userId": DEMO_USER_ID,
            "itemId": "watch-casio-gshock",
            "itemName": "Casio G-Shock GA-2100",
            "category": "watches",
            "pricePaidQuote": "11000",
            "quoteSymbol": "NGNT",
            "status": "delivered",
            "orderedAt": now - timedelta(days=130),
            "shippedAt": now - timedelta(days=128),
            "deliveredAt": now - timedelta(days=125),
            "expectedDelivery": now - timedelta(days=125),
        },
    ]


def _seed_wishlist() -> list[dict[str, Any]]:
    now = _now()
    return [
        {
            "userId": DEMO_USER_ID,
            "itemId": "hoodie-supreme-box",
            "itemName": "Supreme Box Logo Hoodie",
            "currentPriceQuote": "45000",
            "targetPriceQuote": "30000",
            "quoteSymbol": "NGNT",
            "addedAt": now - timedelta(days=12),
        },
        {
            "userId": DEMO_USER_ID,
            "itemId": "tech-rode-wireless-go",
            "itemName": "Rode Wireless GO II",
            "currentPriceQuote": "29000",
            "targetPriceQuote": "22000",
            "quoteSymbol": "NGNT",
            "addedAt": now - timedelta(days=8),
        },
        {
            "userId": DEMO_USER_ID,
            "itemId": "sneakers-nike-dunk-low",
            "itemName": "Nike Dunk Low Panda",
            "currentPriceQuote": "28000",
            "targetPriceQuote": "20000",
            "quoteSymbol": "NGNT",
            "addedAt": now - timedelta(days=5),
            "notes": "wait for restock — currently out of stock",
        },
    ]


def main() -> int:
    uri = os.environ.get("MONGODB_URI", "")
    if not uri:
        print(
            "MONGODB_URI is not set. Configure it in .env.rapid-agent.",
            file=sys.stderr,
        )
        return 1

    client = MongoClient(uri)
    # Drop + reseed for idempotency. The demo is meant to produce the
    # same fixture every time so the recorded video is reproducible.
    client.drop_database(DB_NAME)
    db = client[DB_NAME]

    print(f"Seeding database '{DB_NAME}' at {uri.split('@')[-1].split('/')[0]}…")

    db.users.insert_many(_seed_users())
    db.products.insert_many(_seed_products())
    db.purchases.insert_many(_seed_purchases())
    db.wishlist.insert_many(_seed_wishlist())

    # Useful indexes for the queries the agent will run.
    db.purchases.create_index("userId")
    db.purchases.create_index("orderId", unique=True)
    db.wishlist.create_index([("userId", 1), ("itemId", 1)], unique=True)
    db.products.create_index("category")

    counts = {
        "users": db.users.count_documents({}),
        "products": db.products.count_documents({}),
        "purchases": db.purchases.count_documents({}),
        "wishlist": db.wishlist.count_documents({}),
    }
    print(f"Seeded: {counts}")
    print(f"Demo user id: {DEMO_USER_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
