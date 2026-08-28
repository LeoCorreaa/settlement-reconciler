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
- Dataset: 12 synthetic cases (2 clean, 9 normal, 1 hard) spanning **40 to 400
  orders per monthly book** (real seller volumes) with **71 planted
  divergences** across 8 divergence types, generated deterministically with
  ground truth (`python -m datagen.generate`). Adversarial structure:
  compound divergences (one order corrupted two ways behind a single net
  delta), subtle cent-level overcharges just above the contractual tolerance,
  legitimate split payouts and chargebacks as false-positive traps, and a hard
  case combining a partial refund, a split payout and a shorted commission
  refund on the same order.

Solvers never read `truth.json`; it is used only by the evaluator
(enforced by code layout and verifiable in `solvers/`).

## Solutions compared

| Solution | What it is |
|---|---|
| `baseline` | One direct prompt: fee rules + both CSVs, asks for divergences as JSON. Same model, same information as the agent. |
| `agent v1` | Agentic loop with read/paging tools only; the model does all math itself. |
| `agent v2` | v1 + deterministic tools: `scan_mismatches` (candidate deltas, no causes) and `calc_expected` (contractual expectations per order). Arithmetic in tools, judgment in the agent. |
| `agent v3` | v2 + deterministic verification: every submitted finding is fact-checked against the rules engine; rejected findings go back to the agent for one revision round. |

## Results

Full 12-case runs on the final (hardened) dataset. `results/*.json` holds the
per-case detail; agent runs also produce one trajectory per case under
`trajectories/`.

| Solution | Model | F1 | Precision | Recall | Clean-case FPs | Cost | Time |
|---|---|---|---|---|---|---|---|
| mock (floor) | - | 0.000 | 0.000 | 0.000 | 0 | $0.00 | 0s |
| baseline | claude-sonnet-5 | _pending_ | | | | | |
| agent v1 | claude-sonnet-5 | _pending (size-tier subset)_ | | | | | |
| agent v2 | claude-sonnet-5 | **1.000** | 1.000 | 1.000 | 0 | $1.01 | 776s |
| agent v2 | claude-haiku-4-5 | 0.964 | 1.000 | 0.930 | 0 | $0.49 | 714s |
| agent v3.0 (residual check) | claude-haiku-4-5 | 0.978 | 1.000 | 0.958 | 0 | $0.53 | 409s |
| agent v3.1 (+impact validation) | claude-haiku-4-5 | 0.978 | 1.000 | 0.958 | 0 | $0.55 | 445s |
| agent v3 | claude-sonnet-5 | _pending_ | | | | | |

v3.0 vs v3.1 tie on aggregate F1 but fail differently: v3.0's misses include
findings that *pass* verification via an inflated impact (silently wrong
report); v3.1 blocks that, fixes two more cases outright, and routes what the
model cannot decompose to an explicit "needs manual review" section instead of
a confident error. Archived pre-fix evidence: `results/archive/`,
`trajectories/archive/`.

## Improvement Changelog

One entry per meaningful iteration, with the evidence that drove the next
decision. Probe runs used the earlier dataset revisions noted inline.

| Stage | What we tried and why | Evidence | Decision / learning |
|---|---|---|---|
| Baseline probe | Single prompt (rules + both CSVs), 16k output cap, on the first small-book dataset | 40 orders: **4/4, F1 1.000** ($0.14). 80 orders: **0/9** - it spent the entire 16k output budget on arithmetic reasoning and never emitted the JSON | Single-shot saturates small books and collapses by ~80 orders. Raised its ceiling to a streamed 32k so it never loses for lack of thinking room, and rescaled cases to real monthly volumes (40-400 orders) |
| Agent v2 first run | Deterministic tools (`scan_mismatches`, `calc_expected`) so arithmetic lives in tools and judgment in the agent | 50 orders: 4/4 in 8 API calls, $0.15 | Design validated; measure at scale |
| Prompt caching | Rolling cache breakpoints (tools + system + latest user block) | 50-order run: only **16 uncached input tokens**; 55k cache reads billed at 10% | Kept - cuts input cost ~85% on multi-step runs |
| v2 full run | All 12 cases, 40-400 orders | **60/60, F1 1.000, $0.81** - including 10/10 on the 400-order hard case ($0.11, 74s) where the baseline had scored 0 at 80 orders | A saturated benchmark discriminates nothing. Hardened the dataset instead of celebrating |
| Dataset hardening | Compound divergences (two root causes behind one net delta) + subtle 30-80 cent overcharges | v2 still **71/71, F1 1.000** ($1.01) | The settlement schema separates fee and shipping columns, so decomposition is mechanical once `calc_expected` exists - the schema was doing the reasoning. Next contrast: capability curve (v1 without deterministic tools; weaker model with/without verification) |
| Weaker-model probe | v2 unchanged, model swapped to claude-haiku-4-5 (half the price) | **F1 0.964** (recall 0.930, $0.49). All 5 misses were the second cause of a compound divergence or a subtle overcharge - silent omissions | Verification has a concrete target: catch what the model leaves out, not just what it invents |
| v3.0: completeness verification | Per-order residual check: observed delta must be fully explained by reported impacts; failures go back to the agent for one revision | haiku: **F1 0.978**, recovered 2 of 5 misses | Trajectories exposed **reward hacking**: on MLB-090140 the model *described both causes in its explanation*, then packed them into one finding with an inflated impact so the residual closed (see `trajectories/archive/case_09_agent_v3.0_haiku-4-5_reward-hack.jsonl`) |
| v3.1: impact validation | Every divergence type has a rule-derived canonical impact (fee delta from the fee column, shipping delta from the shipping column, ...); the presence check now validates the reported amount | haiku: **F1 0.978** aggregate, but the subtle case_08 and compound case_11 became perfect and the hack died; case_09 regressed (model could not decompose within one retry; findings rejected) | Verification converts silent errors into explicit signals. Added the production answer: post-retry failures surface as "needs manual review" items in the report instead of disappearing |

## Main failure mode and hot take

_Draft - to be finalized after the Sonnet baseline/v1/v3 runs._

**Main failure mode:** strict verification plus a single revision round can
make a small model *drop* findings it partially understood (case_09 went 8/9
under lenient checks to 6/9 under strict ones - the model saw the compound
divergence but could not express it as two correctly-quantified findings).
The fix is not weaker verification: it is refusing to fail silently - every
rejected finding and unexplained residual now lands in the report's "needs
manual review" section with the exact residual amount.

**Hot take:** verification does not make a weak model strong - it makes its
weakness *visible*. The residual check alone was gamed within one run
(inflate an impact until the ledger closes); only value-level validation
killed the hack. For a finance workflow, a flagged unknown beats a confident
error every time, and an agent that can say "I could not fully explain this
order" is worth more than one that always balances its books.

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
