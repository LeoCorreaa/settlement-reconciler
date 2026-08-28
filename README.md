# Settlement Reconciler

An agentic workflow that reconciles a marketplace seller's order book against
the payment processor's settlement statement, finds every divergence, explains
its root cause with evidence, and quantifies the financial impact.

Built for the micro1 Frontier Engineering Challenge 2026 (Agentic Workflows).

## The user and the bottleneck

**Who:** the finance person of a small or mid-size online store selling on a
marketplace (think Mercado Livre, the largest marketplace in Latin America -
the mechanics are identical on Amazon or eBay).

**The bottleneck:** every month the marketplace settles thousands of
micro-transactions: gross amount minus commission (which depends on category
and listing type), minus low-ticket fixed fees, minus seller-paid shipping,
plus refunds, partial refunds, chargebacks, split payouts. Verifying that the
statement matches the contract is hours of spreadsheet work per week, and in
practice most sellers simply don't do it: fee overcharges of a few reais per
order, refunds that never returned the commission, or orders that were never
settled at all pass silently. Money leaks.

**Why solving it matters:** a reconciliation that runs in minutes, catches
every divergence and explains each one with the contract rule and the numbers
gives the seller money back and an evidence trail to open disputes with the
marketplace. The agent only reads and reports - a human reviews the report and
decides what to dispute (human-in-the-loop by design).

## What gets measured

- **Primary metric:** F1 on divergence detection, where a finding only counts
  as correct if both the order and the divergence type (root cause) match the
  ground truth.
- Secondary: false positives on clean books, cost per run, wall-clock time.
- Dataset: 12 synthetic cases (2 clean, 9 normal, 1 hard) with 42 planted
  divergences across 8 divergence types, generated deterministically with
  ground truth (`python -m datagen.generate`). The hard case combines a
  partial refund, a legitimately split payout and a shorted commission refund
  on the same order.

Solvers never read `truth.json`; it is used only by the evaluator.

## Solutions compared

| Solution | What it is |
|---|---|
| `baseline` | One direct prompt: fee rules + both CSVs, asks for divergences as JSON. Same model, same information as the agent. |
| `agent v1` | Agentic loop with read/paging tools only; the model does all math itself. |
| `agent v2` | v1 + deterministic tools: `scan_mismatches` (candidate deltas, no causes) and `calc_expected` (contractual expectations per order). Arithmetic in tools, judgment in the agent. |
| `agent v3` | v2 + deterministic verification: every submitted finding is fact-checked against the rules engine; rejected findings go back to the agent for one revision round. |

## Results

_To be filled from `results/*.json` after the evaluation runs._

| Solution | F1 | Precision | Recall | Clean-case FPs | Cost | Time |
|---|---|---|---|---|---|---|

## Improvement Changelog

_One entry per meaningful iteration; connected to the evidence above._

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Baseline | Single prompt with rules + both CSVs | _pending_ | _pending_ |

## Main failure mode and hot take

_To be written after the experiments._

## Repository layout

```
engine.py            deterministic rules engine (single source of truth)
config.py            model, prices, paths
datagen/             fee rules + deterministic case generator
cases/               12 generated cases (committed for reproducibility)
solvers/baseline.py  single-prompt baseline
solvers/agent/       tools, prompts, manual tool-use loop, verifier
eval/run.py          scoring harness (F1 vs truth.json)
results/             evaluation outputs (committed as evidence)
trajectories/        JSONL trajectory per agent run (committed as evidence)
```

## Coding agents used

This project was built with **Claude Code** (Anthropic), model Claude Fable 5,
as the coding agent; development session transcripts are included with the
submission. The solution itself calls the Anthropic API (default model
`claude-sonnet-5`) through a hand-written tool-use loop - see
`solvers/agent/loop.py`.

See [REPRODUCE.md](REPRODUCE.md) to run everything from a clean environment.
