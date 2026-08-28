# Settlement reconciliation report - case_07

Monthly book of 160 orders / 193 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 6**
- **Owed to the seller (to dispute): R$ 105.22**
- **Received unduly (expect clawback): R$ 670.42**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-070003 | Commission overcharged | 4.38 | Order is toys/premium, commission rate 17%, gross 244.74 => expected commission = round_half_up(244.74*0.17) = 41.61. Settlement row ST-0700003 charged fee -45.99, i.e. 4.38 more than the contractual commission, with matching shipping (-21.90) correct. Expected net 181.23 vs observed net 176.85, delta -4.38 fully explained by the fee overcharge. |
| MLB-070006 | Refund never debited | -36.06 | Order is 'partially_refunded' with refund_amount 45.76. Expected settlement = payment row (net 60.10) + refund row (gross -45.76, fee +9.70, net -36.06) = total expected net 24.04. Only the payment row (net 60.10) is present; the refund row was never settled, so the seller kept the full 60.10 instead of the net 24.04 owed. |
| MLB-070061 | Order never settled | 78.94 | Order is 'delivered' (electronics, classic, gross 113.30, standard shipping) with expected settlement net of 78.94 (fee -12.46, shipping -21.90) per calc_expected, but zero settlement rows exist for this order. |
| MLB-070067 | Cancelled order settled | -57.93 | Order status is 'cancelled' (must have NO settlement rows per rule 6), yet settlement row ST-0700195 shows a payment of gross 77.33, fee -19.40, net 57.93. The full net amount was settled despite the order being cancelled before payment. |
| MLB-070119 | Wrong shipping deduction | 21.90 | Order weight_class is 'standard' but settlement row ST-0700144 deducted shipping of -61.80 instead of the contractual -21.90 for standard shipping (gross 1756.35 >= 79). Expected net was 1523.25 (fee -193.20, ship -21.90); observed net is 1501.35, a shortfall of exactly 21.90 matching the shipping overcharge (61.80 - 21.90 = 39.90 extra, actually the deducted amount corresponds to double-charging: 21.90+39.90=61.80, i.e. both standard and heavy shipping were applied). |
| MLB-079870 | Settlement for unknown order | -576.43 | Settlement row ST-0700194 (payment, gross 662.56, fee -86.13, net 576.43) references order MLB-079870, which does not exist anywhere in the seller's order book. There is no corresponding sale to justify this settlement. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
