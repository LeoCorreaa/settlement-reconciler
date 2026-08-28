# Settlement reconciliation report - case_03

Monthly book of 50 orders / 56 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 4**
- **Owed to the seller (to dispute): R$ 189.33**
- **Received unduly (expect clawback): R$ 48.13**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-030005 | Commission overcharged | 59.18 | Home/premium heavy-weight order, gross=2006.08, expected commission rate 17% => fee=-341.03, shipping=-39.90, expected net=1625.15. Settlement row ST-0300006 charged fee=-400.21 (net=1565.97), an excess commission of 59.18 versus the contractual rate. Entire net delta of -59.18 is explained by this fee overcharge. |
| MLB-030018 | Commission overcharged | 99.73 | Toys/premium order, gross=5114.31, expected commission rate 17% => fee=-869.43 (net=4222.98 per calc_expected). Settlement row ST-0300021 charged fee=-969.16 (net=4123.25), an excess commission of 99.73 with no other rule (no low-ticket fee applies since unit_price=1704.77>=79). Entire net delta of -99.73 is explained by this fee overcharge. |
| MLB-030022 | Order settled twice | -48.13 | Low-ticket electronics/premium order, gross=64.74, expected single payment row net=48.13 (fee=-16.61 incl. low-ticket fee, no shipping since gross<79). Two identical payment rows were posted (ST-0300026 and ST-0300057), each gross=64.74, fee=-16.61, net=48.13, summing to net=96.26 - double the expected amount. The second row is an unwarranted duplicate of the first. |
| MLB-030048 | Order never settled | 30.42 | Fashion/classic low-ticket order (unit_price=42.15<79), delivered status, expected payment row: fee=-11.73 (13% commission + low-ticket fee), no shipping (gross<79), expected net=30.42. No settlement rows exist at all for this order (0 rows observed), so the seller was never paid. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
