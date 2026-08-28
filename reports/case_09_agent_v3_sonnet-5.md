# Settlement reconciliation report - case_09

Monthly book of 250 orders / 296 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 9**
- **Owed to the seller (to dispute): R$ 544.49**
- **Received unduly (expect clawback): R$ 3502.36**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-090030 | Refund never debited | -2726.64 | Order fully refunded (gross 3246.00). Only the payment row (net 2686.74) exists; the expected refund row (gross -3246.00, fee +519.36, net -2726.64) is missing from the statement. Expected final net for the order is -39.90 (payment 2686.74 + refund -2726.64) but observed final net is 2686.74. |
| MLB-090036 | Commission overcharged | 51.37 | Home premium order, gross 2303.40, correct commission rate 17% => 391.58. Payment row charged fee -442.95, an overcharge of 51.37 (442.95-391.58). |
| MLB-090087 | Commission overcharged | 62.72 | Home classic order, gross 2272.51, correct commission rate 12% => 272.70. Payment row charged fee -335.42, an overcharge of 62.72 (335.42-272.70). |
| MLB-090090 | Order settled twice | -405.48 | Order gross 521.19 settled twice: two payment rows each with full commission (-93.81) and shipping (-21.90), net 405.48 each, summing to 810.96. A legitimate split would carry fees only on the first row; here both rows carry identical fees/gross, indicating duplication. Expected net 405.48, observed 810.96. |
| MLB-090140 | Commission overcharged | 43.85 | Fashion classic order, gross 1594.57, correct commission rate 13% => 207.29. Payment row charged fee -251.14, an overcharge of 43.85 (251.14-207.29). |
| MLB-090140 | Refund amount wrong | 207.29 | Order fully refunded; refund row should return the commission (fee +207.29 per rules, i.e. 13% of 1594.57) but observed refund row shows fee 0.00, so the commission was never returned to the seller. |
| MLB-090238 | Order never settled | 161.26 | Order status 'paid', gross 229.44 (home, classic, unit 76.48<79 so low-ticket fee applies), expected net 161.26 (229.44 - 46.28 commission/fee - 21.90 shipping). No settlement rows exist for this order at all. |
| MLB-090243 | Wrong shipping deduction | 18.00 | Fashion premium order, weight_class 'standard', gross 2534.22 (>=79). Correct shipping deduction for standard weight is 21.90, but the payment row deducted 39.90 (heavy rate), an overcharge of 18.00. Commission (-456.16) is correct. |
| MLB-099824 | Settlement for unknown order | -370.24 | Settlement row ST-0900298 (net 370.24) references order MLB-099824, which does not exist anywhere in the seller's order book. No corresponding order to justify this payment. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
