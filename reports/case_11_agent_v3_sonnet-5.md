# Settlement reconciliation report - case_11

Monthly book of 350 orders / 396 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 9**
- **Owed to the seller (to dispute): R$ 789.38**
- **Received unduly (expect clawback): R$ 1669.07**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-110089 | Order never settled | 692.04 | Order is 'paid' with expected net 692.04 (gross 811.30, 12% toys classic commission -97.36, standard shipping -21.90) but has zero settlement rows. |
| MLB-110100 | Refund amount wrong | 15.23 | Partial refund of 101.55 (50% of gross 203.09) on a books/premium order (commission 15% = 30.46) should return marketplace_fee of +15.23 (round_half_up(30.46*50%)) per refund row, giving refund net -86.32. The observed refund row ST-1100109 shows marketplace_fee 0.00 and net -101.55, under-crediting the seller by 15.23, which matches the full order net delta of -15.23. |
| MLB-110151 | Commission overcharged | 3.42 | Toys/premium commission should be 17% of gross 203.35 = 34.57, but settled row ST-1100167 charged fee -37.99, an overcharge of 3.42. |
| MLB-110151 | Wrong shipping deduction | 18.00 | Order weight_class is 'standard' so shipping should be 21.90, but settled row ST-1100167 deducted 39.90 (heavy rate), an overcharge of 18.00. Combined with the 3.42 fee overcharge this fully explains the -21.42 net delta for this order. |
| MLB-110166 | Commission overcharged | 42.69 | Electronics/premium commission should be 16% of gross 1581.29 = 253.01 (per calc_expected), but the settled row ST-1100185 charged fee -295.70, an overcharge of 42.69 (shipping -39.90 matches expected, so the full net delta of -42.69 is fee-driven). |
| MLB-110265 | Wrong shipping deduction | 18.00 | Order weight_class is 'standard' so shipping should be 21.90, but settled row ST-1100296 deducted 39.90 (heavy rate); fee -346.58 matches the expected 18% fashion/premium commission exactly, so the entire -18.00 net delta is the shipping overcharge. |
| MLB-110271 | Cancelled order settled | -1249.58 | Order status is 'cancelled' (cancelled before payment per rules, no settlement should exist), but a payment row ST-1100398 was settled with gross 1465.32, fee -175.84, ship -39.90, net 1249.58. Expected net per rules = 0.00. |
| MLB-110328 | Order settled twice | -220.18 | Two identical payment rows (ST-1100368 and ST-1100397) each carry gross 272.00, fee -29.92, ship -21.90, net 220.18 - both rows include full fees, which is not a legitimate split (split settlements only put fees on the first row). Expected net total is 220.18 but observed sum is 440.36. |
| MLB-110334 | Refund never debited | -199.31 | Order is partially_refunded (refund_amount 240.13) with expected lines: payment net 956.65 and refund net -199.31 (gross -240.13, fee +40.82), for expected_net_total 757.34. Only the payment row (net 956.65) was settled; the refund row is entirely missing from the statement. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
