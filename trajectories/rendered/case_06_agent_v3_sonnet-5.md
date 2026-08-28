# Trajectory: case_06 - agent v3

- **Model:** `claude-sonnet-5`
- **Source:** `case_06_agent_v3_sonnet-5.jsonl`

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
    "total": 120,
    "by_status": {
      "delivered": 53,
      "paid": 46,
      "cancelled": 6,
      "chargeback": 1,
      "partially_refunded": 6,
      "refunded": 8
    }
  },
  "settlement_rows": {
    "total": 144,
    "by_type": {
      "payment": 129,
      "refund": 14,
      "chargeback": 1
    }
  },
  "order_dates": {
    "first": "2026-07-01",
    "last": "2026-07-28"
  },
  "gross_total": "141551.65",
  "settlement_net_total": "92710.78"
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
      "order_id": "MLB-060034",
      "status": "partially_refunded",
      "issue": "net_delta",
      "expected_net": "608.71",
      "observed_net": "423.39",
      "delta": "-185.32",
      "rows_observed": 2
    },
    {
      "order_id": "MLB-060087",
      "status": "paid",
      "issue": "no_rows",
      "expected_net": "172.10",
      "observed_net": "0.00",
      "delta": "-172.10",
      "rows_observed": 0
    },
    {
      "order_id": "MLB-060091",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "47.96",
      "observed_net": "95.92",
      "delta": "47.96",
      "rows_observed": 2
    },
    {
      "order_id": "MLB-060070",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "82.51",
      "observed_net": "62.05",
      "delta": "-20.46",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-060094",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "249.76",
      "observed_net": "231.76",
      "delta": "-18.00",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-060038",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "50.52",
      "observed_net": "48.59",
      "delta": "-1.93",
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
  "order_id": "MLB-060034"
}
```

Result:
```json
{
  "id": "MLB-060034",
  "date": "2026-07-01",
  "status": "partially_refunded",
  "cat": "electronics",
  "listing": "premium",
  "weight": "heavy",
  "unit": "643.47",
  "qty": 3,
  "gross": "1930.41",
  "inst": 3,
  "refund": "1158.25"
}
```

### Step 5: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-060034"
}
```

Result:
```json
{
  "order_id": "MLB-060034",
  "rows": [
    {
      "sid": "ST-0600038",
      "oid": "MLB-060034",
      "date": "2026-07-04",
      "type": "payment",
      "gross": "1930.41",
      "fee": "-308.87",
      "ship": "-39.90",
      "net": "1581.64"
    },
    {
      "sid": "ST-0600039",
      "oid": "MLB-060034",
      "date": "2026-07-11",
      "type": "refund",
      "gross": "-1158.25",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-1158.25"
    }
  ],
  "sums": {
    "gross": "772.16",
    "fee": "-308.87",
    "ship": "-39.90",
    "net": "423.39"
  }
}
```

### Step 6: `calc_expected`

Input:
```json
{
  "order_id": "MLB-060034"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-060034",
    "date": "2026-07-01",
    "status": "partially_refunded",
    "cat": "electronics",
    "listing": "premium",
    "weight": "heavy",
    "unit": "643.47",
    "qty": 3,
    "gross": "1930.41",
    "inst": 3,
    "refund": "1158.25"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "1930.41",
      "fee": "-308.87",
      "ship": "-39.90",
      "net": "1581.64"
    },
    {
      "type": "refund",
      "gross": "-1158.25",
      "fee": "185.32",
      "ship": "0.00",
      "net": "-972.93"
    }
  ],
  "expected_net_total": "608.71",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 7: `get_order`

Input:
```json
{
  "order_id": "MLB-060087"
}
```

Result:
```json
{
  "id": "MLB-060087",
  "date": "2026-07-26",
  "status": "paid",
  "cat": "fashion",
  "listing": "premium",
  "weight": "standard",
  "unit": "236.59",
  "qty": 1,
  "gross": "236.59",
  "inst": 10,
  "refund": "0.00"
}
```

### Step 8: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-060087"
}
```

Result:
```json
{
  "order_id": "MLB-060087",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 9: `calc_expected`

Input:
```json
{
  "order_id": "MLB-060087"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-060087",
    "date": "2026-07-26",
    "status": "paid",
    "cat": "fashion",
    "listing": "premium",
    "weight": "standard",
    "unit": "236.59",
    "qty": 1,
    "gross": "236.59",
    "inst": 10,
    "refund": "0.00"
  },
  "commission_rate_pct": 18.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "236.59",
      "fee": "-42.59",
      "ship": "-21.90",
      "net": "172.10"
    }
  ],
  "expected_net_total": "172.10",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 10: `get_order`

Input:
```json
{
  "order_id": "MLB-060091"
}
```

Result:
```json
{
  "id": "MLB-060091",
  "date": "2026-07-28",
  "status": "paid",
  "cat": "books",
  "listing": "classic",
  "weight": "standard",
  "unit": "33.59",
  "qty": 2,
  "gross": "67.18",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 11: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-060091"
}
```

Result:
```json
{
  "order_id": "MLB-060091",
  "rows": [
    {
      "sid": "ST-0600112",
      "oid": "MLB-060091",
      "date": "2026-07-31",
      "type": "payment",
      "gross": "67.18",
      "fee": "-19.22",
      "ship": "0.00",
      "net": "47.96"
    },
    {
      "sid": "ST-0600145",
      "oid": "MLB-060091",
      "date": "2026-08-01",
      "type": "payment",
      "gross": "67.18",
      "fee": "-19.22",
      "ship": "0.00",
      "net": "47.96"
    }
  ],
  "sums": {
    "gross": "134.36",
    "fee": "-38.44",
    "ship": "0.00",
    "net": "95.92"
  }
}
```

### Step 12: `calc_expected`

Input:
```json
{
  "order_id": "MLB-060091"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-060091",
    "date": "2026-07-28",
    "status": "paid",
    "cat": "books",
    "listing": "classic",
    "weight": "standard",
    "unit": "33.59",
    "qty": 2,
    "gross": "67.18",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 10.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "67.18",
      "fee": "-19.22",
      "ship": "0.00",
      "net": "47.96"
    }
  ],
  "expected_net_total": "47.96",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 13: `get_order`

Input:
```json
{
  "order_id": "MLB-060070"
}
```

Result:
```json
{
  "id": "MLB-060070",
  "date": "2026-07-01",
  "status": "delivered",
  "cat": "electronics",
  "listing": "classic",
  "weight": "standard",
  "unit": "65.68",
  "qty": 2,
  "gross": "131.36",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 14: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-060070"
}
```

Result:
```json
{
  "order_id": "MLB-060070",
  "rows": [
    {
      "sid": "ST-0600083",
      "oid": "MLB-060070",
      "date": "2026-07-04",
      "type": "payment",
      "gross": "131.36",
      "fee": "-29.41",
      "ship": "-39.90",
      "net": "62.05"
    }
  ],
  "sums": {
    "gross": "131.36",
    "fee": "-29.41",
    "ship": "-39.90",
    "net": "62.05"
  }
}
```

### Step 15: `calc_expected`

Input:
```json
{
  "order_id": "MLB-060070"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-060070",
    "date": "2026-07-01",
    "status": "delivered",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "65.68",
    "qty": 2,
    "gross": "131.36",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "131.36",
      "fee": "-26.95",
      "ship": "-21.90",
      "net": "82.51"
    }
  ],
  "expected_net_total": "82.51",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 16: `get_order`

Input:
```json
{
  "order_id": "MLB-060094"
}
```

Result:
```json
{
  "id": "MLB-060094",
  "date": "2026-07-04",
  "status": "delivered",
  "cat": "toys",
  "listing": "classic",
  "weight": "standard",
  "unit": "308.70",
  "qty": 1,
  "gross": "308.70",
  "inst": 3,
  "refund": "0.00"
}
```

### Step 17: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-060094"
}
```

Result:
```json
{
  "order_id": "MLB-060094",
  "rows": [
    {
      "sid": "ST-0600114",
      "oid": "MLB-060094",
      "date": "2026-07-07",
      "type": "payment",
      "gross": "308.70",
      "fee": "-37.04",
      "ship": "-39.90",
      "net": "231.76"
    }
  ],
  "sums": {
    "gross": "308.70",
    "fee": "-37.04",
    "ship": "-39.90",
    "net": "231.76"
  }
}
```

### Step 18: `calc_expected`

Input:
```json
{
  "order_id": "MLB-060094"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-060094",
    "date": "2026-07-04",
    "status": "delivered",
    "cat": "toys",
    "listing": "classic",
    "weight": "standard",
    "unit": "308.70",
    "qty": 1,
    "gross": "308.70",
    "inst": 3,
    "refund": "0.00"
  },
  "commission_rate_pct": 12.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "308.70",
      "fee": "-37.04",
      "ship": "-21.90",
      "net": "249.76"
    }
  ],
  "expected_net_total": "249.76",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 19: `get_order`

Input:
```json
{
  "order_id": "MLB-060038"
}
```

Result:
```json
{
  "id": "MLB-060038",
  "date": "2026-07-06",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "36.18",
  "qty": 3,
  "gross": "108.54",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 20: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-060038"
}
```

Result:
```json
{
  "order_id": "MLB-060038",
  "rows": [
    {
      "sid": "ST-0600042",
      "oid": "MLB-060038",
      "date": "2026-07-09",
      "type": "payment",
      "gross": "108.54",
      "fee": "-38.05",
      "ship": "-21.90",
      "net": "48.59"
    }
  ],
  "sums": {
    "gross": "108.54",
    "fee": "-38.05",
    "ship": "-21.90",
    "net": "48.59"
  }
}
```

### Step 21: `calc_expected`

Input:
```json
{
  "order_id": "MLB-060038"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-060038",
    "date": "2026-07-06",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "36.18",
    "qty": 3,
    "gross": "108.54",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "108.54",
      "fee": "-36.12",
      "ship": "-21.90",
      "net": "50.52"
    }
  ],
  "expected_net_total": "50.52",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 22: `list_orders`

Input:
```json
{
  "status": "cancelled"
}
```

Result:
```json
{
  "total_matching": 6,
  "offset": 0,
  "returned": 6,
  "has_more": false,
  "orders": [
    {
      "id": "MLB-060008",
      "date": "2026-07-25",
      "status": "cancelled",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "48.25",
      "qty": 1,
      "gross": "48.25",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-060014",
      "date": "2026-07-17",
      "status": "cancelled",
      "cat": "toys",
      "listing": "classic",
      "weight": "standard",
      "unit": "304.17",
      "qty": 1,
      "gross": "304.17",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-060028",
      "date": "2026-07-11",
      "status": "cancelled",
      "cat": "electronics",
      "listing": "premium",
      "weight": "heavy",
      "unit": "2028.37",
      "qty": 1,
      "gross": "2028.37",
      "inst": 10,
      "refund": "0.00"
    },
    {
      "id": "MLB-060031",
      "date": "2026-07-17",
      "status": "cancelled",
      "cat": "toys",
      "listing": "classic",
      "weight": "standard",
      "unit": "233.41",
      "qty": 1,
      "gross": "233.41",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-060035",
      "date": "2026-07-17",
      "status": "cancelled",
      "cat": "electronics",
      "listing": "classic",
      "weight": "heavy",
      "unit": "2022.43",
      "qty": 1,
      "gross": "2022.43",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-060093",
      "date": "2026-07-26",
      "status": "cancelled",
      "cat": "home",
      "listing": "classic",
      "weight": "heavy",
      "unit": "1612.03",
      "qty": 2,
      "gross": "3224.06",
      "inst": 1,
      "refund": "0.00"
    }
  ]
}
```

### Step 23: `list_orders`

Input:
```json
{
  "status": "chargeback"
}
```

Result:
```json
{
  "total_matching": 1,
  "offset": 0,
  "returned": 1,
  "has_more": false,
  "orders": [
    {
      "id": "MLB-060013",
      "date": "2026-07-05",
      "status": "chargeback",
      "cat": "books",
      "listing": "classic",
      "weight": "standard",
      "unit": "2108.54",
      "qty": 2,
      "gross": "4217.08",
      "inst": 1,
      "refund": "0.00"
    }
  ]
}
```

### Step 24: `submit_findings`

Input:
```json
{
  "findings": [
    {
      "order_id": "MLB-060034",
      "type": "REFUND_AMOUNT_MISMATCH",
      "explanation": "Partial refund of 1158.25 on a 1930.41 gross premium electronics order (60% refund). Per rules, marketplace_fee on the refund row should return round_half_up(commission*60%) = round_half_up(308.87*0.6) = 185.32, giving expected refund net of -972.93. Observed refund row has fee=0.00 and net=-1158.25, i.e. the commission refund was never credited back to the seller.",
      "impact_brl": "185.32"
    },
    {
      "order_id": "MLB-060087",
      "type": "MISSING_SETTLEMENT",
      "explanation": "Order is 'paid' (fashion premium, gross 236.59) with expected settlement net of 172.10 (fee -42.59, shipping -21.90), but there are zero settlement rows for this order on the statement.",
      "impact_brl": "172.10"
    },
    {
      "order_id": "MLB-060091",
      "type": "DUPLICATE_SETTLEMENT",
      "explanation": "Books/classic order with gross 67.18 should settle once for net 47.96 (fee -19.22, low-ticket fee included). Instead two identical payment rows (ST-0600112 and ST-0600145) each carrying the full gross 67.18 and fee -19.22 were posted, doubling net to 95.92. This is not a legitimate split (a split's second row would carry no fees), it is a duplicate of the same payment.",
      "impact_brl": "-47.96"
    },
    {
      "order_id": "MLB-060070",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order MLB-060070 has weight_class 'standard' and gross 131.36 (>=79 threshold), so shipping should be the standard rate of 21.90. The settlement instead deducted the heavy rate of 39.90, an excess deduction of 18.00.",
      "impact_brl": "18.00"
    },
    {
      "order_id": "MLB-060070",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics/classic order, unit_price 65.68<79 so low-ticket fee of 6.25*2=12.50 applies; commission = round_half_up(131.36*0.11)=14.45, total expected fee -26.95. Observed marketplace_fee is -29.41, an overcharge of 2.46 beyond the contractual commission/low-ticket fee.",
      "impact_brl": "2.46"
    },
    {
      "order_id": "MLB-060094",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Toys/classic order, weight_class 'standard', gross 308.70 (>=79), so shipping should be the standard 21.90 rate. Settlement instead deducted the heavy rate of 39.90, an excess of 18.00; the commission fee of -37.04 matches expectations exactly, isolating the entire -18.00 net delta to the shipping rate error.",
      "impact_brl": "18.00"
    },
    {
      "order_id": "MLB-060038",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics/premium order, unit_price 36.18<79, qty 3, low-ticket fee 6.25*3=18.75; commission = round_half_up(108.54*0.16)=17.37, total expected fee -36.12 (shipping -21.90 matches observed). Observed marketplace_fee is -38.05, an overcharge of 1.93 versus the contractual fee, which fully explains the -1.93 net delta.",
      "impact_brl": "1.93"

... (truncated for readability; full data in the .jsonl)
```

### Deterministic verification: 7 accepted, 0 rejected

Result:
```json
{
  "accepted": true,
  "count": 7
}
```

## Final outcome

- Findings submitted: **7**
- API calls: 5
- Tokens: input=10, output=8,028, cache_read=21,428, cache_write=11,488

Findings:
```json
[
  {
    "order_id": "MLB-060034",
    "type": "REFUND_AMOUNT_MISMATCH",
    "explanation": "Partial refund of 1158.25 on a 1930.41 gross premium electronics order (60% refund). Per rules, marketplace_fee on the refund row should return round_half_up(commission*60%) = round_half_up(308.87*0.6) = 185.32, giving expected refund net of -972.93. Observed refund row has fee=0.00 and net=-1158.25, i.e. the commission refund was never credited back to the seller.",
    "impact_brl": "185.32"
  },
  {
    "order_id": "MLB-060087",
    "type": "MISSING_SETTLEMENT",
    "explanation": "Order is 'paid' (fashion premium, gross 236.59) with expected settlement net of 172.10 (fee -42.59, shipping -21.90), but there are zero settlement rows for this order on the statement.",
    "impact_brl": "172.10"
  },
  {
    "order_id": "MLB-060091",
    "type": "DUPLICATE_SETTLEMENT",
    "explanation": "Books/classic order with gross 67.18 should settle once for net 47.96 (fee -19.22, low-ticket fee included). Instead two identical payment rows (ST-0600112 and ST-0600145) each carrying the full gross 67.18 and fee -19.22 were posted, doubling net to 95.92. This is not a legitimate split (a split's second row would carry no fees), it is a duplicate of the same payment.",
    "impact_brl": "-47.96"
  },
  {
    "order_id": "MLB-060070",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order MLB-060070 has weight_class 'standard' and gross 131.36 (>=79 threshold), so shipping should be the standard rate of 21.90. The settlement instead deducted the heavy rate of 39.90, an excess deduction of 18.00.",
    "impact_brl": "18.00"
  },
  {
    "order_id": "MLB-060070",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics/classic order, unit_price 65.68<79 so low-ticket fee of 6.25*2=12.50 applies; commission = round_half_up(131.36*0.11)=14.45, total expected fee -26.95. Observed marketplace_fee is -29.41, an overcharge of 2.46 beyond the contractual commission/low-ticket fee.",
    "impact_brl": "2.46"
  },
  {
    "order_id": "MLB-060094",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Toys/classic order, weight_class 'standard', gross 308.70 (>=79), so shipping should be the standard 21.90 rate. Settlement instead deducted the heavy rate of 39.90, an excess of 18.00; the commission fee of -37.04 matches expectations exactly, isolating the entire -18.00 net delta to the shipping rate error.",
    "impact_brl": "18.00"
  },
  {
    "order_id": "MLB-060038",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics/premium order, unit_price 36.18<79, qty 3, low-ticket fee 6.25*3=18.75; commission = round_half_up(108.54*0.16)=17.37, total expected fee -36.12 (shipping -21.90 matches observed). Observed marketplace_fee is -38.05, an overcharge of 1.93 versus the contractual fee, which fully explains the -1.93 net delta.",
    "impact_brl": "1.93"
  }
]
```
