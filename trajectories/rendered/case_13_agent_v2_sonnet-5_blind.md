# Trajectory: case_13 - agent v2

- **Model:** `claude-sonnet-5`
- **Source:** `case_13_agent_v2_sonnet-5_blind.jsonl`

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
If a get_notices tool is available, read it BEFORE concluding anything:
month-specific notices can change the effective rules for specific orders,
while the rules document and every calculator tool always reflect the
STANDARD contract only.
When the reconciliation is complete, call submit_findings exactly once with
ALL findings. If the books are clean, submit an empty list.

Workflow: start with get_fee_rules, get_case_summary, then scan_mismatches.
The scan gives you candidate orders with net deltas - it does NOT tell you the
cause, and it can also be triggered by data the rules allow. For EACH
candidate: get_order, get_order_settlements and calc_expected, determine which
rule was violated, and only then record a finding with the correct type.
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
    "total": 150,
    "by_status": {
      "delivered": 65,
      "paid": 60,
      "cancelled": 7,
      "refunded": 10,
      "partially_refunded": 7,
      "chargeback": 1
    }
  },
  "settlement_rows": {
    "total": 161,
    "by_type": {
      "payment": 143,
      "refund": 17,
      "chargeback": 1
    }
  },
  "order_dates": {
    "first": "2026-07-01",
    "last": "2026-07-28"
  },
  "gross_total": "192609.57",
  "settlement_net_total": "135611.81"
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
      "order_id": "MLB-130009",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "5639.80",
      "observed_net": "5775.03",
      "delta": "135.23",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130083",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "5335.32",
      "observed_net": "5456.11",
      "delta": "120.79",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130014",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "3277.60",
      "observed_net": "3356.58",
      "delta": "78.98",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130115",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "3073.12",
      "observed_net": "3143.08",
      "delta": "69.96",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130010",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "2712.42",
      "observed_net": "2774.27",
      "delta": "61.85",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130107",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "781.02",
      "observed_net": "800.14",
      "delta": "19.12",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130013",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "625.55",
      "observed_net": "641.39",
      "delta": "15.84",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130132",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "476.00",
      "observed_net": "487.19",
      "delta": "11.19",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130004",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "341.96",
      "observed_net": "351.05",
      "delta": "9.09",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130006",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "280.71",
      "observed_net": "287.91",
      "delta": "7.20",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130002",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "273.44",
      "observed_net": "280.47",
      "delta": "7.03",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130001",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "137.77",
      "observed_net": "141.57",
      "delta": "3.80",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130007",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "95.35",
      "observed_net": "98.14",
      "delta": "2.79",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130011",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "54.24",
      "observed_net": "56.35",
      "delta": "2.11",
      "rows_o
... (truncated for readability; full data in the .jsonl)
```

### Step 4: `get_order`

Input:
```json
{
  "order_id": "MLB-130009"
}
```

Result:
```json
{
  "id": "MLB-130009",
  "date": "2026-07-14",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "heavy",
  "unit": "2253.85",
  "qty": 3,
  "gross": "6761.55",
  "inst": 12,
  "refund": "0.00"
}
```

### Step 5: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130009"
}
```

Result:
```json
{
  "order_id": "MLB-130009",
  "rows": [
    {
      "sid": "ST-1300009",
      "oid": "MLB-130009",
      "date": "2026-07-17",
      "type": "payment",
      "gross": "6761.55",
      "fee": "-946.62",
      "ship": "-39.90",
      "net": "5775.03"
    }
  ],
  "sums": {
    "gross": "6761.55",
    "fee": "-946.62",
    "ship": "-39.90",
    "net": "5775.03"
  }
}
```

### Step 6: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130009"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130009",
    "date": "2026-07-14",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "heavy",
    "unit": "2253.85",
    "qty": 3,
    "gross": "6761.55",
    "inst": 12,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "6761.55",
      "fee": "-1081.85",
      "ship": "-39.90",
      "net": "5639.80"
    }
  ],
  "expected_net_total": "5639.80",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 7: `get_order`

Input:
```json
{
  "order_id": "MLB-130083"
}
```

Result:
```json
{
  "id": "MLB-130083",
  "date": "2026-07-14",
  "status": "paid",
  "cat": "electronics",
  "listing": "classic",
  "weight": "heavy",
  "unit": "2013.19",
  "qty": 3,
  "gross": "6039.57",
  "inst": 3,
  "refund": "0.00"
}
```

### Step 8: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130083"
}
```

Result:
```json
{
  "order_id": "MLB-130083",
  "rows": [
    {
      "sid": "ST-1300089",
      "oid": "MLB-130083",
      "date": "2026-07-17",
      "type": "payment",
      "gross": "6039.57",
      "fee": "-543.56",
      "ship": "-39.90",
      "net": "5456.11"
    }
  ],
  "sums": {
    "gross": "6039.57",
    "fee": "-543.56",
    "ship": "-39.90",
    "net": "5456.11"
  }
}
```

### Step 9: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130083"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130083",
    "date": "2026-07-14",
    "status": "paid",
    "cat": "electronics",
    "listing": "classic",
    "weight": "heavy",
    "unit": "2013.19",
    "qty": 3,
    "gross": "6039.57",
    "inst": 3,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "6039.57",
      "fee": "-664.35",
      "ship": "-39.90",
      "net": "5335.32"
    }
  ],
  "expected_net_total": "5335.32",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 10: `get_order`

Input:
```json
{
  "order_id": "MLB-130014"
}
```

Result:
```json
{
  "id": "MLB-130014",
  "date": "2026-07-08",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "heavy",
  "unit": "1974.70",
  "qty": 2,
  "gross": "3949.40",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 11: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130014"
}
```

Result:
```json
{
  "order_id": "MLB-130014",
  "rows": [
    {
      "sid": "ST-1300014",
      "oid": "MLB-130014",
      "date": "2026-07-11",
      "type": "payment",
      "gross": "3949.40",
      "fee": "-552.92",
      "ship": "-39.90",
      "net": "3356.58"
    }
  ],
  "sums": {
    "gross": "3949.40",
    "fee": "-552.92",
    "ship": "-39.90",
    "net": "3356.58"
  }
}
```

### Step 12: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130014"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130014",
    "date": "2026-07-08",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "heavy",
    "unit": "1974.70",
    "qty": 2,
    "gross": "3949.40",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "3949.40",
      "fee": "-631.90",
      "ship": "-39.90",
      "net": "3277.60"
    }
  ],
  "expected_net_total": "3277.60",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 13: `get_order`

Input:
```json
{
  "order_id": "MLB-130115"
}
```

Result:
```json
{
  "id": "MLB-130115",
  "date": "2026-07-18",
  "status": "delivered",
  "cat": "electronics",
  "listing": "classic",
  "weight": "heavy",
  "unit": "1748.89",
  "qty": 2,
  "gross": "3497.78",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 14: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130115"
}
```

Result:
```json
{
  "order_id": "MLB-130115",
  "rows": [
    {
      "sid": "ST-1300126",
      "oid": "MLB-130115",
      "date": "2026-07-21",
      "type": "payment",
      "gross": "3497.78",
      "fee": "-314.80",
      "ship": "-39.90",
      "net": "3143.08"
    }
  ],
  "sums": {
    "gross": "3497.78",
    "fee": "-314.80",
    "ship": "-39.90",
    "net": "3143.08"
  }
}
```

### Step 15: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130115"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130115",
    "date": "2026-07-18",
    "status": "delivered",
    "cat": "electronics",
    "listing": "classic",
    "weight": "heavy",
    "unit": "1748.89",
    "qty": 2,
    "gross": "3497.78",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "3497.78",
      "fee": "-384.76",
      "ship": "-39.90",
      "net": "3073.12"
    }
  ],
  "expected_net_total": "3073.12",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 16: `get_order`

Input:
```json
{
  "order_id": "MLB-130010"
}
```

Result:
```json
{
  "id": "MLB-130010",
  "date": "2026-07-15",
  "status": "paid",
  "cat": "electronics",
  "listing": "classic",
  "weight": "heavy",
  "unit": "1030.83",
  "qty": 3,
  "gross": "3092.49",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 17: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130010"
}
```

Result:
```json
{
  "order_id": "MLB-130010",
  "rows": [
    {
      "sid": "ST-1300010",
      "oid": "MLB-130010",
      "date": "2026-07-18",
      "type": "payment",
      "gross": "3092.49",
      "fee": "-278.32",
      "ship": "-39.90",
      "net": "2774.27"
    }
  ],
  "sums": {
    "gross": "3092.49",
    "fee": "-278.32",
    "ship": "-39.90",
    "net": "2774.27"
  }
}
```

### Step 18: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130010"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130010",
    "date": "2026-07-15",
    "status": "paid",
    "cat": "electronics",
    "listing": "classic",
    "weight": "heavy",
    "unit": "1030.83",
    "qty": 3,
    "gross": "3092.49",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "3092.49",
      "fee": "-340.17",
      "ship": "-39.90",
      "net": "2712.42"
    }
  ],
  "expected_net_total": "2712.42",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 19: `get_order`

Input:
```json
{
  "order_id": "MLB-130107"
}
```

Result:
```json
{
  "id": "MLB-130107",
  "date": "2026-07-18",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "318.62",
  "qty": 3,
  "gross": "955.86",
  "inst": 10,
  "refund": "0.00"
}
```

### Step 20: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130107"
}
```

Result:
```json
{
  "order_id": "MLB-130107",
  "rows": [
    {
      "sid": "ST-1300117",
      "oid": "MLB-130107",
      "date": "2026-07-21",
      "type": "payment",
      "gross": "955.86",
      "fee": "-133.82",
      "ship": "-21.90",
      "net": "800.14"
    }
  ],
  "sums": {
    "gross": "955.86",
    "fee": "-133.82",
    "ship": "-21.90",
    "net": "800.14"
  }
}
```

### Step 21: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130107"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130107",
    "date": "2026-07-18",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "318.62",
    "qty": 3,
    "gross": "955.86",
    "inst": 10,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "955.86",
      "fee": "-152.94",
      "ship": "-21.90",
      "net": "781.02"
    }
  ],
  "expected_net_total": "781.02",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 22: `get_order`

Input:
```json
{
  "order_id": "MLB-130013"
}
```

Result:
```json
{
  "id": "MLB-130013",
  "date": "2026-07-18",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "heavy",
  "unit": "792.20",
  "qty": 1,
  "gross": "792.20",
  "inst": 10,
  "refund": "0.00"
}
```

### Step 23: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130013"
}
```

Result:
```json
{
  "order_id": "MLB-130013",
  "rows": [
    {
      "sid": "ST-1300013",
      "oid": "MLB-130013",
      "date": "2026-07-21",
      "type": "payment",
      "gross": "792.20",
      "fee": "-110.91",
      "ship": "-39.90",
      "net": "641.39"
    }
  ],
  "sums": {
    "gross": "792.20",
    "fee": "-110.91",
    "ship": "-39.90",
    "net": "641.39"
  }
}
```

### Step 24: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130013"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130013",
    "date": "2026-07-18",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "heavy",
    "unit": "792.20",
    "qty": 1,
    "gross": "792.20",
    "inst": 10,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "792.20",
      "fee": "-126.75",
      "ship": "-39.90",
      "net": "625.55"
    }
  ],
  "expected_net_total": "625.55",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 25: `get_order`

Input:
```json
{
  "order_id": "MLB-130132"
}
```

Result:
```json
{
  "id": "MLB-130132",
  "date": "2026-07-08",
  "status": "delivered",
  "cat": "electronics",
  "listing": "classic",
  "weight": "standard",
  "unit": "279.72",
  "qty": 2,
  "gross": "559.44",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 26: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130132"
}
```

Result:
```json
{
  "order_id": "MLB-130132",
  "rows": [
    {
      "sid": "ST-1300141",
      "oid": "MLB-130132",
      "date": "2026-07-11",
      "type": "payment",
      "gross": "559.44",
      "fee": "-50.35",
      "ship": "-21.90",
      "net": "487.19"
    }
  ],
  "sums": {
    "gross": "559.44",
    "fee": "-50.35",
    "ship": "-21.90",
    "net": "487.19"
  }
}
```

### Step 27: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130132"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130132",
    "date": "2026-07-08",
    "status": "delivered",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "279.72",
    "qty": 2,
    "gross": "559.44",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "559.44",
      "fee": "-61.54",
      "ship": "-21.90",
      "net": "476.00"
    }
  ],
  "expected_net_total": "476.00",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 28: `get_order`

Input:
```json
{
  "order_id": "MLB-130004"
}
```

Result:
```json
{
  "id": "MLB-130004",
  "date": "2026-07-10",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "heavy",
  "unit": "454.59",
  "qty": 1,
  "gross": "454.59",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 29: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130004"
}
```

Result:
```json
{
  "order_id": "MLB-130004",
  "rows": [
    {
      "sid": "ST-1300003",
      "oid": "MLB-130004",
      "date": "2026-07-13",
      "type": "payment",
      "gross": "454.59",
      "fee": "-63.64",
      "ship": "-39.90",
      "net": "351.05"
    }
  ],
  "sums": {
    "gross": "454.59",
    "fee": "-63.64",
    "ship": "-39.90",
    "net": "351.05"
  }
}
```

### Step 30: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130004"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130004",
    "date": "2026-07-10",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "heavy",
    "unit": "454.59",
    "qty": 1,
    "gross": "454.59",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "454.59",
      "fee": "-72.73",
      "ship": "-39.90",
      "net": "341.96"
    }
  ],
  "expected_net_total": "341.96",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 31: `get_order`

Input:
```json
{
  "order_id": "MLB-130006"
}
```

Result:
```json
{
  "id": "MLB-130006",
  "date": "2026-07-11",
  "status": "delivered",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "360.25",
  "qty": 1,
  "gross": "360.25",
  "inst": 10,
  "refund": "0.00"
}
```

### Step 32: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130006"
}
```

Result:
```json
{
  "order_id": "MLB-130006",
  "rows": [
    {
      "sid": "ST-1300006",
      "oid": "MLB-130006",
      "date": "2026-07-14",
      "type": "payment",
      "gross": "360.25",
      "fee": "-50.44",
      "ship": "-21.90",
      "net": "287.91"
    }
  ],
  "sums": {
    "gross": "360.25",
    "fee": "-50.44",
    "ship": "-21.90",
    "net": "287.91"
  }
}
```

### Step 33: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130006"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130006",
    "date": "2026-07-11",
    "status": "delivered",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "360.25",
    "qty": 1,
    "gross": "360.25",
    "inst": 10,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "360.25",
      "fee": "-57.64",
      "ship": "-21.90",
      "net": "280.71"
    }
  ],
  "expected_net_total": "280.71",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 34: `get_order`

Input:
```json
{
  "order_id": "MLB-130002"
}
```

Result:
```json
{
  "id": "MLB-130002",
  "date": "2026-07-09",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "351.59",
  "qty": 1,
  "gross": "351.59",
  "inst": 6,
  "refund": "0.00"
}
```

### Step 35: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130002"
}
```

Result:
```json
{
  "order_id": "MLB-130002",
  "rows": [
    {
      "sid": "ST-1300002",
      "oid": "MLB-130002",
      "date": "2026-07-12",
      "type": "payment",
      "gross": "351.59",
      "fee": "-49.22",
      "ship": "-21.90",
      "net": "280.47"
    }
  ],
  "sums": {
    "gross": "351.59",
    "fee": "-49.22",
    "ship": "-21.90",
    "net": "280.47"
  }
}
```

### Step 36: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130002"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130002",
    "date": "2026-07-09",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "351.59",
    "qty": 1,
    "gross": "351.59",
    "inst": 6,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "351.59",
      "fee": "-56.25",
      "ship": "-21.90",
      "net": "273.44"
    }
  ],
  "expected_net_total": "273.44",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 37: `get_order`

Input:
```json
{
  "order_id": "MLB-130001"
}
```

Result:
```json
{
  "id": "MLB-130001",
  "date": "2026-07-08",
  "status": "delivered",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "190.08",
  "qty": 1,
  "gross": "190.08",
  "inst": 10,
  "refund": "0.00"
}
```

### Step 38: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130001"
}
```

Result:
```json
{
  "order_id": "MLB-130001",
  "rows": [
    {
      "sid": "ST-1300001",
      "oid": "MLB-130001",
      "date": "2026-07-11",
      "type": "payment",
      "gross": "190.08",
      "fee": "-26.61",
      "ship": "-21.90",
      "net": "141.57"
    }
  ],
  "sums": {
    "gross": "190.08",
    "fee": "-26.61",
    "ship": "-21.90",
    "net": "141.57"
  }
}
```

### Step 39: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130001"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130001",
    "date": "2026-07-08",
    "status": "delivered",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "190.08",
    "qty": 1,
    "gross": "190.08",
    "inst": 10,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "190.08",
      "fee": "-30.41",
      "ship": "-21.90",
      "net": "137.77"
    }
  ],
  "expected_net_total": "137.77",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 40: `get_order`

Input:
```json
{
  "order_id": "MLB-130007"
}
```

Result:
```json
{
  "id": "MLB-130007",
  "date": "2026-07-12",
  "status": "delivered",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "139.58",
  "qty": 1,
  "gross": "139.58",
  "inst": 12,
  "refund": "0.00"
}
```

### Step 41: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130007"
}
```

Result:
```json
{
  "order_id": "MLB-130007",
  "rows": [
    {
      "sid": "ST-1300007",
      "oid": "MLB-130007",
      "date": "2026-07-15",
      "type": "payment",
      "gross": "139.58",
      "fee": "-19.54",
      "ship": "-21.90",
      "net": "98.14"
    }
  ],
  "sums": {
    "gross": "139.58",
    "fee": "-19.54",
    "ship": "-21.90",
    "net": "98.14"
  }
}
```

### Step 42: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130007"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130007",
    "date": "2026-07-12",
    "status": "delivered",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "139.58",
    "qty": 1,
    "gross": "139.58",
    "inst": 12,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "139.58",
      "fee": "-22.33",
      "ship": "-21.90",
      "net": "95.35"
    }
  ],
  "expected_net_total": "95.35",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 43: `get_order`

Input:
```json
{
  "order_id": "MLB-130011"
}
```

Result:
```json
{
  "id": "MLB-130011",
  "date": "2026-07-16",
  "status": "delivered",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "52.76",
  "qty": 2,
  "gross": "105.52",
  "inst": 3,
  "refund": "0.00"
}
```

### Step 44: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130011"
}
```

Result:
```json
{
  "order_id": "MLB-130011",
  "rows": [
    {
      "sid": "ST-1300011",
      "oid": "MLB-130011",
      "date": "2026-07-19",
      "type": "payment",
      "gross": "105.52",
      "fee": "-27.27",
      "ship": "-21.90",
      "net": "56.35"
    }
  ],
  "sums": {
    "gross": "105.52",
    "fee": "-27.27",
    "ship": "-21.90",
    "net": "56.35"
  }
}
```

### Step 45: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130011"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130011",
    "date": "2026-07-16",
    "status": "delivered",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "52.76",
    "qty": 2,
    "gross": "105.52",
    "inst": 3,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "105.52",
      "fee": "-29.38",
      "ship": "-21.90",
      "net": "54.24"
    }
  ],
  "expected_net_total": "54.24",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 46: `get_order`

Input:
```json
{
  "order_id": "MLB-130052"
}
```

Result:
```json
{
  "id": "MLB-130052",
  "date": "2026-07-03",
  "status": "partially_refunded",
  "cat": "fashion",
  "listing": "classic",
  "weight": "standard",
  "unit": "17.93",
  "qty": 1,
  "gross": "17.93",
  "inst": 1,
  "refund": "3.59"
}
```

### Step 47: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130052"
}
```

Result:
```json
{
  "order_id": "MLB-130052",
  "rows": [
    {
      "sid": "ST-1300055",
      "oid": "MLB-130052",
      "date": "2026-07-06",
      "type": "payment",
      "gross": "17.93",
      "fee": "-8.58",
      "ship": "0.00",
      "net": "9.35"
    },
    {
      "sid": "ST-1300056",
      "oid": "MLB-130052",
      "date": "2026-07-13",
      "type": "refund",
      "gross": "-3.59",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-3.59"
    }
  ],
  "sums": {
    "gross": "14.34",
    "fee": "-8.58",
    "ship": "0.00",
    "net": "5.76"
  }
}
```

### Step 48: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130052"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130052",
    "date": "2026-07-03",
    "status": "partially_refunded",
    "cat": "fashion",
    "listing": "classic",
    "weight": "standard",
    "unit": "17.93",
    "qty": 1,
    "gross": "17.93",
    "inst": 1,
    "refund": "3.59"
  },
  "commission_rate_pct": 13.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "17.93",
      "fee": "-8.58",
      "ship": "0.00",
      "net": "9.35"
    },
    {
      "type": "refund",
      "gross": "-3.59",
      "fee": "1.72",
      "ship": "0.00",
      "net": "-1.87"
    }
  ],
  "expected_net_total": "7.48",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 49: `get_order`

Input:
```json
{
  "order_id": "MLB-130138"
}
```

Result:
```json
{
  "id": "MLB-130138",
  "date": "2026-07-08",
  "status": "delivered",
  "cat": "electronics",
  "listing": "classic",
  "weight": "standard",
  "unit": "32.57",
  "qty": 1,
  "gross": "32.57",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 50: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130138"
}
```

Result:
```json
{
  "order_id": "MLB-130138",
  "rows": [
    {
      "sid": "ST-1300148",
      "oid": "MLB-130138",
      "date": "2026-07-11",
      "type": "payment",
      "gross": "32.57",
      "fee": "-9.18",
      "ship": "0.00",
      "net": "23.39"
    }
  ],
  "sums": {
    "gross": "32.57",
    "fee": "-9.18",
    "ship": "0.00",
    "net": "23.39"
  }
}
```

### Step 51: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130138"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130138",
    "date": "2026-07-08",
    "status": "delivered",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "32.57",
    "qty": 1,
    "gross": "32.57",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "32.57",
      "fee": "-9.83",
      "ship": "0.00",
      "net": "22.74"
    }
  ],
  "expected_net_total": "22.74",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 52: `get_order`

Input:
```json
{
  "order_id": "MLB-130117"
}
```

Result:
```json
{
  "id": "MLB-130117",
  "date": "2026-07-18",
  "status": "delivered",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "31.99",
  "qty": 1,
  "gross": "31.99",
  "inst": 10,
  "refund": "0.00"
}
```

### Step 53: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130117"
}
```

Result:
```json
{
  "order_id": "MLB-130117",
  "rows": [
    {
      "sid": "ST-1300128",
      "oid": "MLB-130117",
      "date": "2026-07-21",
      "type": "payment",
      "gross": "31.99",
      "fee": "-10.73",
      "ship": "0.00",
      "net": "21.26"
    }
  ],
  "sums": {
    "gross": "31.99",
    "fee": "-10.73",
    "ship": "0.00",
    "net": "21.26"
  }
}
```

### Step 54: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130117"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130117",
    "date": "2026-07-18",
    "status": "delivered",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "31.99",
    "qty": 1,
    "gross": "31.99",
    "inst": 10,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "31.99",
      "fee": "-11.37",
      "ship": "0.00",
      "net": "20.62"
    }
  ],
  "expected_net_total": "20.62",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 55: `get_order`

Input:
```json
{
  "order_id": "MLB-130008"
}
```

Result:
```json
{
  "id": "MLB-130008",
  "date": "2026-07-13",
  "status": "delivered",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "29.92",
  "qty": 1,
  "gross": "29.92",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 56: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130008"
}
```

Result:
```json
{
  "order_id": "MLB-130008",
  "rows": [
    {
      "sid": "ST-1300008",
      "oid": "MLB-130008",
      "date": "2026-07-16",
      "type": "payment",
      "gross": "29.92",
      "fee": "-10.44",
      "ship": "0.00",
      "net": "19.48"
    }
  ],
  "sums": {
    "gross": "29.92",
    "fee": "-10.44",
    "ship": "0.00",
    "net": "19.48"
  }
}
```

### Step 57: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130008"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130008",
    "date": "2026-07-13",
    "status": "delivered",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "29.92",
    "qty": 1,
    "gross": "29.92",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "29.92",
      "fee": "-11.04",
      "ship": "0.00",
      "net": "18.88"
    }
  ],
  "expected_net_total": "18.88",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 58: `get_order`

Input:
```json
{
  "order_id": "MLB-130088"
}
```

Result:
```json
{
  "id": "MLB-130088",
  "date": "2026-07-14",
  "status": "delivered",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "19.96",
  "qty": 1,
  "gross": "19.96",
  "inst": 12,
  "refund": "0.00"
}
```

### Step 59: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130088"
}
```

Result:
```json
{
  "order_id": "MLB-130088",
  "rows": [
    {
      "sid": "ST-1300095",
      "oid": "MLB-130088",
      "date": "2026-07-17",
      "type": "payment",
      "gross": "19.96",
      "fee": "-9.04",
      "ship": "0.00",
      "net": "10.92"
    }
  ],
  "sums": {
    "gross": "19.96",
    "fee": "-9.04",
    "ship": "0.00",
    "net": "10.92"
  }
}
```

### Step 60: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130088"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130088",
    "date": "2026-07-14",
    "status": "delivered",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "19.96",
    "qty": 1,
    "gross": "19.96",
    "inst": 12,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "19.96",
      "fee": "-9.44",
      "ship": "0.00",
      "net": "10.52"
    }
  ],
  "expected_net_total": "10.52",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 61: `get_order`

Input:
```json
{
  "order_id": "MLB-130097"
}
```

Result:
```json
{
  "id": "MLB-130097",
  "date": "2026-07-09",
  "status": "partially_refunded",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "22.42",
  "qty": 1,
  "gross": "22.42",
  "inst": 12,
  "refund": "15.69"
}
```

### Step 62: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130097"
}
```

Result:
```json
{
  "order_id": "MLB-130097",
  "rows": [
    {
      "sid": "ST-1300105",
      "oid": "MLB-130097",
      "date": "2026-07-12",
      "type": "payment",
      "gross": "22.42",
      "fee": "-9.39",
      "ship": "0.00",
      "net": "13.03"
    },
    {
      "sid": "ST-1300106",
      "oid": "MLB-130097",
      "date": "2026-07-19",
      "type": "refund",
      "gross": "-15.69",
      "fee": "6.57",
      "ship": "0.00",
      "net": "-9.12"
    }
  ],
  "sums": {
    "gross": "6.73",
    "fee": "-2.82",
    "ship": "0.00",
    "net": "3.91"
  }
}
```

### Step 63: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130097"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130097",
    "date": "2026-07-09",
    "status": "partially_refunded",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "22.42",
    "qty": 1,
    "gross": "22.42",
    "inst": 12,
    "refund": "15.69"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "22.42",
      "fee": "-9.84",
      "ship": "0.00",
      "net": "12.58"
    },
    {
      "type": "refund",
      "gross": "-15.69",
      "fee": "6.89",
      "ship": "0.00",
      "net": "-8.80"
    }
  ],
  "expected_net_total": "3.78",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 64: `list_orders`

Input:
```json
{
  "status": "</antml parameter>\n<parameter name=\"offset\">0"
}
```

Result:
```json
{
  "total_matching": 0,
  "offset": 0,
  "returned": 0,
  "has_more": false,
  "orders": []
}
```

### Step 65: `list_orders`

Input:
```json
{
  "offset": 0
}
```

Result:
```json
{
  "total_matching": 150,
  "offset": 0,
  "returned": 25,
  "has_more": true,
  "orders": [
    {
      "id": "MLB-130001",
      "date": "2026-07-08",
      "status": "delivered",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "190.08",
      "qty": 1,
      "gross": "190.08",
      "inst": 10,
      "refund": "0.00"
    },
    {
      "id": "MLB-130002",
      "date": "2026-07-09",
      "status": "paid",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "351.59",
      "qty": 1,
      "gross": "351.59",
      "inst": 6,
      "refund": "0.00"
    },
    {
      "id": "MLB-130003",
      "date": "2026-07-07",
      "status": "cancelled",
      "cat": "toys",
      "listing": "premium",
      "weight": "standard",
      "unit": "2020.25",
      "qty": 1,
      "gross": "2020.25",
      "inst": 6,
      "refund": "0.00"
    },
    {
      "id": "MLB-130004",
      "date": "2026-07-10",
      "status": "paid",
      "cat": "electronics",
      "listing": "premium",
      "weight": "heavy",
      "unit": "454.59",
      "qty": 1,
      "gross": "454.59",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130005",
      "date": "2026-07-01",
      "status": "refunded",
      "cat": "fashion",
      "listing": "classic",
      "weight": "standard",
      "unit": "1943.27",
      "qty": 1,
      "gross": "1943.27",
      "inst": 1,
      "refund": "1943.27"
    },
    {
      "id": "MLB-130006",
      "date": "2026-07-11",
      "status": "delivered",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "360.25",
      "qty": 1,
      "gross": "360.25",
      "inst": 10,
      "refund": "0.00"
    },
    {
      "id": "MLB-130007",
      "date": "2026-07-12",
      "status": "delivered",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "139.58",
      "qty": 1,
      "gross": "139.58",
      "inst": 12,
      "refund": "0.00"
    },
    {
      "id": "MLB-130008",
      "date": "2026-07-13",
      "status": "delivered",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "29.92",
      "qty": 1,
      "gross": "29.92",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130009",
      "date": "2026-07-14",
      "status": "paid",
      "cat": "electronics",
      "listing": "premium",
      "weight": "heavy",
      "unit": "2253.85",
      "qty": 3,
      "gross": "6761.55",
      "inst": 12,
      "refund": "0.00"
    },
    {
      "id": "MLB-130010",
      "date": "2026-07-15",
      "status": "paid",
      "cat": "electronics",
      "listing": "classic",
      "weight": "heavy",
      "unit": "1030.83",
      "qty": 3,
      "gross": "3092.49",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130011",
      "date": "2026-07-16",
      "status": "deliver
... (truncated for readability; full data in the .jsonl)
```

### Step 66: `list_orders`

Input:
```json
{
  "offset": 25
}
```

Result:
```json
{
  "total_matching": 150,
  "offset": 25,
  "returned": 25,
  "has_more": true,
  "orders": [
    {
      "id": "MLB-130026",
      "date": "2026-07-16",
      "status": "delivered",
      "cat": "fashion",
      "listing": "classic",
      "weight": "standard",
      "unit": "526.91",
      "qty": 3,
      "gross": "1580.73",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130027",
      "date": "2026-07-14",
      "status": "delivered",
      "cat": "fashion",
      "listing": "classic",
      "weight": "standard",
      "unit": "23.23",
      "qty": 1,
      "gross": "23.23",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130028",
      "date": "2026-07-02",
      "status": "partially_refunded",
      "cat": "electronics",
      "listing": "classic",
      "weight": "standard",
      "unit": "36.26",
      "qty": 2,
      "gross": "72.52",
      "inst": 1,
      "refund": "14.50"
    },
    {
      "id": "MLB-130029",
      "date": "2026-07-13",
      "status": "delivered",
      "cat": "home",
      "listing": "classic",
      "weight": "standard",
      "unit": "76.08",
      "qty": 3,
      "gross": "228.24",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130030",
      "date": "2026-07-16",
      "status": "delivered",
      "cat": "books",
      "listing": "premium",
      "weight": "standard",
      "unit": "34.50",
      "qty": 1,
      "gross": "34.50",
      "inst": 10,
      "refund": "0.00"
    },
    {
      "id": "MLB-130031",
      "date": "2026-07-28",
      "status": "delivered",
      "cat": "books",
      "listing": "premium",
      "weight": "standard",
      "unit": "785.51",
      "qty": 1,
      "gross": "785.51",
      "inst": 12,
      "refund": "0.00"
    },
    {
      "id": "MLB-130032",
      "date": "2026-07-09",
      "status": "delivered",
      "cat": "home",
      "listing": "classic",
      "weight": "heavy",
      "unit": "513.80",
      "qty": 3,
      "gross": "1541.40",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130033",
      "date": "2026-07-25",
      "status": "partially_refunded",
      "cat": "books",
      "listing": "classic",
      "weight": "standard",
      "unit": "37.97",
      "qty": 2,
      "gross": "75.94",
      "inst": 1,
      "refund": "45.56"
    },
    {
      "id": "MLB-130034",
      "date": "2026-07-15",
      "status": "paid",
      "cat": "books",
      "listing": "classic",
      "weight": "standard",
      "unit": "60.78",
      "qty": 1,
      "gross": "60.78",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130035",
      "date": "2026-07-03",
      "status": "delivered",
      "cat": "home",
      "listing": "classic",
      "weight": "standard",
      "unit": "38.61",
      "qty": 1,
      "gross": "38.61",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130036",
      "date": "2026-07-12",
      "status": "paid",
      "cat": "fashion
... (truncated for readability; full data in the .jsonl)
```

### Step 67: `list_orders`

Input:
```json
{
  "offset": 50
}
```

Result:
```json
{
  "total_matching": 150,
  "offset": 50,
  "returned": 25,
  "has_more": true,
  "orders": [
    {
      "id": "MLB-130051",
      "date": "2026-07-19",
      "status": "delivered",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "261.04",
      "qty": 2,
      "gross": "522.08",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130052",
      "date": "2026-07-03",
      "status": "partially_refunded",
      "cat": "fashion",
      "listing": "classic",
      "weight": "standard",
      "unit": "17.93",
      "qty": 1,
      "gross": "17.93",
      "inst": 1,
      "refund": "3.59"
    },
    {
      "id": "MLB-130053",
      "date": "2026-07-28",
      "status": "paid",
      "cat": "toys",
      "listing": "premium",
      "weight": "standard",
      "unit": "1966.39",
      "qty": 1,
      "gross": "1966.39",
      "inst": 10,
      "refund": "0.00"
    },
    {
      "id": "MLB-130054",
      "date": "2026-07-23",
      "status": "delivered",
      "cat": "fashion",
      "listing": "premium",
      "weight": "standard",
      "unit": "43.06",
      "qty": 3,
      "gross": "129.18",
      "inst": 10,
      "refund": "0.00"
    },
    {
      "id": "MLB-130055",
      "date": "2026-07-17",
      "status": "paid",
      "cat": "home",
      "listing": "premium",
      "weight": "heavy",
      "unit": "2045.54",
      "qty": 2,
      "gross": "4091.08",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130056",
      "date": "2026-07-25",
      "status": "paid",
      "cat": "toys",
      "listing": "classic",
      "weight": "standard",
      "unit": "298.58",
      "qty": 2,
      "gross": "597.16",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130057",
      "date": "2026-07-11",
      "status": "delivered",
      "cat": "toys",
      "listing": "premium",
      "weight": "standard",
      "unit": "64.40",
      "qty": 1,
      "gross": "64.40",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130058",
      "date": "2026-07-23",
      "status": "delivered",
      "cat": "toys",
      "listing": "classic",
      "weight": "standard",
      "unit": "2176.09",
      "qty": 3,
      "gross": "6528.27",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130059",
      "date": "2026-07-23",
      "status": "delivered",
      "cat": "electronics",
      "listing": "classic",
      "weight": "standard",
      "unit": "73.12",
      "qty": 2,
      "gross": "146.24",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130060",
      "date": "2026-07-26",
      "status": "delivered",
      "cat": "home",
      "listing": "premium",
      "weight": "standard",
      "unit": "295.60",
      "qty": 1,
      "gross": "295.60",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130061",
      "date": "2026-07-15",
      "status": "paid",
      "cat": "home",
      "
... (truncated for readability; full data in the .jsonl)
```

### Step 68: `list_orders`

Input:
```json
{
  "offset": 75
}
```

Result:
```json
{
  "total_matching": 150,
  "offset": 75,
  "returned": 25,
  "has_more": true,
  "orders": [
    {
      "id": "MLB-130076",
      "date": "2026-07-20",
      "status": "cancelled",
      "cat": "electronics",
      "listing": "classic",
      "weight": "heavy",
      "unit": "448.94",
      "qty": 3,
      "gross": "1346.82",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130077",
      "date": "2026-07-15",
      "status": "delivered",
      "cat": "home",
      "listing": "classic",
      "weight": "heavy",
      "unit": "934.76",
      "qty": 1,
      "gross": "934.76",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130078",
      "date": "2026-07-25",
      "status": "paid",
      "cat": "books",
      "listing": "classic",
      "weight": "standard",
      "unit": "38.59",
      "qty": 1,
      "gross": "38.59",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130079",
      "date": "2026-07-07",
      "status": "paid",
      "cat": "toys",
      "listing": "premium",
      "weight": "standard",
      "unit": "208.14",
      "qty": 3,
      "gross": "624.42",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130080",
      "date": "2026-07-06",
      "status": "delivered",
      "cat": "home",
      "listing": "premium",
      "weight": "standard",
      "unit": "81.44",
      "qty": 3,
      "gross": "244.32",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130081",
      "date": "2026-07-15",
      "status": "paid",
      "cat": "fashion",
      "listing": "classic",
      "weight": "standard",
      "unit": "634.51",
      "qty": 3,
      "gross": "1903.53",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130082",
      "date": "2026-07-03",
      "status": "delivered",
      "cat": "toys",
      "listing": "classic",
      "weight": "standard",
      "unit": "221.98",
      "qty": 2,
      "gross": "443.96",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130083",
      "date": "2026-07-14",
      "status": "paid",
      "cat": "electronics",
      "listing": "classic",
      "weight": "heavy",
      "unit": "2013.19",
      "qty": 3,
      "gross": "6039.57",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130084",
      "date": "2026-07-01",
      "status": "paid",
      "cat": "toys",
      "listing": "premium",
      "weight": "standard",
      "unit": "2119.23",
      "qty": 3,
      "gross": "6357.69",
      "inst": 6,
      "refund": "0.00"
    },
    {
      "id": "MLB-130085",
      "date": "2026-07-10",
      "status": "refunded",
      "cat": "fashion",
      "listing": "premium",
      "weight": "standard",
      "unit": "312.19",
      "qty": 2,
      "gross": "624.38",
      "inst": 3,
      "refund": "624.38"
    },
    {
      "id": "MLB-130086",
      "date": "2026-07-19",
      "status": "paid",
      "cat": "electronics",
      "listing": "prem
... (truncated for readability; full data in the .jsonl)
```

### Step 69: `list_orders`

Input:
```json
{
  "offset": 100
}
```

Result:
```json
{
  "total_matching": 150,
  "offset": 100,
  "returned": 25,
  "has_more": true,
  "orders": [
    {
      "id": "MLB-130101",
      "date": "2026-07-11",
      "status": "refunded",
      "cat": "home",
      "listing": "premium",
      "weight": "standard",
      "unit": "18.12",
      "qty": 1,
      "gross": "18.12",
      "inst": 10,
      "refund": "18.12"
    },
    {
      "id": "MLB-130102",
      "date": "2026-07-07",
      "status": "delivered",
      "cat": "toys",
      "listing": "premium",
      "weight": "standard",
      "unit": "416.32",
      "qty": 2,
      "gross": "832.64",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130103",
      "date": "2026-07-03",
      "status": "delivered",
      "cat": "fashion",
      "listing": "premium",
      "weight": "standard",
      "unit": "253.14",
      "qty": 3,
      "gross": "759.42",
      "inst": 6,
      "refund": "0.00"
    },
    {
      "id": "MLB-130104",
      "date": "2026-07-21",
      "status": "paid",
      "cat": "books",
      "listing": "premium",
      "weight": "standard",
      "unit": "285.65",
      "qty": 1,
      "gross": "285.65",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130105",
      "date": "2026-07-11",
      "status": "delivered",
      "cat": "fashion",
      "listing": "premium",
      "weight": "standard",
      "unit": "66.19",
      "qty": 1,
      "gross": "66.19",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130106",
      "date": "2026-07-21",
      "status": "delivered",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "63.18",
      "qty": 1,
      "gross": "63.18",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130107",
      "date": "2026-07-18",
      "status": "paid",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "318.62",
      "qty": 3,
      "gross": "955.86",
      "inst": 10,
      "refund": "0.00"
    },
    {
      "id": "MLB-130108",
      "date": "2026-07-17",
      "status": "delivered",
      "cat": "home",
      "listing": "classic",
      "weight": "standard",
      "unit": "166.26",
      "qty": 1,
      "gross": "166.26",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130109",
      "date": "2026-07-17",
      "status": "delivered",
      "cat": "home",
      "listing": "premium",
      "weight": "standard",
      "unit": "156.17",
      "qty": 2,
      "gross": "312.34",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130110",
      "date": "2026-07-05",
      "status": "delivered",
      "cat": "toys",
      "listing": "premium",
      "weight": "standard",
      "unit": "340.68",
      "qty": 1,
      "gross": "340.68",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-130111",
      "date": "2026-07-10",
      "status": "refunded",
      "cat": "home",
      "l
... (truncated for readability; full data in the .jsonl)
```

### Step 70: `list_orders`

Input:
```json
{
  "offset": 125
}
```

Result:
```json
{
  "total_matching": 150,
  "offset": 125,
  "returned": 25,
  "has_more": false,
  "orders": [
    {
      "id": "MLB-130126",
      "date": "2026-07-28",
      "status": "delivered",
      "cat": "books",
      "listing": "premium",
      "weight": "standard",
      "unit": "1625.46",
      "qty": 3,
      "gross": "4876.38",
      "inst": 12,
      "refund": "0.00"
    },
    {
      "id": "MLB-130127",
      "date": "2026-07-25",
      "status": "delivered",
      "cat": "electronics",
      "listing": "classic",
      "weight": "heavy",
      "unit": "1920.75",
      "qty": 1,
      "gross": "1920.75",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130128",
      "date": "2026-07-03",
      "status": "paid",
      "cat": "books",
      "listing": "premium",
      "weight": "standard",
      "unit": "33.54",
      "qty": 1,
      "gross": "33.54",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130129",
      "date": "2026-07-09",
      "status": "cancelled",
      "cat": "books",
      "listing": "classic",
      "weight": "standard",
      "unit": "95.45",
      "qty": 1,
      "gross": "95.45",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130130",
      "date": "2026-07-07",
      "status": "delivered",
      "cat": "books",
      "listing": "premium",
      "weight": "standard",
      "unit": "2014.71",
      "qty": 2,
      "gross": "4029.42",
      "inst": 12,
      "refund": "0.00"
    },
    {
      "id": "MLB-130131",
      "date": "2026-07-26",
      "status": "paid",
      "cat": "electronics",
      "listing": "classic",
      "weight": "heavy",
      "unit": "621.67",
      "qty": 3,
      "gross": "1865.01",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130132",
      "date": "2026-07-08",
      "status": "delivered",
      "cat": "electronics",
      "listing": "classic",
      "weight": "standard",
      "unit": "279.72",
      "qty": 2,
      "gross": "559.44",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130133",
      "date": "2026-07-07",
      "status": "delivered",
      "cat": "fashion",
      "listing": "classic",
      "weight": "standard",
      "unit": "308.41",
      "qty": 1,
      "gross": "308.41",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130134",
      "date": "2026-07-09",
      "status": "delivered",
      "cat": "fashion",
      "listing": "classic",
      "weight": "standard",
      "unit": "486.78",
      "qty": 3,
      "gross": "1460.34",
      "inst": 1,
      "refund": "0.00"
    },
    {
      "id": "MLB-130135",
      "date": "2026-07-25",
      "status": "delivered",
      "cat": "books",
      "listing": "premium",
      "weight": "standard",
      "unit": "312.85",
      "qty": 1,
      "gross": "312.85",
      "inst": 10,
      "refund": "0.00"
    },
    {
      "id": "MLB-130136",
      "date": "2026-07-07",
      "status": "delivered",
      "cat"
... (truncated for readability; full data in the .jsonl)
```

### Step 71: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130012"
}
```

Result:
```json
{
  "order_id": "MLB-130012",
  "rows": [
    {
      "sid": "ST-1300012",
      "oid": "MLB-130012",
      "date": "2026-07-20",
      "type": "payment",
      "gross": "424.29",
      "fee": "-67.89",
      "ship": "-39.90",
      "net": "316.50"
    }
  ],
  "sums": {
    "gross": "424.29",
    "fee": "-67.89",
    "ship": "-39.90",
    "net": "316.50"
  }
}
```

### Step 72: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130012"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130012",
    "date": "2026-07-17",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "heavy",
    "unit": "424.29",
    "qty": 1,
    "gross": "424.29",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "424.29",
      "fee": "-67.89",
      "ship": "-39.90",
      "net": "316.50"
    }
  ],
  "expected_net_total": "316.50",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 73: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130039"
}
```

Result:
```json
{
  "order_id": "MLB-130039",
  "rows": [
    {
      "sid": "ST-1300043",
      "oid": "MLB-130039",
      "date": "2026-07-09",
      "type": "payment",
      "gross": "48.63",
      "fee": "-11.60",
      "ship": "0.00",
      "net": "37.03"
    }
  ],
  "sums": {
    "gross": "48.63",
    "fee": "-11.60",
    "ship": "0.00",
    "net": "37.03"
  }
}
```

### Step 74: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130039"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130039",
    "date": "2026-07-06",
    "status": "paid",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "48.63",
    "qty": 1,
    "gross": "48.63",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "48.63",
      "fee": "-11.60",
      "ship": "0.00",
      "net": "37.03"
    }
  ],
  "expected_net_total": "37.03",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 75: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130046"
}
```

Result:
```json
{
  "order_id": "MLB-130046",
  "rows": [
    {
      "sid": "ST-1300049",
      "oid": "MLB-130046",
      "date": "2026-07-28",
      "type": "payment",
      "gross": "74.69",
      "fee": "-18.20",
      "ship": "0.00",
      "net": "56.49"
    }
  ],
  "sums": {
    "gross": "74.69",
    "fee": "-18.20",
    "ship": "0.00",
    "net": "56.49"
  }
}
```

### Step 76: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130046"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130046",
    "date": "2026-07-25",
    "status": "delivered",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "74.69",
    "qty": 1,
    "gross": "74.69",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "74.69",
      "fee": "-18.20",
      "ship": "0.00",
      "net": "56.49"
    }
  ],
  "expected_net_total": "56.49",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 77: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130059"
}
```

Result:
```json
{
  "order_id": "MLB-130059",
  "rows": [
    {
      "sid": "ST-1300063",
      "oid": "MLB-130059",
      "date": "2026-07-26",
      "type": "payment",
      "gross": "146.24",
      "fee": "-28.59",
      "ship": "-21.90",
      "net": "95.75"
    }
  ],
  "sums": {
    "gross": "146.24",
    "fee": "-28.59",
    "ship": "-21.90",
    "net": "95.75"
  }
}
```

### Step 78: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130059"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130059",
    "date": "2026-07-23",
    "status": "delivered",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "73.12",
    "qty": 2,
    "gross": "146.24",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "146.24",
      "fee": "-28.59",
      "ship": "-21.90",
      "net": "95.75"
    }
  ],
  "expected_net_total": "95.75",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 79: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130028"
}
```

Result:
```json
{
  "order_id": "MLB-130028",
  "rows": [
    {
      "sid": "ST-1300030",
      "oid": "MLB-130028",
      "date": "2026-07-05",
      "type": "payment",
      "gross": "72.52",
      "fee": "-20.48",
      "ship": "0.00",
      "net": "52.04"
    },
    {
      "sid": "ST-1300031",
      "oid": "MLB-130028",
      "date": "2026-07-12",
      "type": "refund",
      "gross": "-14.50",
      "fee": "4.10",
      "ship": "0.00",
      "net": "-10.40"
    }
  ],
  "sums": {
    "gross": "58.02",
    "fee": "-16.38",
    "ship": "0.00",
    "net": "41.64"
  }
}
```

### Step 80: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130065"
}
```

Result:
```json
{
  "order_id": "MLB-130065",
  "rows": [
    {
      "sid": "ST-1300069",
      "oid": "MLB-130065",
      "date": "2026-07-22",
      "type": "payment",
      "gross": "69.22",
      "fee": "-13.86",
      "ship": "0.00",
      "net": "55.36"
    }
  ],
  "sums": {
    "gross": "69.22",
    "fee": "-13.86",
    "ship": "0.00",
    "net": "55.36"
  }
}
```

### Step 81: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130074"
}
```

Result:
```json
{
  "order_id": "MLB-130074",
  "rows": [
    {
      "sid": "ST-1300080",
      "oid": "MLB-130074",
      "date": "2026-07-14",
      "type": "payment",
      "gross": "691.12",
      "fee": "-62.20",
      "ship": "-21.90",
      "net": "607.02"
    },
    {
      "sid": "ST-1300081",
      "oid": "MLB-130074",
      "date": "2026-07-21",
      "type": "refund",
      "gross": "-691.12",
      "fee": "62.20",
      "ship": "0.00",
      "net": "-628.92"
    }
  ],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "-21.90",
    "net": "-21.90"
  }
}
```

### Step 82: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130086"
}
```

Result:
```json
{
  "order_id": "MLB-130086",
  "rows": [
    {
      "sid": "ST-1300093",
      "oid": "MLB-130086",
      "date": "2026-07-22",
      "type": "payment",
      "gross": "4363.16",
      "fee": "-698.11",
      "ship": "-39.90",
      "net": "3625.15"
    }
  ],
  "sums": {
    "gross": "4363.16",
    "fee": "-698.11",
    "ship": "-39.90",
    "net": "3625.15"
  }
}
```

### Step 83: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130091"
}
```

Result:
```json
{
  "order_id": "MLB-130091",
  "rows": [
    {
      "sid": "ST-1300099",
      "oid": "MLB-130091",
      "date": "2026-07-06",
      "type": "payment",
      "gross": "2043.27",
      "fee": "-224.76",
      "ship": "-39.90",
      "net": "1778.61"
    }
  ],
  "sums": {
    "gross": "2043.27",
    "fee": "-224.76",
    "ship": "-39.90",
    "net": "1778.61"
  }
}
```

### Step 84: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130092"
}
```

Result:
```json
{
  "order_id": "MLB-130092",
  "rows": [
    {
      "sid": "ST-1300100",
      "oid": "MLB-130092",
      "date": "2026-07-07",
      "type": "payment",
      "gross": "341.52",
      "fee": "-37.57",
      "ship": "-21.90",
      "net": "282.05"
    }
  ],
  "sums": {
    "gross": "341.52",
    "fee": "-37.57",
    "ship": "-21.90",
    "net": "282.05"
  }
}
```

### Step 85: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130106"
}
```

Result:
```json
{
  "order_id": "MLB-130106",
  "rows": [
    {
      "sid": "ST-1300116",
      "oid": "MLB-130106",
      "date": "2026-07-24",
      "type": "payment",
      "gross": "63.18",
      "fee": "-16.36",
      "ship": "0.00",
      "net": "46.82"
    }
  ],
  "sums": {
    "gross": "63.18",
    "fee": "-16.36",
    "ship": "0.00",
    "net": "46.82"
  }
}
```

### Step 86: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130124"
}
```

Result:
```json
{
  "order_id": "MLB-130124",
  "rows": [
    {
      "sid": "ST-1300134",
      "oid": "MLB-130124",
      "date": "2026-07-06",
      "type": "payment",
      "gross": "30.61",
      "fee": "-9.62",
      "ship": "0.00",
      "net": "20.99"
    }
  ],
  "sums": {
    "gross": "30.61",
    "fee": "-9.62",
    "ship": "0.00",
    "net": "20.99"
  }
}
```

### Step 87: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130127"
}
```

Result:
```json
{
  "order_id": "MLB-130127",
  "rows": [
    {
      "sid": "ST-1300137",
      "oid": "MLB-130127",
      "date": "2026-07-28",
      "type": "payment",
      "gross": "1920.75",
      "fee": "-211.28",
      "ship": "-39.90",
      "net": "1669.57"
    }
  ],
  "sums": {
    "gross": "1920.75",
    "fee": "-211.28",
    "ship": "-39.90",
    "net": "1669.57"
  }
}
```

### Step 88: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130131"
}
```

Result:
```json
{
  "order_id": "MLB-130131",
  "rows": [
    {
      "sid": "ST-1300140",
      "oid": "MLB-130131",
      "date": "2026-07-29",
      "type": "payment",
      "gross": "1865.01",
      "fee": "-205.15",
      "ship": "-39.90",
      "net": "1619.96"
    }
  ],
  "sums": {
    "gross": "1865.01",
    "fee": "-205.15",
    "ship": "-39.90",
    "net": "1619.96"
  }
}
```

### Step 89: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130140"
}
```

Result:
```json
{
  "order_id": "MLB-130140",
  "rows": [
    {
      "sid": "ST-1300150",
      "oid": "MLB-130140",
      "date": "2026-07-26",
      "type": "payment",
      "gross": "1611.75",
      "fee": "-257.88",
      "ship": "-39.90",
      "net": "1313.97"
    }
  ],
  "sums": {
    "gross": "1611.75",
    "fee": "-257.88",
    "ship": "-39.90",
    "net": "1313.97"
  }
}
```

### Step 90: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130145"
}
```

Result:
```json
{
  "order_id": "MLB-130145",
  "rows": [
    {
      "sid": "ST-1300154",
      "oid": "MLB-130145",
      "date": "2026-07-07",
      "type": "payment",
      "gross": "78.27",
      "fee": "-18.77",
      "ship": "0.00",
      "net": "59.50"
    }
  ],
  "sums": {
    "gross": "78.27",
    "fee": "-18.77",
    "ship": "0.00",
    "net": "59.50"
  }
}
```

### Step 91: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130146"
}
```

Result:
```json
{
  "order_id": "MLB-130146",
  "rows": [
    {
      "sid": "ST-1300155",
      "oid": "MLB-130146",
      "date": "2026-07-24",
      "type": "payment",
      "gross": "64.96",
      "fee": "-13.40",
      "ship": "0.00",
      "net": "51.56"
    },
    {
      "sid": "ST-1300156",
      "oid": "MLB-130146",
      "date": "2026-07-31",
      "type": "refund",
      "gross": "-64.96",
      "fee": "13.40",
      "ship": "0.00",
      "net": "-51.56"
    }
  ],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 92: `get_order`

Input:
```json
{
  "order_id": "MLB-130033"
}
```

Result:
```json
{
  "id": "MLB-130033",
  "date": "2026-07-25",
  "status": "partially_refunded",
  "cat": "books",
  "listing": "classic",
  "weight": "standard",
  "unit": "37.97",
  "qty": 2,
  "gross": "75.94",
  "inst": 1,
  "refund": "45.56"
}
```

### Step 93: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130033"
}
```

Result:
```json
{
  "order_id": "MLB-130033",
  "rows": [
    {
      "sid": "ST-1300036",
      "oid": "MLB-130033",
      "date": "2026-07-28",
      "type": "payment",
      "gross": "75.94",
      "fee": "-20.09",
      "ship": "0.00",
      "net": "55.85"
    },
    {
      "sid": "ST-1300037",
      "oid": "MLB-130033",
      "date": "2026-08-04",
      "type": "refund",
      "gross": "-45.56",
      "fee": "12.05",
      "ship": "0.00",
      "net": "-33.51"
    }
  ],
  "sums": {
    "gross": "30.38",
    "fee": "-8.04",
    "ship": "0.00",
    "net": "22.34"
  }
}
```

### Step 94: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130033"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130033",
    "date": "2026-07-25",
    "status": "partially_refunded",
    "cat": "books",
    "listing": "classic",
    "weight": "standard",
    "unit": "37.97",
    "qty": 2,
    "gross": "75.94",
    "inst": 1,
    "refund": "45.56"
  },
  "commission_rate_pct": 10.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "75.94",
      "fee": "-20.09",
      "ship": "0.00",
      "net": "55.85"
    },
    {
      "type": "refund",
      "gross": "-45.56",
      "fee": "12.05",
      "ship": "0.00",
      "net": "-33.51"
    }
  ],
  "expected_net_total": "22.34",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 95: `get_order`

Input:
```json
{
  "order_id": "MLB-130041"
}
```

Result:
```json
{
  "id": "MLB-130041",
  "date": "2026-07-15",
  "status": "partially_refunded",
  "cat": "books",
  "listing": "classic",
  "weight": "standard",
  "unit": "725.02",
  "qty": 3,
  "gross": "2175.06",
  "inst": 1,
  "refund": "1087.53"
}
```

### Step 96: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130041"
}
```

Result:
```json
{
  "order_id": "MLB-130041",
  "rows": [
    {
      "sid": "ST-1300045",
      "oid": "MLB-130041",
      "date": "2026-07-18",
      "type": "payment",
      "gross": "2175.06",
      "fee": "-217.51",
      "ship": "-21.90",
      "net": "1935.65"
    },
    {
      "sid": "ST-1300046",
      "oid": "MLB-130041",
      "date": "2026-07-25",
      "type": "refund",
      "gross": "-1087.53",
      "fee": "108.76",
      "ship": "0.00",
      "net": "-978.77"
    }
  ],
  "sums": {
    "gross": "1087.53",
    "fee": "-108.75",
    "ship": "-21.90",
    "net": "956.88"
  }
}
```

### Step 97: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130041"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130041",
    "date": "2026-07-15",
    "status": "partially_refunded",
    "cat": "books",
    "listing": "classic",
    "weight": "standard",
    "unit": "725.02",
    "qty": 3,
    "gross": "2175.06",
    "inst": 1,
    "refund": "1087.53"
  },
  "commission_rate_pct": 10.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "2175.06",
      "fee": "-217.51",
      "ship": "-21.90",
      "net": "1935.65"
    },
    {
      "type": "refund",
      "gross": "-1087.53",
      "fee": "108.76",
      "ship": "0.00",
      "net": "-978.77"
    }
  ],
  "expected_net_total": "956.88",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 98: `get_order`

Input:
```json
{
  "order_id": "MLB-130089"
}
```

Result:
```json
{
  "id": "MLB-130089",
  "date": "2026-07-17",
  "status": "partially_refunded",
  "cat": "toys",
  "listing": "classic",
  "weight": "standard",
  "unit": "15.09",
  "qty": 1,
  "gross": "15.09",
  "inst": 1,
  "refund": "6.04"
}
```

### Step 99: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130089"
}
```

Result:
```json
{
  "order_id": "MLB-130089",
  "rows": [
    {
      "sid": "ST-1300096",
      "oid": "MLB-130089",
      "date": "2026-07-20",
      "type": "payment",
      "gross": "15.09",
      "fee": "-8.06",
      "ship": "0.00",
      "net": "7.03"
    },
    {
      "sid": "ST-1300097",
      "oid": "MLB-130089",
      "date": "2026-07-27",
      "type": "refund",
      "gross": "-6.04",
      "fee": "3.22",
      "ship": "0.00",
      "net": "-2.82"
    }
  ],
  "sums": {
    "gross": "9.05",
    "fee": "-4.84",
    "ship": "0.00",
    "net": "4.21"
  }
}
```

### Step 100: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130089"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130089",
    "date": "2026-07-17",
    "status": "partially_refunded",
    "cat": "toys",
    "listing": "classic",
    "weight": "standard",
    "unit": "15.09",
    "qty": 1,
    "gross": "15.09",
    "inst": 1,
    "refund": "6.04"
  },
  "commission_rate_pct": 12.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "15.09",
      "fee": "-8.06",
      "ship": "0.00",
      "net": "7.03"
    },
    {
      "type": "refund",
      "gross": "-6.04",
      "fee": "3.22",
      "ship": "0.00",
      "net": "-2.82"
    }
  ],
  "expected_net_total": "4.21",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 101: `get_order`

Input:
```json
{
  "order_id": "MLB-130149"
}
```

Result:
```json
{
  "id": "MLB-130149",
  "date": "2026-07-04",
  "status": "partially_refunded",
  "cat": "fashion",
  "listing": "classic",
  "weight": "standard",
  "unit": "62.70",
  "qty": 1,
  "gross": "62.70",
  "inst": 1,
  "refund": "37.62"
}
```

### Step 102: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130149"
}
```

Result:
```json
{
  "order_id": "MLB-130149",
  "rows": [
    {
      "sid": "ST-1300159",
      "oid": "MLB-130149",
      "date": "2026-07-07",
      "type": "payment",
      "gross": "62.70",
      "fee": "-14.40",
      "ship": "0.00",
      "net": "48.30"
    },
    {
      "sid": "ST-1300160",
      "oid": "MLB-130149",
      "date": "2026-07-14",
      "type": "refund",
      "gross": "-37.62",
      "fee": "8.64",
      "ship": "0.00",
      "net": "-28.98"
    }
  ],
  "sums": {
    "gross": "25.08",
    "fee": "-5.76",
    "ship": "0.00",
    "net": "19.32"
  }
}
```

### Step 103: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130149"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130149",
    "date": "2026-07-04",
    "status": "partially_refunded",
    "cat": "fashion",
    "listing": "classic",
    "weight": "standard",
    "unit": "62.70",
    "qty": 1,
    "gross": "62.70",
    "inst": 1,
    "refund": "37.62"
  },
  "commission_rate_pct": 13.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "62.70",
      "fee": "-14.40",
      "ship": "0.00",
      "net": "48.30"
    },
    {
      "type": "refund",
      "gross": "-37.62",
      "fee": "8.64",
      "ship": "0.00",
      "net": "-28.98"
    }
  ],
  "expected_net_total": "19.32",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 104: `scan_mismatches`

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
      "order_id": "MLB-130009",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "5639.80",
      "observed_net": "5775.03",
      "delta": "135.23",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130083",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "5335.32",
      "observed_net": "5456.11",
      "delta": "120.79",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130014",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "3277.60",
      "observed_net": "3356.58",
      "delta": "78.98",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130115",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "3073.12",
      "observed_net": "3143.08",
      "delta": "69.96",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130010",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "2712.42",
      "observed_net": "2774.27",
      "delta": "61.85",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130107",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "781.02",
      "observed_net": "800.14",
      "delta": "19.12",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130013",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "625.55",
      "observed_net": "641.39",
      "delta": "15.84",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130132",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "476.00",
      "observed_net": "487.19",
      "delta": "11.19",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130004",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "341.96",
      "observed_net": "351.05",
      "delta": "9.09",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130006",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "280.71",
      "observed_net": "287.91",
      "delta": "7.20",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130002",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "273.44",
      "observed_net": "280.47",
      "delta": "7.03",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130001",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "137.77",
      "observed_net": "141.57",
      "delta": "3.80",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130007",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "95.35",
      "observed_net": "98.14",
      "delta": "2.79",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-130011",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "54.24",
      "observed_net": "56.35",
      "delta": "2.11",
      "rows_o
... (truncated for readability; full data in the .jsonl)
```

### Step 105: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130003"
}
```

Result:
```json
{
  "order_id": "MLB-130003",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 106: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130076"
}
```

Result:
```json
{
  "order_id": "MLB-130076",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 107: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130121"
}
```

Result:
```json
{
  "order_id": "MLB-130121",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

**Agent:**

> Good, cancelled orders are clean. Now let's finalize impact calculations and submit findings.

### Step 108: `submit_findings`

Input:
```json
{
  "findings": [
    {
      "order_id": "MLB-130009",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics premium listing: contractual commission is 16% of gross (expected fee -1081.85 on gross 6761.55 -> expected net 5639.80). Settlement row ST-1300009 applied only 14% (-946.62), yielding observed net 5775.03. Commission under-collected by 135.23.",
      "impact_brl": "-135.23"
    },
    {
      "order_id": "MLB-130083",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics classic listing: contractual commission is 11% of gross (expected fee -664.35 on gross 6039.57 -> expected net 5335.32). Settlement row ST-1300089 applied only 9% (-543.56), yielding observed net 5456.11. Commission under-collected by 120.79.",
      "impact_brl": "-120.79"
    },
    {
      "order_id": "MLB-130014",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics premium listing: contractual commission is 16% of gross (expected fee -631.90 on gross 3949.40 -> expected net 3277.60). Settlement row ST-1300014 applied only 14% (-552.92), yielding observed net 3356.58. Commission under-collected by 78.98.",
      "impact_brl": "-78.98"
    },
    {
      "order_id": "MLB-130115",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics classic listing: contractual commission is 11% of gross (expected fee -384.76 on gross 3497.78 -> expected net 3073.12). Settlement row ST-1300126 applied only 9% (-314.80), yielding observed net 3143.08. Commission under-collected by 69.96.",
      "impact_brl": "-69.96"
    },
    {
      "order_id": "MLB-130010",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics classic listing: contractual commission is 11% of gross (expected fee -340.17 on gross 3092.49 -> expected net 2712.42). Settlement row ST-1300010 applied only 9% (-278.32), yielding observed net 2774.27. Commission under-collected by 61.85.",
      "impact_brl": "-61.85"
    },
    {
      "order_id": "MLB-130107",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics premium listing: contractual commission is 16% of gross (expected fee -152.94 on gross 955.86 -> expected net 781.02). Settlement row ST-1300117 applied only 14% (-133.82), yielding observed net 800.14. Commission under-collected by 19.12.",
      "impact_brl": "-19.12"
    },
    {
      "order_id": "MLB-130013",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics premium listing: contractual commission is 16% of gross (expected fee -126.75 on gross 792.20 -> expected net 625.55). Settlement row ST-1300013 applied only 14% (-110.91), yielding observed net 641.39. Commission under-collected by 15.84.",
      "impact_brl": "-15.84"
    },
    {
      "order_id": "MLB-130132",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics classic listing: contractual commission is 11% of gross (expected fee -61.54 on gross 559.44 -> expected net 476.00). Settlement row ST-1300141 applied only 9% (-50.35), yielding observed
... (truncated for readability; full data in the .jsonl)
```

Result:
```json
{
  "accepted": true,
  "count": 20
}
```

## Final outcome

- Findings submitted: **20**
- API calls: 16
- Tokens: input=32, output=25,564, cache_read=356,271, cache_write=58,455

Findings:
```json
[
  {
    "order_id": "MLB-130009",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics premium listing: contractual commission is 16% of gross (expected fee -1081.85 on gross 6761.55 -> expected net 5639.80). Settlement row ST-1300009 applied only 14% (-946.62), yielding observed net 5775.03. Commission under-collected by 135.23.",
    "impact_brl": "-135.23"
  },
  {
    "order_id": "MLB-130083",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics classic listing: contractual commission is 11% of gross (expected fee -664.35 on gross 6039.57 -> expected net 5335.32). Settlement row ST-1300089 applied only 9% (-543.56), yielding observed net 5456.11. Commission under-collected by 120.79.",
    "impact_brl": "-120.79"
  },
  {
    "order_id": "MLB-130014",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics premium listing: contractual commission is 16% of gross (expected fee -631.90 on gross 3949.40 -> expected net 3277.60). Settlement row ST-1300014 applied only 14% (-552.92), yielding observed net 3356.58. Commission under-collected by 78.98.",
    "impact_brl": "-78.98"
  },
  {
    "order_id": "MLB-130115",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics classic listing: contractual commission is 11% of gross (expected fee -384.76 on gross 3497.78 -> expected net 3073.12). Settlement row ST-1300126 applied only 9% (-314.80), yielding observed net 3143.08. Commission under-collected by 69.96.",
    "impact_brl": "-69.96"
  },
  {
    "order_id": "MLB-130010",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics classic listing: contractual commission is 11% of gross (expected fee -340.17 on gross 3092.49 -> expected net 2712.42). Settlement row ST-1300010 applied only 9% (-278.32), yielding observed net 2774.27. Commission under-collected by 61.85.",
    "impact_brl": "-61.85"
  },
  {
    "order_id": "MLB-130107",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics premium listing: contractual commission is 16% of gross (expected fee -152.94 on gross 955.86 -> expected net 781.02). Settlement row ST-1300117 applied only 14% (-133.82), yielding observed net 800.14. Commission under-collected by 19.12.",
    "impact_brl": "-19.12"
  },
  {
    "order_id": "MLB-130013",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics premium listing: contractual commission is 16% of gross (expected fee -126.75 on gross 792.20 -> expected net 625.55). Settlement row ST-1300013 applied only 14% (-110.91), yielding observed net 641.39. Commission under-collected by 15.84.",
    "impact_brl": "-15.84"
  },
  {
    "order_id": "MLB-130132",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics classic listing: contractual commission is 11% of gross (expected fee -61.54 on gross 559.44 -> expected net 476.00). Settlement row ST-1300141 applied only 9% (-50.35), yielding observed net 487.19. Commission under-collected by 11.19.",
    "impact_brl": "-11.19"
  },
  {
    "order_id": "MLB
... (truncated for readability; full data in the .jsonl)
```
