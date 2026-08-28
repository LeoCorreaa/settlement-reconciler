"""Tool implementations exposed to the reconciliation agent.

Deterministic reads over the case data plus the rules engine. The arithmetic
lives here on purpose: tools do the mechanical work, the agent does the
judgment (root-causing, classification, deciding what is worth reporting).

Variants control which tools exist:
  v1: paging/read tools only - the agent does all math itself
  v2+: adds scan_mismatches (candidate deltas, no causes) and calc_expected
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict

import config
from engine import expected_settlement_lines, money

ORDERS_PAGE = 25
SETTLEMENTS_PAGE = 30


def _compact_order(o: dict) -> dict:
    return {
        "id": o["order_id"], "date": o["order_date"], "status": o["status"],
        "cat": o["category"], "listing": o["listing_type"], "weight": o["weight_class"],
        "unit": money(o["unit_price_cents"]), "qty": o["quantity"],
        "gross": money(o["gross_cents"]), "inst": o["installments"],
        "refund": money(o["refund_amount_cents"]),
    }


def _compact_row(r: dict) -> dict:
    return {
        "sid": r["settlement_id"], "oid": r["order_id"], "date": r["settlement_date"],
        "type": r["type"], "gross": money(r["gross_cents"]), "fee": money(r["fee_cents"]),
        "ship": money(r["shipping_cents"]), "net": money(r["net_cents"]),
    }


class CaseTools:
    def __init__(self, case: dict, variant: str):
        self.case = case
        self.variant = variant
        self.schedule = case["schedule"]
        self.rows_by_order: dict[str, list[dict]] = defaultdict(list)
        for row in case["settlements"]:
            self.rows_by_order[row["order_id"]].append(row)
        self.submitted: list[dict] | None = None

    # ------------------------------------------------------------- registry

    def defs(self) -> list[dict]:
        tools = [
            {
                "name": "get_case_summary",
                "description": "Counts and totals for the whole case: orders by status, settlement rows by type, period covered.",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "get_fee_rules",
                "description": "The contractual fee rules document (commissions, shipping, refunds, chargebacks, split settlements, tolerance).",
                "input_schema": {"type": "object", "properties": {}},
            },
            {
                "name": "list_orders",
                "description": f"Page through the seller's orders ({ORDERS_PAGE} per page), optionally filtered by status.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "offset": {"type": "integer", "description": "0-based offset"},
                        "status": {"type": "string", "description": "optional status filter; empty for all"},
                    },
                },
            },
            {
                "name": "list_settlements",
                "description": f"Page through the settlement statement rows ({SETTLEMENTS_PAGE} per page).",
                "input_schema": {
                    "type": "object",
                    "properties": {"offset": {"type": "integer", "description": "0-based offset"}},
                },
            },
            {
                "name": "get_order",
                "description": "Full detail of one order from the seller's book.",
                "input_schema": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                },
            },
            {
                "name": "get_order_settlements",
                "description": "All settlement rows for one order_id, with summed gross/fee/shipping/net.",
                "input_schema": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                },
            },
            {
                "name": "submit_findings",
                "description": "Submit the final list of divergences. Call exactly once, when the reconciliation is complete. Submit an empty list if the books are clean.",
                "strict": True,
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "findings": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "order_id": {"type": "string"},
                                    "type": {"type": "string", "enum": config.DIVERGENCE_TYPES},
                                    "explanation": {"type": "string", "description": "root cause with the numbers as evidence"},
                                    "impact_brl": {"type": "string", "description": "signed amount; positive = seller was hurt"},
                                },
                                "required": ["order_id", "type", "explanation", "impact_brl"],
                                "additionalProperties": False,
                            },
                        },
                    },
                    "required": ["findings"],
                    "additionalProperties": False,
                },
            },
        ]
        if self.variant != "v1":
            tools.insert(2, {
                "name": "scan_mismatches",
                "description": "Deterministic sweep comparing every order's expected settlement (per the rules) with the observed rows. Returns candidates with net deltas beyond tolerance, orders with no rows, unexpected rows, and orphan settlement rows. It does NOT determine causes - investigate each candidate.",
                "input_schema": {"type": "object", "properties": {}},
            })
            tools.insert(3, {
                "name": "calc_expected",
                "description": "Expected fees and settlement lines for one order under the contractual rules: commission rate, low-ticket fee, shipping, per-line values and expected net total.",
                "input_schema": {
                    "type": "object",
                    "properties": {"order_id": {"type": "string"}},
                    "required": ["order_id"],
                },
            })
        return tools

    # ------------------------------------------------------------- dispatch

    def execute(self, name: str, tool_input: dict) -> str:
        handler = getattr(self, f"tool_{name}", None)
        if handler is None:
            return json.dumps({"error": f"unknown tool {name}"})
        try:
            result = handler(**(tool_input or {}))
        except TypeError as exc:
            result = {"error": f"bad arguments: {exc}"}
        except Exception as exc:  # surface tool bugs to the transcript, not a crash
            result = {"error": f"{type(exc).__name__}: {exc}"}
        return json.dumps(result, separators=(",", ":"))

    # ---------------------------------------------------------------- tools

    def tool_get_case_summary(self) -> dict:
        orders = self.case["orders"]
        rows = self.case["settlements"]
        return {
            "orders": {"total": len(orders), "by_status": dict(Counter(o["status"] for o in orders))},
            "settlement_rows": {"total": len(rows), "by_type": dict(Counter(r["type"] for r in rows))},
            "order_dates": {"first": min(o["order_date"] for o in orders),
                            "last": max(o["order_date"] for o in orders)},
            "gross_total": money(sum(o["gross_cents"] for o in orders)),
            "settlement_net_total": money(sum(r["net_cents"] for r in rows)),
        }

    def tool_get_fee_rules(self) -> dict:
        return {"fee_rules_markdown": config.FEE_RULES_PATH.read_text(encoding="utf-8")}

    def tool_list_orders(self, offset: int = 0, status: str = "") -> dict:
        pool = [o for o in self.case["orders"] if not status or o["status"] == status]
        page = pool[offset:offset + ORDERS_PAGE]
        return {
            "total_matching": len(pool), "offset": offset, "returned": len(page),
            "has_more": offset + ORDERS_PAGE < len(pool),
            "orders": [_compact_order(o) for o in page],
        }

    def tool_list_settlements(self, offset: int = 0) -> dict:
        rows = self.case["settlements"]
        page = rows[offset:offset + SETTLEMENTS_PAGE]
        return {
            "total": len(rows), "offset": offset, "returned": len(page),
            "has_more": offset + SETTLEMENTS_PAGE < len(rows),
            "rows": [_compact_row(r) for r in page],
        }

    def tool_get_order(self, order_id: str) -> dict:
        order = self.case["orders_by_id"].get(order_id)
        if order is None:
            return {"error": f"order {order_id} not found in the seller's book"}
        return _compact_order(order)

    def tool_get_order_settlements(self, order_id: str) -> dict:
        rows = self.rows_by_order.get(order_id, [])
        return {
            "order_id": order_id,
            "rows": [_compact_row(r) for r in rows],
            "sums": {
                "gross": money(sum(r["gross_cents"] for r in rows)),
                "fee": money(sum(r["fee_cents"] for r in rows)),
                "ship": money(sum(r["shipping_cents"] for r in rows)),
                "net": money(sum(r["net_cents"] for r in rows)),
            },
        }

    def tool_scan_mismatches(self) -> dict:
        tolerance = self.schedule["tolerance_cents"]
        known = set(self.case["orders_by_id"])
        candidates = []
        for order in self.case["orders"]:
            expected = expected_settlement_lines(order, self.schedule)
            expected_net = sum(line["net_cents"] for line in expected)
            rows = self.rows_by_order.get(order["order_id"], [])
            observed_net = sum(r["net_cents"] for r in rows)
            if expected and not rows:
                issue = "no_rows"
            elif rows and not expected:
                issue = "unexpected_rows"
            elif abs(observed_net - expected_net) > tolerance:
                issue = "net_delta"
            else:
                continue
            candidates.append({
                "order_id": order["order_id"], "status": order["status"], "issue": issue,
                "expected_net": money(expected_net), "observed_net": money(observed_net),
                "delta": money(observed_net - expected_net), "rows_observed": len(rows),
            })
        for order_id, rows in self.rows_by_order.items():
            if order_id not in known:
                candidates.append({
                    "order_id": order_id, "status": "NOT_IN_ORDER_BOOK", "issue": "orphan_rows",
                    "expected_net": "0.00", "observed_net": money(sum(r["net_cents"] for r in rows)),
                    "delta": money(sum(r["net_cents"] for r in rows)), "rows_observed": len(rows),
                })
        candidates.sort(key=lambda c: -abs(int(c["delta"].replace(".", "").replace("-", "") or 0)))
        return {
            "tolerance_brl": money(tolerance),
            "candidates": candidates,
            "note": "Deltas only - causes are NOT determined. Investigate each candidate before reporting.",
        }

    def tool_calc_expected(self, order_id: str) -> dict:
        order = self.case["orders_by_id"].get(order_id)
        if order is None:
            return {"error": f"order {order_id} not found in the seller's book"}
        rate_bp = self.schedule["rates_bp"][order["category"]][order["listing_type"]]
        lines = expected_settlement_lines(order, self.schedule)
        return {
            "order": _compact_order(order),
            "commission_rate_pct": rate_bp / 100,
            "low_ticket_fee_applies": order["unit_price_cents"] < self.schedule["low_ticket_below_cents"],
            "expected_lines": [
                {"type": l["type"], "gross": money(l["gross_cents"]), "fee": money(l["fee_cents"]),
                 "ship": money(l["shipping_cents"]), "net": money(l["net_cents"])}
                for l in lines
            ],
            "expected_net_total": money(sum(l["net_cents"] for l in lines)),
            "note": "Payment may legitimately arrive split across two rows (fees on the first).",
        }

    def tool_submit_findings(self, findings: list) -> dict:
        from solvers.common import validate_findings
        clean, errors = validate_findings(findings)
        if errors:
            return {"accepted": False, "errors": errors}
        self.submitted = clean
        return {"accepted": True, "count": len(clean)}
