# HackerEarth submission - copy-paste texts

Fill the form at: challenge dashboard > Submissions > New Submission.
Paste each block into the matching field; trim to fit character limits if a
field is shorter.

---

## Title

Settlement Reconciler - an agentic auditor for marketplace payouts

## Short summary / tagline (if the form has one)

An agent that audits a marketplace seller's monthly settlement against the
contract: finds every divergence, explains the root cause with evidence, and
quantifies what to dispute. Final system: F1 1.000 on 71 planted divergences
across 40-400-order books for $0.85, where a strong single-prompt baseline
scores 0.42 for $3.75. Stable across 3 replicas; survives a
generalization test where the rules are deliberately incomplete.

## Long description

**Who has the problem.** The finance person of a store selling on a
marketplace (Mercado Livre, Amazon, eBay - our synthetic data mirrors
Mercado Livre mechanics). Every month the processor settles hundreds of
micro-transactions: category-dependent commissions, low-ticket fees,
seller-paid shipping, partial refunds, chargebacks, split payouts.

**The bottleneck.** Verifying the statement against the contract is hours of
spreadsheet work, so in practice nobody does it - and money leaks silently:
overcharged commissions, refunds that never return the fee, orders never
settled at all.

**The solution.** A labor-split agent: a deterministic scan does the
arithmetic (expected vs observed per order - WHERE to look, never WHY); an
LLM agent investigates each candidate with contractual calculator tools and
attributes the root cause among 8 divergence types; a deterministic verifier
validates every reported amount against its rule-derived canonical value AND
checks that each order's delta is fully explained, sending failures back for
one revision; whatever still cannot be explained is routed to a
needs-manual-review section instead of failing silently. The output is a
dispute-ready report a finance person would sign. The agent only reads and
reports - disputing is always a human decision.

**Measured results** (12-case benchmark, 71 planted divergences, ground
truth, clean-book false-positive traps):

- Final agent (claude-sonnet-5): F1 1.000, zero false positives, $0.85,
  12 min - stable across 3 frozen-code replicas (1.000/1.000/1.000).
- Honest baseline (same model, same rules, one prompt, streamed 32k
  thinking budget): F1 0.422, $3.75, 40 min - perfect through 120 orders,
  exactly zero from 160 up (a binary scale cliff).
- Agent without deterministic tools (v1): collapses at 120 orders,
  EARLIER than the baseline - "agentic" is not the unlock; the labor split is.
- On a model half the price (claude-haiku-4-5): 0.964 bare, 0.978 with
  verification; the misses became explicit flags instead of silent errors.

**Generalization under incomplete rules (case_13).** A commission promo
exists only in a plain-text notice; every tool knows just the standard
contract. Blind, the pipeline files 19 false accusations (F1 0.091).
Reading the notice, the agent dismisses all 19; after one evidence-driven
prompt sentence ("a notice cuts both ways"), it scores a perfect 2/2 -
judgment earning its keep exactly where determinism ends.

**Discovered along the way** (full Improvement Changelog in the README, 14
measured iterations): the model reward-hacking our residual check by
inflating one finding's impact until the ledger closed - caught via the
logged trajectory (archived in the repo) and killed with value-level
validation.

**Coding agents.** Built entirely with Claude Code (model Claude Fable 5);
every commit is co-authored, and `dev-trajectories/` documents the
collaboration. The solution calls the Anthropic API through a hand-written
tool-use loop with prompt caching; all 53 solution trajectories (JSONL +
readable renderings) are committed.

**Reproducibility.** Deterministic dataset generator (fixed seeds, cases
committed), exact commands, pinned SDK, measured costs (~$7-8 to reproduce
every table, ~$4.60 for the headline comparison) - see REPRODUCE.md.
Limitations are stated up front in the README.

## Links

- Repository: https://github.com/LeoCorreaa/settlement-reconciler
- Video (under 5 min): https://youtu.be/VE6iOZbgbOc
- Reproduction guide: https://github.com/LeoCorreaa/settlement-reconciler/blob/main/REPRODUCE.md
- Improvement Changelog: https://github.com/LeoCorreaa/settlement-reconciler#improvement-changelog
- Agent trajectories: https://github.com/LeoCorreaa/settlement-reconciler/tree/main/trajectories
- Coding-agent evidence: https://github.com/LeoCorreaa/settlement-reconciler/tree/main/dev-trajectories

## Tech stack (if asked)

Python 3.12, Anthropic API (claude-sonnet-5, claude-haiku-4-5),
anthropic==1.2.0, hand-written tool-use loop with prompt caching, Claude
Code (Claude Fable 5) as the coding agent. No frameworks.

## AI tools disclosure (if asked)

Coding agent: Claude Code with Claude Fable 5 (required disclosure;
development trajectories in dev-trajectories/). Solution models:
claude-sonnet-5 and claude-haiku-4-5 via the Anthropic API. All agent
trajectories for the solution are committed in trajectories/.
