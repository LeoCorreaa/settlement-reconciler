"""Offline sanity checks for the dataset, scan and verifier (no API calls).

1. Coverage: scan_mismatches must surface every planted divergence's order_id
   (if the deterministic sweep can't see it, no solver can).
2. Cleanliness: clean cases and untouched orders must produce ZERO candidates
   (split settlements and rounding must not look like divergences).
3. Verifier soundness: the ground truth, submitted as findings, must be 100%
   accepted; deliberately wrong findings must be rejected.

Usage:
    python -m scripts.sanity_check
"""

from __future__ import annotations

import json
import sys
from collections import Counter

import config
from engine import money, to_cents
from solvers import common
from solvers.agent.tools import CaseTools
from solvers.agent.verify import check_completeness, verify_findings

failures = 0


def fail(message: str) -> None:
    global failures
    failures += 1
    print(f"  FAIL {message}")


def main() -> None:
    case_dirs = sorted(d for d in config.CASES_DIR.iterdir() if d.is_dir())
    for case_dir in case_dirs:
        truths = json.loads((case_dir / "truth.json").read_text(encoding="utf-8"))["divergences"]
        meta = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
        case = common.load_case(case_dir)
        tools = CaseTools(case, "v2")
        scan = json.loads(tools.execute("scan_mismatches", {}))
        candidate_ids = {c["order_id"] for c in scan["candidates"]}
        truth_ids = {t["order_id"] for t in truths}

        if meta["difficulty"] == "generalization":
            # case_13 inverts the usual contract: the standard-rules scan MUST
            # flag the legitimate promo orders as noise, MUST miss the
            # promo-not-applied divergence (it looks correct under standard
            # rules), and must still see the ordinary refund divergence.
            promo_ids = set(meta["promo_eligible_orders"])
            victim = next(t["order_id"] for t in truths if t["type"] == "FEE_OVERCHARGE")
            refund_truth = next(t["order_id"] for t in truths
                                if t["type"] == "REFUND_AMOUNT_MISMATCH")
            print(f"{case_dir.name}: {len(truths)} real truths, "
                  f"{len(candidate_ids)} scan candidates (promo noise expected)")
            if len(candidate_ids) < 10:
                fail("expected heavy promo noise in the scan (>=10 candidates)")
            if victim in candidate_ids:
                fail(f"promo victim {victim} should be INVISIBLE to the standard-rules scan")
            if refund_truth not in candidate_ids:
                fail(f"refund divergence {refund_truth} must be visible to the scan")
            for promo_id in sorted(promo_ids - {victim} - candidate_ids):
                fail(f"legitimate promo order {promo_id} should look like a candidate")
            continue

        print(f"{case_dir.name}: {len(truths)} truths, {len(candidate_ids)} scan candidates")

        # 1. every planted divergence must be visible to the scan
        for missing in sorted(truth_ids - candidate_ids):
            fail(f"planted divergence on {missing} is invisible to scan_mismatches")

        # 2. no false candidates: every candidate must belong to a truth
        for extra in sorted(candidate_ids - truth_ids):
            fail(f"scan flags {extra} but no divergence was planted there")

        # 3a. ground truth submitted as findings must be fully accepted
        as_findings = [{"order_id": t["order_id"], "type": t["type"],
                        "explanation": t["note"], "impact_brl": t["impact_brl"]}
                       for t in truths]
        accepted, rejected = verify_findings(as_findings, case)
        for r in rejected:
            fail(f"verifier rejected TRUE finding {r['order_id']} {r['type']}: {r['reason']}")

        # 3b. wrong findings must be rejected
        clean_orders = [o for o in case["orders"] if o["order_id"] not in truth_ids
                        and o["status"] in ("paid", "delivered")]
        bogus = [{"order_id": o["order_id"], "type": "FEE_OVERCHARGE",
                  "explanation": "bogus", "impact_brl": "1.00"} for o in clean_orders[:3]]
        accepted, rejected = verify_findings(bogus, case)
        for a in accepted:
            fail(f"verifier accepted BOGUS finding {a['order_id']} FEE_OVERCHARGE")

        # 3c. the full truth set must leave no unexplained residuals
        for issue in check_completeness(as_findings, case):
            fail(f"completeness flags residual with FULL truth on {issue['order_id']}")

        # 3d. dropping one divergence of a compound order must be caught
        multi = [oid for oid, n in Counter(t["order_id"] for t in truths).items() if n > 1]
        for target in multi:
            removed_one = False
            partial = []
            for f in as_findings:
                if not removed_one and f["order_id"] == target:
                    removed_one = True
                    continue
                partial.append(f)
            if not any(i["order_id"] == target for i in check_completeness(partial, case)):
                fail(f"completeness misses a dropped divergence on compound order {target}")

        # 3e. inflating one finding's impact to absorb a compound order's whole
        # delta (the reward hack) must be rejected by impact validation
        for target in multi:
            entries = [t for t in truths if t["order_id"] == target]
            total = sum(to_cents(t["impact_brl"]) for t in entries)
            inflated = {"order_id": target, "type": entries[0]["type"],
                        "explanation": "inflated to cover the whole delta",
                        "impact_brl": money(total)}
            accepted, _ = verify_findings([inflated], case)
            if accepted:
                fail(f"verifier accepted INFLATED impact on compound order {target}")

    print()
    if failures:
        print(f"{failures} sanity failure(s)")
        sys.exit(1)
    print("all sanity checks passed")


if __name__ == "__main__":
    main()
