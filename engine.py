"""Deterministic marketplace settlement engine.

Single source of truth for the synthetic marketplace rules described in
datagen/fee_rules.md. Used by:
  - datagen/generate.py  to build correct settlements before planting divergences
  - the agent's tools    to compute expected fees/lines for an order
  - the v3 verifier      to fact-check findings before they are accepted

It never reads truth.json - it derives expectations from the rules only.

All money is integer cents. Settlement rows follow the seller-balance sign
convention: net = gross + marketplace_fee + shipping_fee (fees are negative).
"""

from __future__ import annotations

import json
from pathlib import Path

FEE_SCHEDULE_PATH = Path(__file__).resolve().parent / "datagen" / "fee_schedule.json"

PAID_STATUSES = {"paid", "delivered"}
ALL_STATUSES = {"paid", "delivered", "refunded", "partially_refunded", "cancelled", "chargeback"}


# ---------------------------------------------------------------- money utils

def to_cents(value: str | float | int) -> int:
    """Parse '1234.56' / 1234.56 into integer cents (half-up on floats)."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        sign = -1 if value < 0 else 1
        return sign * int(abs(value) * 100 + 0.5)
    text = str(value).strip().replace(",", "")
    negative = text.startswith("-")
    if negative:
        text = text[1:]
    if "." in text:
        whole, frac = text.split(".", 1)
        frac = (frac + "00")[:2]
    else:
        whole, frac = text, "00"
    cents = int(whole or "0") * 100 + int(frac)
    return -cents if negative else cents


def money(cents: int) -> str:
    """Format integer cents as '1234.56' (with sign)."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def half_up(numerator: int, denominator: int) -> int:
    """Round-half-up integer division for non-negative numerators."""
    return (numerator + denominator // 2) // denominator


# ---------------------------------------------------------------- fee schedule

def load_fee_schedule(path: Path | None = None) -> dict:
    raw = json.loads((path or FEE_SCHEDULE_PATH).read_text(encoding="utf-8"))
    rates = {
        category: {listing: round(rate * 10000) for listing, rate in listings.items()}
        for category, listings in raw["commission_rates"].items()
    }
    return {
        "rates_bp": rates,
        "low_ticket_below_cents": to_cents(raw["low_ticket_fixed_fee"]["unit_price_below"]),
        "low_ticket_fee_cents": to_cents(raw["low_ticket_fixed_fee"]["fee_per_unit"]),
        "free_shipping_threshold_cents": to_cents(raw["seller_shipping"]["free_shipping_threshold"]),
        "shipping_cost_cents": {k: to_cents(v) for k, v in raw["seller_shipping"]["cost"].items()},
        "tolerance_cents": to_cents(raw["tolerance_brl"]),
        "raw": raw,
    }


# ---------------------------------------------------------------- expectations

def commission_cents(order: dict, schedule: dict) -> int:
    """Total commission for an order: percentage fee + low-ticket fixed fee."""
    rate_bp = schedule["rates_bp"][order["category"]][order["listing_type"]]
    fee = half_up(order["gross_cents"] * rate_bp, 10000)
    if order["unit_price_cents"] < schedule["low_ticket_below_cents"]:
        fee += schedule["low_ticket_fee_cents"] * order["quantity"]
    return fee


def shipping_cents(order: dict, schedule: dict) -> int:
    """Shipping charged to the seller (0 when the buyer pays shipping)."""
    if order["gross_cents"] >= schedule["free_shipping_threshold_cents"]:
        return schedule["shipping_cost_cents"][order["weight_class"]]
    return 0


def expected_settlement_lines(order: dict, schedule: dict) -> list[dict]:
    """Expected settlement lines for an order under the documented rules.

    Line dicts: {type, gross_cents, fee_cents, shipping_cents, net_cents}.
    """
    status = order["status"]
    if status == "cancelled":
        return []

    gross = order["gross_cents"]
    fee = commission_cents(order, schedule)
    shipping = shipping_cents(order, schedule)
    payment = {
        "type": "payment",
        "gross_cents": gross,
        "fee_cents": -fee,
        "shipping_cents": -shipping,
        "net_cents": gross - fee - shipping,
    }
    if status in PAID_STATUSES:
        return [payment]

    if status in ("refunded", "partially_refunded"):
        pct = 100 if status == "refunded" else order["refund_pct"]
        refund_gross = half_up(gross * pct, 100)
        refund_fee = half_up(fee * pct, 100)
        refund = {
            "type": "refund",
            "gross_cents": -refund_gross,
            "fee_cents": refund_fee,
            "shipping_cents": 0,
            "net_cents": -refund_gross + refund_fee,
        }
        return [payment, refund]

    if status == "chargeback":
        chargeback = {
            "type": "chargeback",
            "gross_cents": -gross,
            "fee_cents": 0,
            "shipping_cents": 0,
            "net_cents": -gross,
        }
        return [payment, chargeback]

    raise ValueError(f"unknown order status: {status}")


def expected_net_cents(order: dict, schedule: dict) -> int:
    return sum(line["net_cents"] for line in expected_settlement_lines(order, schedule))
