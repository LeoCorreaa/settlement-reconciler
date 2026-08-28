# Settlement reconciliation report - case_10

Monthly book of 300 orders / 338 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 8**
- **Owed to the seller (to dispute): R$ 376.94**
- **Received unduly (expect clawback): R$ 625.30**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-100045 | Cancelled order settled | -41.07 | Order MLB-100045 has status 'cancelled', which per rule #6 must carry NO settlement rows. However settlement row ST-1000339 (payment, gross 52.58, fee -11.51, net 41.07) was posted and paid out to the seller. |
| MLB-100060 | Refund amount wrong | 17.43 | Order MLB-100060 is fully refunded (books/premium, gross 74.56, commission 17.43). Per rule #4 the refund row must return the commission: expected refund line gross -74.56, fee +17.43, net -57.13. Observed refund row ST-1000066 has fee 0.00, net -74.56 - the 17.43 commission was never credited back, making the order-level net -17.43 instead of the expected 0.00. |
| MLB-100069 | Wrong shipping deduction | 18.00 | Order MLB-100069 has weight_class 'standard', so expected shipping deduction is -21.90 (expected net 336.81, fee -73.47 matches observed). Observed row ST-1000075 deducted -39.90 (the 'heavy' rate) instead, producing net 318.81, an extra 18.00 shipping charge to the seller. |
| MLB-100150 | Order never settled | 329.42 | Order MLB-100150 is status 'paid' (home/classic, gross 419.68, heavy weight) with expected settlement net 329.42 (fee -50.36, shipping -39.90) per calc_expected, but zero settlement rows exist for this order. |
| MLB-100168 | Commission overcharged | 11.41 | Order MLB-100168 (fashion/premium, gross 406.02) should be charged an 18% commission = 73.08 (calc_expected fee -73.08, net 311.04, shipping -21.90 matches observed). Observed row ST-1000185 charged fee -84.49, 11.41 more than the contractual rate, dropping net to 299.63. |
| MLB-100187 | Commission overcharged | 0.68 | Order MLB-100187 (books/premium, gross 2380.47) should be charged 15% commission = 357.07 (calc_expected fee -357.07, net 2001.50, shipping -21.90 matches observed). Observed row ST-1000205 charged fee -357.75, 0.68 above the contractual rate, giving net 2000.82. |
| MLB-100300 | Refund never debited | -8.37 | Order MLB-100300 is status 'refunded' (fashion/premium, gross 17.83, refund_amount 17.83). Expected settlement is payment net 8.37 plus a refund row (gross -17.83, fee +9.46, net -8.37) netting to 0.00 total. Only the payment row (ST-1000337, net 8.37) exists; no refund row was ever posted, leaving the seller with an unreversed 8.37 credit. |
| MLB-109378 | Settlement for unknown order | -575.86 | Settlement row ST-1000340 (payment, gross 661.91, fee -86.05, net 575.86) references order MLB-109378 which does not exist anywhere in the seller's order book. No order justifies this payment, so the entire net amount is an orphan credit. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
