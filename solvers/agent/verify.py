"""Deterministic verification of submitted findings (v3).

Each finding is fact-checked against the rules engine and the observed rows -
never against truth.json. A finding that the data cannot support is rejected
with a concrete reason, which is fed back to the agent for one revision round.
"""

from __future__ import annotations

from collections import defaultdict

from engine import expected_settlement_lines, money


def verify_findings(findings: list[dict], case: dict) -> tuple[list[dict], list[dict]]:
    """Returns (accepted, rejected); rejected items carry a 'reason'."""
    schedule = case["schedule"]
    tolerance = schedule["tolerance_cents"]
    rows_by_order: dict[str, list[dict]] = defaultdict(list)
    for row in case["settlements"]:
        rows_by_order[row["order_id"]].append(row)

    accepted, rejected = [], []
    for finding in findings:
        reason = _check(finding, case, rows_by_order, tolerance)
        if reason is None:
            accepted.append(finding)
        else:
            rejected.append({**finding, "reason": reason})
    return accepted, rejected


def _check(finding: dict, case: dict, rows_by_order: dict, tolerance: int) -> str | None:
    order_id = finding["order_id"]
    kind = finding["type"]
    order = case["orders_by_id"].get(order_id)
    rows = rows_by_order.get(order_id, [])
    payments = [r for r in rows if r["type"] == "payment"]
    refunds = [r for r in rows if r["type"] == "refund"]

    if kind == "ORPHAN_SETTLEMENT":
        if order is not None:
            return f"{order_id} exists in the seller's book, so its rows are not orphans"
        if not rows:
            return f"no settlement rows reference {order_id}"
        return None

    if order is None:
        return f"order {order_id} does not exist in the seller's book (did you mean ORPHAN_SETTLEMENT?)"

    expected = expected_settlement_lines(order, case["schedule"])
    exp_payment = next((l for l in expected if l["type"] == "payment"), None)
    exp_refund = next((l for l in expected if l["type"] == "refund"), None)

    if kind == "MISSING_SETTLEMENT":
        if not expected:
            return f"{order_id} is {order['status']} and should have no settlement rows"
        if rows:
            return (f"{order_id} has {len(rows)} settlement row(s) netting "
                    f"{money(sum(r['net_cents'] for r in rows))}, so nothing is missing")
        return None

    if kind == "DUPLICATE_SETTLEMENT":
        if exp_payment is None:
            return f"{order_id} should have no payment at all"
        observed_gross = sum(r["gross_cents"] for r in payments)
        if observed_gross <= exp_payment["gross_cents"] + tolerance:
            return (f"payment gross observed {money(observed_gross)} does not exceed "
                    f"expected {money(exp_payment['gross_cents'])}; no duplication")
        return None

    if kind == "FEE_OVERCHARGE":
        if exp_payment is None:
            return f"{order_id} should have no payment row to overcharge"
        observed_fee = sum(r["fee_cents"] for r in payments)
        if observed_fee >= exp_payment["fee_cents"] - tolerance:
            return (f"observed commission {money(observed_fee)} matches the contracted "
                    f"{money(exp_payment['fee_cents'])}; no overcharge on payment rows")
        return None

    if kind == "WRONG_SHIPPING_DEDUCTION":
        if exp_payment is None:
            return f"{order_id} should have no payment row"
        observed_ship = sum(r["shipping_cents"] for r in payments)
        if abs(observed_ship - exp_payment["shipping_cents"]) <= tolerance:
            return (f"observed shipping {money(observed_ship)} matches expected "
                    f"{money(exp_payment['shipping_cents'])}")
        return None

    if kind == "REFUND_NOT_SETTLED":
        if order["status"] not in ("refunded", "partially_refunded"):
            return f"{order_id} has status {order['status']}; no refund is expected"
        if refunds:
            return f"{order_id} has a refund row netting {money(sum(r['net_cents'] for r in refunds))}"
        return None

    if kind == "REFUND_AMOUNT_MISMATCH":
        if exp_refund is None:
            return f"{order_id} has status {order['status']}; no refund is expected"
        if not refunds:
            return f"{order_id} has no refund row at all (that is REFUND_NOT_SETTLED)"
        observed_net = sum(r["net_cents"] for r in refunds)
        if abs(observed_net - exp_refund["net_cents"]) <= tolerance:
            return (f"refund net observed {money(observed_net)} matches expected "
                    f"{money(exp_refund['net_cents'])}")
        return None

    if kind == "CANCELLED_BUT_SETTLED":
        if order["status"] != "cancelled":
            return f"{order_id} has status {order['status']}, not cancelled"
        if not rows:
            return f"{order_id} has no settlement rows; nothing was settled"
        return None

    return f"unknown divergence type {kind}"
