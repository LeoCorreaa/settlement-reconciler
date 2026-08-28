# Settlement reconciliation report - case_12

Monthly book of 400 orders / 460 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 13**
- **Owed to the seller (to dispute): R$ 1491.75**
- **Received unduly (expect clawback): R$ 744.20**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-120018 | Commission overcharged | 0.37 | Toys/classic commission on gross 2031.52 should be 12% = 243.78, giving expected net 1765.84. Settlement row ST-1200022 charged fee -244.15, an overcharge of 0.37 (exceeds the 0.02 rounding tolerance), giving net 1765.47. |
| MLB-120048 | Order settled twice | -59.61 | Expected single payment row: gross 78.41, fee -18.80 (16% commission + 6.25 low-ticket fee), net 59.61. The identical row was settled twice (ST-1200056 and ST-1200460), doubling gross/fee/net to 156.82/-37.60/119.22. |
| MLB-120052 | Refund amount wrong | 160.36 | Partial refund of 20% (1233.56 of 6167.82) should carry fee=+160.36 (20% of the 801.82 commission) per rules, giving refund net -1073.20. Observed refund row ST-1200062 has fee=0.00 and net=-1233.56, so the commission was never returned to the seller. Total order net observed 4110.54 vs expected 4270.90. |
| MLB-120103 | Refund never debited | -136.56 | Order status is 'refunded' (full refund of 151.73). Expected two rows: payment net 114.66 and refund net -136.56, totaling -21.90. Only the payment row (net 114.66) appears on the statement; the refund clawback row is missing entirely. |
| MLB-120115 | Wrong shipping deduction | 18.00 | Order weight_class is 'standard' so shipping should be -21.90, giving expected net 321.10. Settlement row ST-1200136 deducted -39.90 (the 'heavy' rate) instead, giving net 303.10. |
| MLB-120125 | Commission overcharged | 1.79 | Electronics/classic commission on gross 106.40 should be 11% = 11.70. Payment row ST-1200146 charged fee -13.49, an overcharge of 1.79. |
| MLB-120125 | Refund amount wrong | 11.70 | Full refund on this order should return the commission (expected refund fee +11.70, refund net -94.70 per rules). Refund row ST-1200147 shows fee 0.00 and net -106.40, so the commission was never credited back. |
| MLB-120185 | Wrong shipping deduction | 18.00 | Order weight_class is 'standard' so shipping should be -21.90, giving expected net 492.43. Settlement row ST-1200219 deducted -39.90 (the 'heavy' rate) instead, giving net 474.43. |
| MLB-120224 | Cancelled order settled | -153.01 | Order status is 'cancelled' (cancelled before payment), which per rules must have NO settlement rows. Row ST-1200462 nonetheless settled gross 217.59, fee -42.68, ship -21.90, net 153.01. |
| MLB-120236 | Commission overcharged | 7.28 | Books/classic commission on gross 343.59 should be 10% = 34.36, giving expected net 287.33. Settlement row ST-1200277 charged fee -41.64, an overcharge of 7.28, giving net 280.05. |
| MLB-120264 | Commission overcharged | 9.58 | Toys/classic commission on gross 630.17 should be 12% = 75.62, giving expected net 532.65. Settlement row ST-1200308 charged fee -85.20, an overcharge of 9.58, giving net 523.07. |
| MLB-120328 | Order never settled | 1264.67 | Order is 'paid' with expected net 1264.67 (gross 1482.47, commission -177.90 at 12% home/classic, shipping -39.90 heavy) but has zero settlement rows on the statement. |
| MLB-129910 | Settlement for unknown order | -395.02 | Settlement row ST-1200461 (payment, gross 454.05, fee -59.03, net 395.02) references order MLB-129910 which does not exist anywhere in the seller's order book. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
