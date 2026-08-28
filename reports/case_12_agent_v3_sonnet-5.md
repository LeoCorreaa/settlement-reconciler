# Settlement reconciliation report - case_12

Monthly book of 400 orders / 460 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 13**
- **Owed to the seller (to dispute): R$ 1491.75**
- **Received unduly (expect clawback): R$ 744.20**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-120018 | Commission overcharged | 0.37 | Order is toys/classic, gross 2031.52, expected commission = 12% = 243.78 (fee -243.78), expected net 1765.84. Observed payment row ST-1200022 charged fee -244.15, net 1765.47 - an overcharge of 0.37 (exceeds the 0.02 rounding tolerance). |
| MLB-120048 | Order settled twice | -59.61 | Order gross 78.41 (electronics premium, low-ticket fee applies) has expected single payment net of 59.61, but the same payment (gross 78.41, fee -18.80, net 59.61) was settled twice via rows ST-1200056 and ST-1200460, summing to net 119.22 instead of 59.61. |
| MLB-120052 | Refund amount wrong | 160.36 | Partial refund of 1233.56 (20% of gross 6167.82) should return commission per rules: expected refund row fee=+160.36 (13% commission * 20%), net=-1073.20. Observed refund row ST-1200062 has fee=0.00, net=-1233.56, i.e. the commission was never returned to the seller. |
| MLB-120103 | Refund never debited | -136.56 | Order status is refunded (full refund of 151.73). Expected settlement includes payment row (net 114.66) AND a refund row (gross -151.73, fee +15.17, net -136.56) for expected total net -21.90. Only the payment row (net 114.66) is present; the refund row was never settled. |
| MLB-120115 | Wrong shipping deduction | 18.00 | Order weight_class is 'standard' so shipping should be 21.90, giving expected net 321.10 (fee -42.39, ship -21.90). Settlement row ST-1200136 deducted -39.90 (heavy rate), yielding net 303.10 - an over-deduction of 18.00. |
| MLB-120125 | Commission overcharged | 1.79 | Order is electronics/classic, gross 106.40, expected commission = 11% = 11.70 (fee -11.70). Observed payment row ST-1200146 charged fee -13.49, an overcharge of 1.79. |
| MLB-120125 | Refund amount wrong | 11.70 | Full refund of gross 106.40 should return commission: expected refund row fee=+11.70, net=-94.70. Observed refund row ST-1200147 has fee=0.00, net=-106.40, so the commission was never returned to the seller. |
| MLB-120185 | Wrong shipping deduction | 18.00 | Order weight_class is 'standard' so shipping should be 21.90, giving expected net 492.43 (fee -76.85, ship -21.90). Settlement row ST-1200219 deducted -39.90 (heavy rate), yielding net 474.43 - an over-deduction of 18.00. |
| MLB-120224 | Cancelled order settled | -153.01 | Order status is cancelled (should have NO settlement rows per rules section 6), but settlement row ST-1200462 exists with gross 217.59, fee -42.68, ship -21.90, net 153.01. |
| MLB-120236 | Commission overcharged | 7.28 | Order is books/classic, gross 343.59, expected commission = 10% = 34.36 (fee -34.36), expected net 287.33. Observed payment row ST-1200277 charged fee -41.64, net 280.05 - an overcharge of 7.28. |
| MLB-120264 | Commission overcharged | 9.58 | Order is toys/classic, gross 630.17, expected commission = 12% = 75.62 (fee -75.62), expected net 532.65. Observed payment row ST-1200308 charged fee -85.20, net 523.07 - an overcharge of 9.58. |
| MLB-120328 | Order never settled | 1264.67 | Order is paid (gross 1482.47, home/classic/heavy) with expected net 1264.67 per calc_expected, but zero settlement rows exist for this order. |
| MLB-129910 | Settlement for unknown order | -395.02 | Settlement row ST-1200461 (gross 454.05, fee -59.03, net 395.02) references order MLB-129910 which does not exist anywhere in the seller's order book. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
