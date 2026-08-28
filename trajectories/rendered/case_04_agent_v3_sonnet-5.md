# Trajectory: case_04 - agent v3

- **Model:** `claude-sonnet-5`
- **Source:** `case_04_agent_v3_sonnet-5.jsonl`

<details><summary><b>System prompt (agent instructions)</b></summary>

```
You are a marketplace settlement reconciliation analyst working for an
online seller. Your job: compare the seller's order book against the payment
processor's settlement statement for one month and find EVERY real divergence,
classify its root cause, and quantify its impact.

Divergence types (use exactly these labels):
- MISSING_SETTLEMENT
- DUPLICATE_SETTLEMENT
- ORPHAN_SETTLEMENT
- FEE_OVERCHARGE
- WRONG_SHIPPING_DEDUCTION
- REFUND_NOT_SETTLED
- REFUND_AMOUNT_MISMATCH
- CANCELLED_BUT_SETTLED

Critical domain knowledge:
- Split settlements are LEGITIMATE: one payment may arrive as two rows, fees
  on the first row. Not a divergence when the sums match.
- A legitimate chargeback is NOT a divergence.
- Net differences of up to 0.02 BRL are rounding noise - never report them.
- impact_brl sign convention: positive = the seller was hurt (received less
  than owed), negative = the seller was unduly favored (will face clawback).
- Every explanation must cite the concrete numbers (expected vs observed).

Report ONLY divergences you can attribute to a concrete rule violation.
Missing a real divergence and inventing a false one are equally bad.
When the reconciliation is complete, call submit_findings exactly once with
ALL findings. If the books are clean, submit an empty list.

Workflow: start with get_fee_rules, get_case_summary, then scan_mismatches.
The scan gives you candidate orders with net deltas - it does NOT tell you the
cause, and it can also be triggered by data the rules allow. For EACH
candidate: get_order, get_order_settlements and calc_expected, determine which
rule was violated, and only then record a finding with the correct type.
An order can carry MORE THAN ONE divergence: always check whether your
explanation accounts for the ENTIRE net delta of the candidate.
After you submit, two deterministic checks run against the rules engine:
each finding must be supported by the data, and each candidate's net delta
must be fully explained by your reported impacts. If either check fails you
will get ONE chance to revise and resubmit.
```
</details>

**Kickoff (user):** Reconcile the seller's monthly book against the settlement statement. Use your tools; when finished, call submit_findings.

### Step 1: `get_fee_rules`

Input:
```json
{}
```

Result:
```json
{
  "fee_rules_markdown": "# Marketplace Settlement Rules\n\nSynthetic ruleset modeled on typical Latin American marketplace terms (Mercado\nLivre style). All amounts in BRL. These rules are the contract between the\nmarketplace and the seller; the settlement statement must follow them exactly.\n\n## 1. Commission\n\n- Each sale pays a commission: `commission = round_half_up(gross_amount * rate)`.\n- The rate depends on `category` and `listing_type` (see `fee_schedule.json`):\n\n| Category    | classic | premium |\n|-------------|---------|---------|\n| electronics | 11%     | 16%     |\n| fashion     | 13%     | 18%     |\n| home        | 12%     | 17%     |\n| toys        | 12%     | 17%     |\n| books       | 10%     | 15%     |\n\n- Low-ticket fixed fee: when `unit_price < 79.00`, add `6.25 * quantity` to the\n  commission.\n- `premium` listings offer interest-free installments to the buyer; that cost\n  is already built into the higher premium rate. The number of installments\n  does NOT change any fee.\n\n## 2. Shipping charged to the seller\n\n- Orders with `gross_amount >= 79.00` ship free for the buyer and the SELLER\n  pays shipping: `21.90` (weight_class `standard`) or `39.90` (`heavy`).\n- Orders with `gross_amount < 79.00`: no shipping is deducted from the seller.\n\n## 3. Sign convention on the settlement statement\n\nEvery settlement row satisfies `net_amount = gross_amount + marketplace_fee +\nshipping_fee`. Fees appear as negative values on payment rows.\n\n- `payment` row: `gross = +G`, `marketplace_fee = -commission`,\n  `shipping_fee = -shipping`, `net = G - commission - shipping`.\n\n## 4. Refunds\n\n- Full refund (`status = refunded`): one `refund` row with `gross = -G`,\n  `marketplace_fee = +commission` (commission is returned to the seller),\n  `shipping_fee = 0` (shipping is NOT returned). `net = -G + commission`.\n- Partial refund of p% (`status = partially_refunded`, see `refund_amount` on\n  the order): `gross = -round_half_up(G * p%)`,\n  `marketplace_fee = +round_half_up(commission * p%)`, `shipping_fee = 0`.\n\n## 5. Chargebacks\n\n- `chargeback` row: `gross = -G`, no commission or shipping returned.\n  A legitimate chargeback is NOT a divergence.\n\n## 6. Cancelled orders\n\n- Orders cancelled before payment (`status = cancelled`) must have NO\n  settlement rows at all.\n\n## 7. Split settlements (IMPORTANT)\n\n- A single order's `payment` MAY legitimately arrive split across two rows\n  (installment funding): the first row carries all the fees, the second row\n  carries the remaining gross with no fees. This is NOT a divergence when the\n  summed values match the expected totals.\n\n## 8. Tolerance\n\n- Net differences of up to `0.02` per order are rounding noise, NOT\n  divergences. Only report a divergence when the absolute impact exceeds 0.02.\n"
}
```

### Step 2: `get_case_summary`

Input:
```json
{}
```

Result:
```json
{
  "orders": {
    "total": 60,
    "by_status": {
      "paid": 26,
      "delivered": 23,
      "cancelled": 3,
      "partially_refunded": 3,
      "refunded": 4,
      "chargeback": 1
    }
  },
  "settlement_rows": {
    "total": 68,
    "by_type": {
      "payment": 60,
      "refund": 7,
      "chargeback": 1
    }
  },
  "order_dates": {
    "first": "2026-07-01",
    "last": "2026-07-28"
  },
  "gross_total": "56964.83",
  "settlement_net_total": "40972.56"
}
```

### Step 3: `scan_mismatches`

Input:
```json
{}
```

Result:
```json
{
  "tolerance_brl": "0.02",
  "candidates": [
    {
      "order_id": "MLB-049648",
      "status": "NOT_IN_ORDER_BOOK",
      "issue": "orphan_rows",
      "expected_net": "0.00",
      "observed_net": "186.31",
      "delta": "186.31",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-040050",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "2485.86",
      "observed_net": "2463.96",
      "delta": "-21.90",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-040060",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "772.69",
      "observed_net": "754.69",
      "delta": "-18.00",
      "rows_observed": 1
    }
  ],
  "note": "Deltas only - causes are NOT determined. Investigate each candidate before reporting."
}
```

### Step 4: `get_order`

Input:
```json
{
  "order_id": "MLB-049648"
}
```

Result:
```json
{
  "error": "order MLB-049648 not found in the seller's book"
}
```

### Step 5: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-049648"
}
```

Result:
```json
{
  "order_id": "MLB-049648",
  "rows": [
    {
      "sid": "ST-0400068",
      "oid": "MLB-049648",
      "date": "2026-07-12",
      "type": "payment",
      "gross": "214.15",
      "fee": "-27.84",
      "ship": "0.00",
      "net": "186.31"
    }
  ],
  "sums": {
    "gross": "214.15",
    "fee": "-27.84",
    "ship": "0.00",
    "net": "186.31"
  }
}
```

### Step 6: `get_order`

Input:
```json
{
  "order_id": "MLB-040050"
}
```

Result:
```json
{
  "id": "MLB-040050",
  "date": "2026-07-20",
  "status": "paid",
  "cat": "home",
  "listing": "premium",
  "weight": "heavy",
  "unit": "1014.36",
  "qty": 3,
  "gross": "3043.08",
  "inst": 3,
  "refund": "0.00"
}
```

### Step 7: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040050"
}
```

Result:
```json
{
  "order_id": "MLB-040050",
  "rows": [
    {
      "sid": "ST-0400057",
      "oid": "MLB-040050",
      "date": "2026-07-23",
      "type": "payment",
      "gross": "3043.08",
      "fee": "-517.32",
      "ship": "-61.80",
      "net": "2463.96"
    }
  ],
  "sums": {
    "gross": "3043.08",
    "fee": "-517.32",
    "ship": "-61.80",
    "net": "2463.96"
  }
}
```

### Step 8: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040050"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040050",
    "date": "2026-07-20",
    "status": "paid",
    "cat": "home",
    "listing": "premium",
    "weight": "heavy",
    "unit": "1014.36",
    "qty": 3,
    "gross": "3043.08",
    "inst": 3,
    "refund": "0.00"
  },
  "commission_rate_pct": 17.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "3043.08",
      "fee": "-517.32",
      "ship": "-39.90",
      "net": "2485.86"
    }
  ],
  "expected_net_total": "2485.86",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 9: `get_order`

Input:
```json
{
  "order_id": "MLB-040060"
}
```

Result:
```json
{
  "id": "MLB-040060",
  "date": "2026-07-07",
  "status": "delivered",
  "cat": "books",
  "listing": "classic",
  "weight": "standard",
  "unit": "441.44",
  "qty": 2,
  "gross": "882.88",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 10: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040060"
}
```

Result:
```json
{
  "order_id": "MLB-040060",
  "rows": [
    {
      "sid": "ST-0400067",
      "oid": "MLB-040060",
      "date": "2026-07-10",
      "type": "payment",
      "gross": "882.88",
      "fee": "-88.29",
      "ship": "-39.90",
      "net": "754.69"
    }
  ],
  "sums": {
    "gross": "882.88",
    "fee": "-88.29",
    "ship": "-39.90",
    "net": "754.69"
  }
}
```

### Step 11: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040060"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040060",
    "date": "2026-07-07",
    "status": "delivered",
    "cat": "books",
    "listing": "classic",
    "weight": "standard",
    "unit": "441.44",
    "qty": 2,
    "gross": "882.88",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 10.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "882.88",
      "fee": "-88.29",
      "ship": "-21.90",
      "net": "772.69"
    }
  ],
  "expected_net_total": "772.69",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 12: `submit_findings`

Input:
```json
{
  "findings": [
    {
      "order_id": "MLB-049648",
      "type": "ORPHAN_SETTLEMENT",
      "explanation": "Settlement row ST-0400068 (gross 214.15, fee -27.84, net 186.31) references order MLB-049648 which does not exist in the seller's order book. No corresponding order to justify this payment.",
      "impact_brl": "-186.31"
    },
    {
      "order_id": "MLB-040050",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order MLB-040050 is weight_class 'heavy', so expected shipping deduction is 39.90 per rules. Settlement row ST-0400057 deducted 61.80 in shipping instead, an overcharge of 21.90 (61.80-39.90). Net observed 2463.96 vs expected 2485.86, delta -21.90 fully explained by the shipping overcharge.",
      "impact_brl": "21.90"
    },
    {
      "order_id": "MLB-040060",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order MLB-040060 is weight_class 'standard', so expected shipping deduction is 21.90 per rules. Settlement row ST-0400067 deducted 39.90 in shipping instead, an overcharge of 18.00 (39.90-21.90). Net observed 754.69 vs expected 772.69, delta -18.00 fully explained by the shipping overcharge.",
      "impact_brl": "18.00"
    }
  ]
}
```

### Deterministic verification: 3 accepted, 0 rejected

Result:
```json
{
  "accepted": true,
  "count": 3
}
```

## Final outcome

- Findings submitted: **3**
- API calls: 4
- Tokens: input=8, output=1,843, cache_read=12,699, cache_write=3,477

Findings:
```json
[
  {
    "order_id": "MLB-049648",
    "type": "ORPHAN_SETTLEMENT",
    "explanation": "Settlement row ST-0400068 (gross 214.15, fee -27.84, net 186.31) references order MLB-049648 which does not exist in the seller's order book. No corresponding order to justify this payment.",
    "impact_brl": "-186.31"
  },
  {
    "order_id": "MLB-040050",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order MLB-040050 is weight_class 'heavy', so expected shipping deduction is 39.90 per rules. Settlement row ST-0400057 deducted 61.80 in shipping instead, an overcharge of 21.90 (61.80-39.90). Net observed 2463.96 vs expected 2485.86, delta -21.90 fully explained by the shipping overcharge.",
    "impact_brl": "21.90"
  },
  {
    "order_id": "MLB-040060",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order MLB-040060 is weight_class 'standard', so expected shipping deduction is 21.90 per rules. Settlement row ST-0400067 deducted 39.90 in shipping instead, an overcharge of 18.00 (39.90-21.90). Net observed 754.69 vs expected 772.69, delta -18.00 fully explained by the shipping overcharge.",
    "impact_brl": "18.00"
  }
]
```
