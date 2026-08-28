"""Deterministic verification of submitted findings (v3).

Two independent checks, both against the rules engine and the observed rows -
never against truth.json:

1. Presence + impact: a finding must be supported by the data AND its reported
   impact must equal the rule-derived impact for that divergence type (fee
   deltas come from the fee column, shipping deltas from the shipping column,
   and so on). Validating the amount closes the reward hack where the model
   inflates one finding's impact to make the residual check pass instead of
   locating a coexisting divergence.
2. Completeness: per order, the observed net delta must be fully explained by
   the sum of reported impacts; an unexplained residual above tolerance means
   a divergence is missing or an impact amount is wrong.

Failures are fed back to the agent for one revision round.
"""

from __future__ import annotations

from collections import defaultdict

from engine import expected_settlement_lines, expected_net_cents, money, to_cents


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


def check_completeness(findings: list[dict], case: dict) -> list[dict]:
    """Per-order residual check: observed delta must equal -sum(impacts).

    Sign convention: impact_brl is positive when the seller was hurt, so a
    fully explained order satisfies observed_delta + sum(impacts) ~ 0.
    Returns a list of {"order_id", "reason"} issues.
    """
    schedule = case["schedule"]
    tolerance = schedule["tolerance_cents"]

    rows_by_order: dict[str, list[dict]] = defaultdict(list)
    for row in case["settlements"]:
        rows_by_order[row["order_id"]].append(row)

    deltas: dict[str, int] = {}
    for order in case["orders"]:
        observed = sum(r["net_cents"] for r in rows_by_order.get(order["order_id"], []))
        delta = observed - expected_net_cents(order, schedule)
        if abs(delta) > tolerance:
            deltas[order["order_id"]] = delta
    for order_id, rows in rows_by_order.items():
        if order_id not in case["orders_by_id"]:
            deltas[order_id] = sum(r["net_cents"] for r in rows)

    impacts: dict[str, int] = defaultdict(int)
    issues: list[dict] = []
    for finding in findings:
        try:
            impacts[finding["order_id"]] += to_cents(finding.get("impact_brl", "0"))
        except (ValueError, TypeError):
            issues.append({"order_id": finding["order_id"],
                           "reason": f"impact_brl '{finding.get('impact_brl')}' is not a parseable amount"})

    for order_id, delta in sorted(deltas.items()):
        residual = delta + impacts.get(order_id, 0)
        if abs(residual) > tolerance:
            issues.append({
                "order_id": order_id,
                "reason": (f"the observed settlement is {money(delta)} off the contract for this "
                           f"order, but your findings explain {money(-impacts.get(order_id, 0))}; "
                           f"unexplained residual of {money(residual)}. Either a divergence on "
                           f"this order is missing from your findings (orders can have MORE THAN "
                           f"ONE divergence) or an impact amount is wrong."),
            })
    return issues


def _check(finding: dict, case: dict, rows_by_order: dict, tolerance: int) -> str | None:
    order_id = finding["order_id"]
    kind = finding["type"]
    order = case["orders_by_id"].get(order_id)
    rows = rows_by_order.get(order_id, [])
    payments = [r for r in rows if r["type"] == "payment"]
    refunds = [r for r in rows if r["type"] == "refund"]

    def impact_matches(canonical: int) -> str | None:
        try:
            reported = to_cents(finding.get("impact_brl", "0"))
        except (ValueError, TypeError):
            return f"impact_brl '{finding.get('impact_brl')}' is not a parseable amount"
        if abs(reported - canonical) > tolerance:
            return (f"impact_brl {finding.get('impact_brl')} does not match the rule-derived "
                    f"impact {money(canonical)} for {kind} on {order_id} - if this order's "
                    f"total delta is larger, another divergence coexists on the same order")
        return None

    if kind == "ORPHAN_SETTLEMENT":
        if order is not None:
            return f"{order_id} exists in the seller's book, so its rows are not orphans"
        if not rows:
            return f"no settlement rows reference {order_id}"
        return impact_matches(-sum(r["net_cents"] for r in rows))

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
        return impact_matches(sum(l["net_cents"] for l in expected))

    if kind == "DUPLICATE_SETTLEMENT":
        if exp_payment is None:
            return f"{order_id} should have no payment at all"
        observed_gross = sum(r["gross_cents"] for r in payments)
        if observed_gross <= exp_payment["gross_cents"] + tolerance:
            return (f"payment gross observed {money(observed_gross)} does not exceed "
                    f"expected {money(exp_payment['gross_cents'])}; no duplication")
        excess_net = sum(r["net_cents"] for r in payments) - exp_payment["net_cents"]
        return impact_matches(-excess_net)

    if kind == "FEE_OVERCHARGE":
        if exp_payment is None:
            return f"{order_id} should have no payment row to overcharge"
        observed_fee = sum(r["fee_cents"] for r in payments)
        delta = exp_payment["fee_cents"] - observed_fee
        if delta <= tolerance:
            return (f"observed commission {money(observed_fee)} matches the contracted "
                    f"{money(exp_payment['fee_cents'])}; no overcharge on payment rows")
        return impact_matches(delta)

    if kind == "WRONG_SHIPPING_DEDUCTION":
        if exp_payment is None:
            return f"{order_id} should have no payment row"
        observed_ship = sum(r["shipping_cents"] for r in payments)
        delta = exp_payment["shipping_cents"] - observed_ship
        if abs(delta) <= tolerance:
            return (f"observed shipping {money(observed_ship)} matches expected "
                    f"{money(exp_payment['shipping_cents'])}")
        return impact_matches(delta)

    if kind == "REFUND_NOT_SETTLED":
        if order["status"] not in ("refunded", "partially_refunded"):
            return f"{order_id} has status {order['status']}; no refund is expected"
        if refunds:
            return f"{order_id} has a refund row netting {money(sum(r['net_cents'] for r in refunds))}"
        return impact_matches(exp_refund["net_cents"])

    if kind == "REFUND_AMOUNT_MISMATCH":
        if exp_refund is None:
            return f"{order_id} has status {order['status']}; no refund is expected"
        if not refunds:
            return f"{order_id} has no refund row at all (that is REFUND_NOT_SETTLED)"
        observed_net = sum(r["net_cents"] for r in refunds)
        delta = exp_refund["net_cents"] - observed_net
        if abs(delta) <= tolerance:
            return (f"refund net observed {money(observed_net)} matches expected "
                    f"{money(exp_refund['net_cents'])}")
        return impact_matches(delta)

    if kind == "CANCELLED_BUT_SETTLED":
        if order["status"] != "cancelled":
            return f"{order_id} has status {order['status']}, not cancelled"
        if not rows:
            return f"{order_id} has no settlement rows; nothing was settled"
        return impact_matches(-sum(r["net_cents"] for r in rows))

    return f"unknown divergence type {kind}"
