"""Shared solver utilities: case loading, findings validation, JSON parsing.

A "finding" is one reported divergence:
    {"order_id": str, "type": <one of config.DIVERGENCE_TYPES>,
     "explanation": str, "impact_brl": str}

Solvers read ONLY orders.csv, settlement.csv and the fee rules. truth.json is
for the evaluator alone.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

import config
from engine import load_fee_schedule, to_cents


def load_case(case_dir: Path) -> dict:
    orders = []
    with (case_dir / "orders.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            orders.append({
                "order_id": row["order_id"],
                "order_date": row["order_date"],
                "status": row["status"],
                "category": row["category"],
                "listing_type": row["listing_type"],
                "weight_class": row["weight_class"],
                "unit_price_cents": to_cents(row["unit_price"]),
                "quantity": int(row["quantity"]),
                "gross_cents": to_cents(row["gross_amount"]),
                "installments": int(row["installments"]),
                "refund_pct": _refund_pct(row),
                "refund_amount_cents": to_cents(row["refund_amount"]),
            })

    settlements = []
    with (case_dir / "settlement.csv").open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            settlements.append({
                "settlement_id": row["settlement_id"],
                "order_id": row["order_id"],
                "settlement_date": row["settlement_date"],
                "type": row["type"],
                "gross_cents": to_cents(row["gross_amount"]),
                "fee_cents": to_cents(row["marketplace_fee"]),
                "shipping_cents": to_cents(row["shipping_fee"]),
                "net_cents": to_cents(row["net_amount"]),
            })

    return {
        "case_dir": case_dir,
        "orders": orders,
        "orders_by_id": {o["order_id"]: o for o in orders},
        "settlements": settlements,
        "schedule": load_fee_schedule(),
    }


def _refund_pct(row: dict) -> int:
    if row["status"] == "refunded":
        return 100
    if row["status"] != "partially_refunded":
        return 0
    gross = to_cents(row["gross_amount"])
    refund = to_cents(row["refund_amount"])
    return round(refund * 100 / gross) if gross else 0


def read_raw_csvs(case_dir: Path) -> tuple[str, str]:
    orders_csv = (case_dir / "orders.csv").read_text(encoding="utf-8")
    settlement_csv = (case_dir / "settlement.csv").read_text(encoding="utf-8")
    return orders_csv, settlement_csv


def fee_rules_text() -> str:
    return config.FEE_RULES_PATH.read_text(encoding="utf-8")


def validate_findings(findings: object) -> tuple[list[dict], list[str]]:
    """Normalize and validate a findings list; returns (clean, errors)."""
    errors: list[str] = []
    clean: list[dict] = []
    if not isinstance(findings, list):
        return [], [f"findings must be a list, got {type(findings).__name__}"]
    for i, item in enumerate(findings):
        if not isinstance(item, dict):
            errors.append(f"finding #{i} is not an object")
            continue
        order_id = str(item.get("order_id", "")).strip()
        div_type = str(item.get("type", "")).strip().upper().replace(" ", "_")
        if not order_id:
            errors.append(f"finding #{i} has no order_id")
            continue
        if div_type not in config.DIVERGENCE_TYPES:
            errors.append(f"finding #{i} has invalid type '{div_type}'")
            continue
        clean.append({
            "order_id": order_id,
            "type": div_type,
            "explanation": str(item.get("explanation", "")).strip(),
            "impact_brl": str(item.get("impact_brl", "")).strip(),
        })
    return clean, errors


def extract_json(text: str) -> object:
    """Best-effort extraction of the first JSON value from model text."""
    text = text.strip()
    if "```" in text:
        for chunk in text.split("```"):
            chunk = chunk.strip()
            if chunk.startswith("json"):
                chunk = chunk[4:].strip()
            if chunk[:1] in "[{":
                try:
                    return json.loads(chunk)
                except json.JSONDecodeError:
                    pass
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        in_string = False
        escape = False
        for pos in range(start, len(text)):
            ch = text[pos]
            if in_string:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_string = False
                continue
            if ch == '"':
                in_string = True
            elif ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:pos + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError("no parseable JSON found in model output")
