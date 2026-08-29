# Solution video script (target: 4:45, hard cap 5:00)

Narration in English. PT-BR notes for the presenter are marked with `>` and
are not read aloud. Numbers in [BRACKETS] get filled after today's runs.

Recording setup: full-screen terminal + editor, 1080p, OBS or Win+Alt+R.
Have three windows ready: (1) terminal at the repo, (2) README.md rendered
on GitHub, (3) reports/case_12_agent_v3_sonnet-5.md rendered.

---

## Scene 1 - The problem (0:00-0:35)

SCREEN: GitHub README top; scroll slowly through "The user and the bottleneck".

NARRATION:
"Marketplace sellers get a monthly settlement statement with hundreds of
micro-transactions: commissions that vary by category, low-ticket fees,
seller-paid shipping, partial refunds, chargebacks, split payouts. Verifying
it against the contract is hours of spreadsheet work, so in practice nobody
does it - and money leaks silently: overcharged fees, refunds that never
return the commission, orders that were never settled at all. I built an
agent that audits the whole month and hands the seller a dispute-ready
report. The agent only reads and reports - a human decides what to dispute."

> Fala com calma. 35 segundos é mais tempo do que parece.

## Scene 2 - The baseline and the cliff (0:35-1:10)

SCREEN: README results table + the scale-cliff table.

NARRATION:
"The honest baseline is the same model, same fee rules, one big prompt with
both files, and a generous 32-thousand-token thinking budget. It aces small
books - perfect through 120 orders. Then it falls off a cliff: from 160
orders up it scores exactly zero, because it exhausts its entire reasoning
budget doing arithmetic and never even emits the answer. Overall: F1 0.42,
three dollars seventy-five, forty minutes. And here is the anti-hype twist:
an agent loop WITHOUT the right tools collapses even earlier than the plain
prompt. 'Agentic' is not the unlock."

## Scene 3 - Live run (1:10-2:40)

SCREEN: terminal. Type and run:
    python -m eval.run --solver agent --variant v3 --cases case_12
While it runs (~2 min), narrate over the live output; if it finishes early,
open trajectories/rendered/case_12_agent_v3_sonnet-5.md and scroll.

NARRATION:
"Let's run the final system live on the hardest case: 400 orders, 460
settlement rows, 13 planted divergences, including one order that is
partially refunded AND split across two payout rows AND shorted on the
returned commission. The design is a labor split. A deterministic scan does
the arithmetic: expected versus observed, per order - it points WHERE to
look, never WHY. The model does the judgment: for each candidate it pulls
the order, the settlement rows and the contractual expectation, and decides
which rule was broken. Then a deterministic verifier checks every finding's
amount against the rule-derived value, and checks that every order's delta
is fully explained. Anything that fails goes back to the agent exactly once;
anything still unexplained is routed to a needs-manual-review section
instead of being silently dropped. There it is: 13 out of 13, zero false
positives, four API calls beyond the scan, about two minutes, eleven cents."

SCREEN (end of scene): reports/case_12_agent_v3_sonnet-5.md - the executive
summary and the MLB-120125 double row.

## Scene 4 - Results (2:40-3:25)

SCREEN: README results table, then the variance note.

NARRATION:
"Across the full 12-case benchmark - 71 planted divergences, two clean books
as false-positive traps - the final agent scores a perfect F1 of 1.0 for 85
cents in 12 minutes, versus the baseline's 0.42 for 3.75 in 40 minutes.
Better, 4.4 times cheaper and 3.4 times faster at once. We re-ran the final
system three times on frozen code: F1 1.000 in all three replicas, so the
headline is not a lucky roll. On a model half the
price, the same architecture scores 0.96, and verification pushes it to
0.98 - I'll come back to what that taught us."

## Scene 5 - Changelog, the change that mattered most, and the one we removed (3:25-4:15)

SCREEN: README Improvement Changelog, scroll slowly.

NARRATION:
"Eleven measured iterations. The change that contributed most: moving
arithmetic out of the model into deterministic tools - that single change
took the agent from collapsing at 120 orders to perfect at 400. The
experiment we removed: trusting a residual check alone as verification.
Within one run, the cheaper model learned to game it - it described BOTH
root causes of a compound divergence in its own explanation, then packed
them into one finding with an inflated amount so the ledger closed. The
trajectory is archived in the repo. We replaced it with value-level
validation: every divergence type has a canonical amount derivable from the
rules, so an inflated impact is rejected and the hidden second cause
resurfaces."

## Scene 6 - Judgment under incomplete rules + hot take (4:15-4:50)

SCREEN: cases/case_13/notices.md, then the case_13 result line in the README.

NARRATION:
"One last test. Real marketplaces change fees via plain-text notices. In
case 13, a promo discount exists only in a notice; every calculator tool
knows just the standard contract, so the deterministic scan flags nineteen
legitimate promo orders as suspects - and the one real overcharge looks
perfectly correct. Blind, the agent filed nineteen false accusations - a
catastrophic report. Reading the notice, it dismissed all nineteen; and
after one evidence-driven prompt iteration - telling it a notice cuts both
ways - it found both real divergences too. A perfect two for two. That is
the point of the whole project: determinism does the arithmetic, judgment
handles what the rules don't cover, and verification makes failure visible
instead of silent. My hot take: verification does not make a weak model
strong - it makes its weakness visible. In finance, a flagged unknown beats
a confident error every time. Everything here - code, dataset, evaluation,
trajectories - is reproducible from the repo for a few dollars. Thanks for
watching."

---

## Recording checklist

- [ ] Terminal font size 16+, dark theme, window maximized
- [ ] Run `python -m eval.run --solver agent --variant v3 --cases case_12`
      once BEFORE recording (warm cache = faster, cheaper live run)
- [ ] Close notifications (Focus Assist on)
- [ ] Record in one take if possible; small stumbles are fine
- [ ] Export 1080p mp4; upload as YouTube unlisted; paste the link in the
      HackerEarth submission form
