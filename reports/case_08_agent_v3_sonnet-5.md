# Settlement reconciliation report - case_08

Monthly book of 200 orders / 232 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 7**
- **Owed to the seller (to dispute): R$ 156.90**
- **Received unduly (expect clawback): R$ 2612.44**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-080018 | Refund amount wrong | 41.38 | Partially refunded order (toys, classic, gross 1149.47, refund_amount 344.84 = 30%). Expected refund row: gross -344.84, marketplace_fee +41.38 (30% of the 137.94 commission returned), net -303.46. Observed refund row ST-0800023 has marketplace_fee 0.00 and net -344.84, i.e. the commission was never returned to the seller. Total expected net 686.17 vs observed 644.79, a shortfall of 41.38. |
| MLB-080068 | Wrong shipping deduction | 21.90 | Order is electronics/premium, weight_class 'heavy', so shipping should be the heavy rate 39.90. Expected payment row: fee -88.70, ship -39.90, net 425.75. Observed row ST-0800078 deducted ship -61.80 (39.90+21.90, i.e. both heavy and standard rates combined), giving net 403.85 - a shortfall of 21.90. |
| MLB-080078 | Cancelled order settled | -336.03 | Order status is 'cancelled' (toys, premium, gross 431.24). Per rules, cancelled orders must have NO settlement rows. However settlement row ST-0800232 exists with net 336.03 paid to the seller. |
| MLB-080086 | Commission overcharged | 0.46 | Order is electronics/classic, gross 4219.64, correct commission 11% => 4219.64*0.11=464.16 (rounded), expected net 3715.58. Observed settlement ST-0800098 charged fee -464.62, giving net 3715.12 - an overcharge of 0.46, which exceeds the 0.02 rounding tolerance. |
| MLB-080113 | Commission overcharged | 14.25 | Order is fashion/premium, gross 734.75, correct commission rate 18% => 734.75*0.18=132.255 rounds to 132.26, expected net 580.59. Observed settlement ST-0800128 charged fee -146.51 (effectively ~19.94%), giving net 566.34, an overcharge of 14.25. |
| MLB-080173 | Order never settled | 78.91 | Delivered order (fashion, classic, gross 130.24, unit price 65.12 < 79 so low-ticket fee applies) expects a payment row with fee -29.43, ship -21.90, net 78.91. No settlement rows exist for this order at all. |
| MLB-080191 | Order settled twice | -2276.41 | Order gross 2602.59 (electronics, classic, heavy) expects one payment row with fee -286.28, ship -39.90, net 2276.41. Instead two IDENTICAL full payment rows (ST-0800221 and ST-0800233) each carrying the full commission and shipping, summing to net 4552.82. This is not a legitimate split (a split's second row would carry no fees), so the entire second row (net 2276.41) is a duplicate payment. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
