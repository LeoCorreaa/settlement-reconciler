"""Render the reconciliation report a finance person would actually use.

Takes the findings of a saved evaluation run and produces one Markdown report
per case: executive summary (money owed to the seller vs expected clawbacks),
the divergence table with evidence, and the recommended next step. The agent
only reads and reports - disputing anything remains a human decision.

Usage:
    python -m scripts.render_report --run results/agent_v3.json
    python -m scripts.render_report --run results/agent_v2.json --case case_12
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import config
from engine import money, to_cents

REPORTS_DIR = config.ROOT / "reports"

TYPE_LABELS = {
    "MISSING_SETTLEMENT": "Order never settled",
    "DUPLICATE_SETTLEMENT": "Order settled twice",
    "ORPHAN_SETTLEMENT": "Settlement for unknown order",
    "FEE_OVERCHARGE": "Commission overcharged",
    "WRONG_SHIPPING_DEDUCTION": "Wrong shipping deduction",
    "REFUND_NOT_SETTLED": "Refund never debited",
    "REFUND_AMOUNT_MISMATCH": "Refund amount wrong",
    "CANCELLED_BUT_SETTLED": "Cancelled order settled",
}


def render_case(entry: dict, model: str) -> str:
    case_id = entry["case"]
    meta = json.loads((config.CASES_DIR / case_id / "case.json").read_text(encoding="utf-8"))
    findings = entry["findings"]

    owed = 0
    clawback = 0
    for f in findings:
        try:
            impact = to_cents(f.get("impact_brl", "0"))
        except (ValueError, AttributeError):
            impact = 0
        if impact > 0:
            owed += impact
        else:
            clawback += -impact

    lines = [
        f"# Settlement reconciliation report - {case_id}",
        "",
        f"Monthly book of {meta['n_orders']} orders / {meta['n_settlement_rows']} "
        f"settlement rows, reconciled automatically by the settlement-reconciler "
        f"agent (model `{model}`).",
        "",
        "## Executive summary",
        "",
        f"- **Divergences found: {len(findings)}**",
        f"- **Owed to the seller (to dispute): R$ {money(owed)}**",
        f"- **Received unduly (expect clawback): R$ {money(clawback)}**",
        "",
    ]

    if findings:
        lines += [
            "## Divergences",
            "",
            "| Order | Issue | Impact (R$) | Evidence |",
            "|---|---|---:|---|",
        ]
        for f in sorted(findings, key=lambda x: x["order_id"]):
            label = TYPE_LABELS.get(f["type"], f["type"])
            explanation = f.get("explanation", "").replace("|", "\\|")
            lines.append(f"| {f['order_id']} | {label} | {f.get('impact_brl', '?')} | {explanation} |")
        lines.append("")
    else:
        lines += ["No divergences found - the settlement matches the contract.", ""]

    unresolved = entry.get("unresolved", [])
    if unresolved:
        lines += [
            "## Needs manual review",
            "",
            "The automated verifier could not fully reconcile the items below - "
            "they are flagged instead of silently dropped:",
            "",
        ]
        for item in unresolved:
            lines.append(f"- **{item['order_id']}**: {item['reason']}")
        lines.append("")

    lines += [
        "## Recommended next step",
        "",
        "Review each divergence above against the marketplace panel, then open "
        "a dispute for the items marked as owed to the seller. This report is "
        "evidence, not an action: no dispute is filed without human approval.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Render per-case reconciliation reports")
    parser.add_argument("--run", required=True, help="path to a results/*.json file")
    parser.add_argument("--case", default="all", help="'all' or one case id")
    args = parser.parse_args()

    payload = json.loads(Path(args.run).read_text(encoding="utf-8"))
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    for entry in payload["per_case"]:
        if args.case != "all" and entry["case"] != args.case:
            continue
        report = render_case(entry, payload["model"])
        out_path = REPORTS_DIR / f"{entry['case']}_{payload['label']}.md"
        out_path.write_text(report, encoding="utf-8")
        print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
