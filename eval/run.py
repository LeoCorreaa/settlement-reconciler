"""Evaluation harness.

Runs a solver over the case set and scores it against truth.json:
a finding counts as a true positive when (order_id, type) matches a planted
divergence. Prints per-case detail plus the aggregate table and writes
results/<label>.json for the README and changelog.

Usage:
    python -m eval.run --solver mock
    python -m eval.run --solver baseline
    python -m eval.run --solver agent --variant v2
    python -m eval.run --solver agent --variant v3 --cases case_03,case_12
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import config


def load_truth(case_dir: Path) -> list[dict]:
    data = json.loads((case_dir / "truth.json").read_text(encoding="utf-8"))
    return data["divergences"]


def load_meta(case_dir: Path) -> dict:
    return json.loads((case_dir / "case.json").read_text(encoding="utf-8"))


def score(findings: list[dict], truths: list[dict]) -> dict:
    truth_keys = {(t["order_id"], t["type"]) for t in truths}
    found_keys = {(f["order_id"], f["type"]) for f in findings}
    tp = sorted(truth_keys & found_keys)
    fp = sorted(found_keys - truth_keys)
    fn = sorted(truth_keys - found_keys)
    return {"tp": tp, "fp": fp, "fn": fn}


def run_solver(solver: str, variant: str, case_dir: Path, model: str) -> dict:
    if solver == "mock":
        from solvers import mock
        return mock.solve(case_dir, model)
    if solver == "baseline":
        from solvers import baseline
        return baseline.solve(case_dir, model)
    if solver == "agent":
        from solvers.agent import loop
        return loop.run(case_dir, model, variant=variant)
    raise ValueError(f"unknown solver {solver}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a solver against the case set")
    parser.add_argument("--solver", required=True, choices=["mock", "baseline", "agent"])
    parser.add_argument("--variant", default="v2", choices=["v1", "v2", "v3"],
                        help="agent variant (ignored for other solvers)")
    parser.add_argument("--cases", default="all",
                        help="'all' or comma-separated case ids (e.g. case_03,case_12)")
    parser.add_argument("--model", default=config.MODEL)
    args = parser.parse_args()

    label = args.solver if args.solver != "agent" else f"agent_{args.variant}"
    if args.cases == "all":
        case_dirs = sorted(d for d in config.CASES_DIR.iterdir() if d.is_dir())
    else:
        case_dirs = [config.CASES_DIR / c.strip() for c in args.cases.split(",")]

    print(f"solver={label} model={args.model} cases={len(case_dirs)}\n")

    per_case = []
    totals = {"tp": 0, "fp": 0, "fn": 0, "input_tokens": 0, "output_tokens": 0,
              "cache_read": 0, "cache_write": 0,
              "seconds": 0.0, "errors": 0, "clean_fp": 0}

    for case_dir in case_dirs:
        truths = load_truth(case_dir)
        meta = load_meta(case_dir)
        started = time.time()
        try:
            result = run_solver(args.solver, args.variant, case_dir, args.model)
            error = ""
        except Exception as exc:
            result = {"findings": [], "usage": {"input_tokens": 0, "output_tokens": 0},
                      "steps": 0, "notes": ""}
            error = f"{type(exc).__name__}: {exc}"
            totals["errors"] += 1
        elapsed = time.time() - started

        detail = score(result["findings"], truths)
        n_tp, n_fp, n_fn = len(detail["tp"]), len(detail["fp"]), len(detail["fn"])
        totals["tp"] += n_tp
        totals["fp"] += n_fp
        totals["fn"] += n_fn
        totals["input_tokens"] += result["usage"]["input_tokens"]
        totals["output_tokens"] += result["usage"]["output_tokens"]
        totals["cache_read"] += result["usage"].get("cache_read_input_tokens", 0)
        totals["cache_write"] += result["usage"].get("cache_creation_input_tokens", 0)
        totals["seconds"] += elapsed
        if meta["difficulty"] == "clean":
            totals["clean_fp"] += n_fp

        line = (f"{case_dir.name} [{meta['difficulty']:6s}] "
                f"truth={len(truths):2d} tp={n_tp:2d} fp={n_fp:2d} fn={n_fn:2d} "
                f"steps={result.get('steps', 0):2d} "
                f"tok={result['usage']['input_tokens'] + result['usage']['output_tokens']:6d} "
                f"{elapsed:6.1f}s")
        if error:
            line += f"  ERROR: {error}"
        print(line)
        for key in detail["fp"]:
            print(f"    FP {key[0]} {key[1]}")
        for key in detail["fn"]:
            print(f"    FN {key[0]} {key[1]}")
        if result.get("notes"):
            print(f"    note: {result['notes']}")

        per_case.append({
            "case": case_dir.name, "difficulty": meta["difficulty"],
            "n_truth": len(truths), "tp": n_tp, "fp": n_fp, "fn": n_fn,
            "tp_keys": detail["tp"], "fp_keys": detail["fp"], "fn_keys": detail["fn"],
            "findings": result["findings"], "steps": result.get("steps", 0),
            "usage": result["usage"], "seconds": round(elapsed, 1),
            "notes": result.get("notes", ""), "error": error,
            "trajectory": result.get("trajectory", ""),
        })

    tp, fp, fn = totals["tp"], totals["fp"], totals["fn"]
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    cost = config.estimate_cost_usd(args.model, totals["input_tokens"], totals["output_tokens"],
                                    totals["cache_read"], totals["cache_write"])

    print(f"\n=== {label} aggregate ===")
    print(f"precision={precision:.3f} recall={recall:.3f} F1={f1:.3f} "
          f"(tp={tp} fp={fp} fn={fn}, clean-case FPs={totals['clean_fp']})")
    print(f"tokens: in={totals['input_tokens']:,} out={totals['output_tokens']:,} "
          f"cache_read={totals['cache_read']:,} cache_write={totals['cache_write']:,} "
          f"cost=${cost:.2f} time={totals['seconds']:.0f}s errors={totals['errors']}")
    print("\nREADME row:")
    print(f"| {label} | {f1:.3f} | {precision:.3f} | {recall:.3f} | "
          f"{totals['clean_fp']} | ${cost:.2f} | {totals['seconds']:.0f}s |")

    config.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "label": label, "solver": args.solver,
        "variant": args.variant if args.solver == "agent" else None,
        "model": args.model,
        "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "aggregate": {
            "precision": round(precision, 4), "recall": round(recall, 4),
            "f1": round(f1, 4), "tp": tp, "fp": fp, "fn": fn,
            "clean_case_fps": totals["clean_fp"],
            "input_tokens": totals["input_tokens"],
            "output_tokens": totals["output_tokens"],
            "cache_read_tokens": totals["cache_read"],
            "cache_write_tokens": totals["cache_write"],
            "cost_usd": round(cost, 4), "seconds": round(totals["seconds"], 1),
            "errors": totals["errors"],
        },
        "per_case": per_case,
    }
    out_path = config.RESULTS_DIR / f"{label}.json"
    out_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"\nsaved {out_path}")


if __name__ == "__main__":
    main()
