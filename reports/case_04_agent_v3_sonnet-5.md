# Settlement reconciliation report - case_04

Monthly book of 60 orders / 68 settlement rows, reconciled automatically by the settlement-reconciler agent (model `claude-sonnet-5`).

## Executive summary

- **Divergences found: 3**
- **Owed to the seller (to dispute): R$ 39.90**
- **Received unduly (expect clawback): R$ 186.31**

## Divergences

| Order | Issue | Impact (R$) | Evidence |
|---|---|---:|---|
| MLB-040050 | Wrong shipping deduction | 21.90 | Order MLB-040050 is weight_class 'heavy', so expected shipping deduction is 39.90 per rules. Settlement row ST-0400057 deducted 61.80 in shipping instead, an overcharge of 21.90 (61.80-39.90). Net observed 2463.96 vs expected 2485.86, delta -21.90 fully explained by the shipping overcharge. |
| MLB-040060 | Wrong shipping deduction | 18.00 | Order MLB-040060 is weight_class 'standard', so expected shipping deduction is 21.90 per rules. Settlement row ST-0400067 deducted 39.90 in shipping instead, an overcharge of 18.00 (39.90-21.90). Net observed 754.69 vs expected 772.69, delta -18.00 fully explained by the shipping overcharge. |
| MLB-049648 | Settlement for unknown order | -186.31 | Settlement row ST-0400068 (gross 214.15, fee -27.84, net 186.31) references order MLB-049648 which does not exist in the seller's order book. No corresponding order to justify this payment. |

## Recommended next step

Review each divergence above against the marketplace panel, then open a dispute for the items marked as owed to the seller. This report is evidence, not an action: no dispute is filed without human approval.
