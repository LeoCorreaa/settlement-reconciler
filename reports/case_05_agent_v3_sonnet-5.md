# Settlement reconciliation report - case_05

Monthly book of 80 orders / 96 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 5**
- **Owed to the seller (to dispute): R$ 734.81**
- **Received unduly (expect clawback): R$ 1352.93**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-050002 | Commission overcharged | 8.70 | Toys/premium order, gross 434.84, correct commission rate is 17% -> expected fee -73.92 (434.84*0.17=73.9228≈73.92), expected net 339.02 (434.84-73.92-21.90 shipping). Observed fee is -82.62 (≈19% of gross, i.e. 434.84*0.19=82.6196), giving observed net 330.32. The extra 8.70 in fees was an overcharge versus the contractual 17% premium/toys rate. |
| MLB-050013 | Refund amount wrong | 11.24 | Fully refunded low-ticket order (fashion/classic, unit 38.40 < 79 -> low-ticket fee applies, commission 11.24). Expected refund row: gross -38.40, fee +11.24 (commission returned), net -27.16. Observed refund row: gross -38.40, fee 0.00, net -38.40 -- the commission was never credited back. Combined with the payment row (net 27.16), expected total net = 0.00 but observed total net = -11.24, a shortfall of 11.24 for the seller. |
| MLB-050016 | Cancelled order settled | -286.85 | Order status is 'cancelled' (books/premium, gross 363.23), which per rule 6 must have NO settlement rows. Instead a payment row was posted: gross 363.23, fee -54.48, ship -21.90, net 286.85. Expected net for a cancelled order is 0.00, so the seller was paid 286.85 it should never have received (and marketplace/seller will need to reverse this). |
| MLB-050058 | Refund never debited | -1066.08 | Order is fully refunded (gross 1211.46, refund 1211.46) but only the original payment row (gross 1211.46, fee -145.38, ship -39.90, net 1026.18) exists on the statement. No refund row (expected gross -1211.46, fee +145.38, net -1066.08) was ever posted. Expected total net = -39.90, observed = 1026.18, a difference of 1066.08 that the seller was overpaid and will need to be clawed back. |
| MLB-050080 | Order never settled | 714.87 | Delivered order (gross 909.36, premium/home/heavy) has zero settlement rows even though the sale was delivered. Expected payment row: gross 909.36, fee -154.59 (17% commission), ship -39.90, net 714.87. Observed net = 0.00, a 714.87 shortfall never paid to the seller. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
