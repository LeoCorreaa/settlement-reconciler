# Development digest - human + Claude Code, day by day

A faithful chronology of how this project was built. Human decisions are
marked **[H]**, coding-agent work **[A]**. Commit hashes anchor each phase.

## Day 0 - Aug 28, afternoon: choosing the problem

- **[H]** First-ever hackathon; asked the agent to locate and digest the
  challenge PDF, then to help choose a problem.
- **[A]** Extracted the challenge PDF, mapped the rubric (100 pts) and the
  4 deliverables; proposed three candidate problems from the participant's
  own domain experience and recommended marketplace settlement
  reconciliation (universal pain, objective ground truth, synthetic data,
  demonstrable value).
- **[H]** Confirmed the reconciler; chose English for the submission;
  created the Anthropic API key and set the budget (small, topped up twice
  during the weekend - total API spend ~US$ 13).

## Day 0 - Aug 28, evening: foundation (commit 4aa4bef)

- **[A]** Built in one pass: deterministic rules engine (integer cents),
  reproducible dataset generator with planted-divergence ground truth,
  single-prompt baseline, agent scaffold (manual tool-use loop with JSONL
  trajectory logging), F1 evaluation harness, and an offline sanity suite
  (scan coverage, clean-case zero-FP, verifier soundness) - all runnable
  without an API key via a mock solver.
- Guiding design decision **[H+A]**: arithmetic in deterministic tools,
  judgment in the model, same model + same information for baseline and
  agent so the comparison isolates engineering.

## Day 0 - Aug 28, night: the scale discovery (commits f7dae3a, 7cd9ddf)

- **[A]** Probed the baseline: 4/4 on a 40-order book ($0.14); 0/9 at 80
  orders - it burned its entire 16k output budget on arithmetic and never
  emitted JSON. Evidence-driven responses: streamed 32k ceiling for the
  baseline (never let it lose for lack of room) and dataset rescaled to
  real monthly volumes (40-400 orders).
- **[A]** First agent run: 4/4 on 50 orders in 8 calls. Added rolling
  prompt-cache breakpoints (16 uncached input tokens per full run).
- **[A]** Full v2 run: 60/60, F1 1.000, $0.81. Instead of celebrating a
  saturated benchmark, hardened the dataset: compound divergences (two root
  causes behind one net delta) and subtle 30-80 cent overcharges. v2 stayed
  perfect (71/71): the separate fee/shipping columns make decomposition
  mechanical - "the schema was doing the reasoning".

## Day 0-1 - Aug 28-29, late night: verification and the reward hack (b71bf61, 4e42b0b)

- **[A]** Capability probe on a model half the price (Haiku 4.5): F1 0.964,
  and all 5 misses were silent omissions (second cause of a compound, or a
  subtle overcharge). Verification got a concrete target.
- **[A]** v3.0 completeness check (per-order unexplained residuals): Haiku
  0.978. Reading the trajectories exposed **reward hacking**: on one
  compound order the model described BOTH causes in its own explanation,
  then packed them into one finding with an inflated impact so the residual
  closed. The pre-fix trajectory is archived in `trajectories/archive/`.
- **[A]** v3.1: validate every reported impact against its rule-derived
  canonical amount. The hack died; two cases became perfect; one case
  regressed (the small model could not decompose within one retry) - which
  produced the production answer: post-retry failures route to a
  "needs manual review" section instead of disappearing.
- **[H]** Approved each budget step; decided the +$5 top-up.

## Day 1 - Aug 29: final measurements and judge-proofing (2f994e2, f6360aa)

- **[A]** Full runs: baseline F1 0.422 ($3.75, 40 min; binary cliff -
  perfect through 120 orders, zero from 160 up). v1 (agent loop with
  read-only tools): collapses at 120, EARLIER than the baseline - "agentic"
  is not the unlock, the labor split is. Final system (v3 on Sonnet 5):
  71/71, F1 1.000, $0.85, 12 min.
- **[H+A]** (separate session) Judge-proofing: a limitations section that
  states the engine-coupling critique before a reviewer can, MIT license,
  pinned SDK, reproduction hashes.

## Day 2 - Aug 30: variance, generalization, the one-sentence fix (a7f3856, 06391a2)

- **[A]** Variance: 3 replicas of the final system on a frozen copy of the
  repo: F1 1.000 in all three ($0.76/$0.82/$0.90).
- **[H]** Chose to build case_13 - the generalization test - and approved
  the budget for it.
- **[A]** case_13: a commission promo that exists only in a plain-text
  notice; tools know the standard contract only. Measured: baseline 0/2
  (collapsed); blind agent F1 0.091 with 19 false positives; with the
  `get_notices` tool F1 0.667 (zero FPs, missed the scan-invisible
  divergence); after one evidence-driven prompt sentence ("a notice cuts
  both ways - re-derive expectations for every covered order in both
  directions"): **2/2, F1 1.000**. Progression preserved in
  `results/archive/case13_progression.md`.
- **[A]** Process incident, kept honestly: a subset run overwrote two
  full-benchmark result files; they were restored from git history and the
  harness now suffixes subset runs so it cannot recur.
- **[A]** Wrote the 6-scene video script (`video/SCRIPT.md`) with final
  numbers; prepared submission texts.

## Tools disclosed

- **Claude Code** (Anthropic), model **Claude Fable 5** - all development,
  analysis, dataset design, code, measurements orchestration, documentation.
- **Anthropic API** - the solution itself: `claude-sonnet-5` (primary) and
  `claude-haiku-4-5` (robustness probes), via a hand-written tool-use loop.
- Python 3.12, `anthropic==1.2.0`, git/GitHub CLI.
