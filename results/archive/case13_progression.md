# case_13 measurement progression (evidence trail)

All runs on claude-sonnet-5, 2026-08-29. The first three runs' full console
output is preserved in `case13_first_runs_console.log`; the final run's
result JSON is `../agent_v2_sonnet-5_c13.json` (it superseded the
intermediate run's JSON under the same label - the console log is the
evidence for that intermediate row).

| Run | F1 | Precision | Recall | FPs | Cost |
|---|---|---|---|---|---|
| baseline (notice in prompt) | 0.000 | - | 0.000 | 0 (collapsed) | $0.35 |
| agent v2 blind (`--no-notices`) | 0.091 | 0.050 | 0.500 | 19 | $0.47 |
| agent v2 + get_notices (original prompt) | 0.667 | 1.000 | 0.500 | 0 | $0.08 |
| agent v2 + get_notices ("both ways" prompt) | **1.000** | 1.000 | 1.000 | 0 | $0.28 |

The "both ways" iteration changed one thing: the system prompt now states
that a notice cuts both ways (scan candidates may be legitimate under it;
un-flagged orders may still be wrong under it), so the agent re-derives
expectations for every covered order in both directions. That single
sentence took recall on the scan-invisible divergence from 0 to 1.
