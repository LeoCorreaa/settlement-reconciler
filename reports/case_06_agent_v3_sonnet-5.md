# Settlement reconciliation report - case_06

Monthly book of 120 orders / 144 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 7**
- **Owed to the seller (to dispute): R$ 397.81**
- **Received unduly (expect clawback): R$ 47.96**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-060034 | Refund amount wrong | 185.32 | Partial refund of 1158.25 on a 1930.41 gross premium electronics order (60% refund). Per rules, marketplace_fee on the refund row should return round_half_up(commission*60%) = round_half_up(308.87*0.6) = 185.32, giving expected refund net of -972.93. Observed refund row has fee=0.00 and net=-1158.25, i.e. the commission refund was never credited back to the seller. |
| MLB-060038 | Commission overcharged | 1.93 | Electronics/premium order, unit_price 36.18<79, qty 3, low-ticket fee 6.25*3=18.75; commission = round_half_up(108.54*0.16)=17.37, total expected fee -36.12 (shipping -21.90 matches observed). Observed marketplace_fee is -38.05, an overcharge of 1.93 versus the contractual fee, which fully explains the -1.93 net delta. |
| MLB-060070 | Wrong shipping deduction | 18.00 | Order MLB-060070 has weight_class 'standard' and gross 131.36 (>=79 threshold), so shipping should be the standard rate of 21.90. The settlement instead deducted the heavy rate of 39.90, an excess deduction of 18.00. |
| MLB-060070 | Commission overcharged | 2.46 | Electronics/classic order, unit_price 65.68<79 so low-ticket fee of 6.25*2=12.50 applies; commission = round_half_up(131.36*0.11)=14.45, total expected fee -26.95. Observed marketplace_fee is -29.41, an overcharge of 2.46 beyond the contractual commission/low-ticket fee. |
| MLB-060087 | Order never settled | 172.10 | Order is 'paid' (fashion premium, gross 236.59) with expected settlement net of 172.10 (fee -42.59, shipping -21.90), but there are zero settlement rows for this order on the statement. |
| MLB-060091 | Order settled twice | -47.96 | Books/classic order with gross 67.18 should settle once for net 47.96 (fee -19.22, low-ticket fee included). Instead two identical payment rows (ST-0600112 and ST-0600145) each carrying the full gross 67.18 and fee -19.22 were posted, doubling net to 95.92. This is not a legitimate split (a split's second row would carry no fees), it is a duplicate of the same payment. |
| MLB-060094 | Wrong shipping deduction | 18.00 | Toys/classic order, weight_class 'standard', gross 308.70 (>=79), so shipping should be the standard 21.90 rate. Settlement instead deducted the heavy rate of 39.90, an excess of 18.00; the commission fee of -37.04 matches expectations exactly, isolating the entire -18.00 net delta to the shipping rate error. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
