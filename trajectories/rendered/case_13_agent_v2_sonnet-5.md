# Trajectory: case_13 - agent v2

- **Model:** `claude-sonnet-5`
- **Source:** `case_13_agent_v2_sonnet-5.jsonl`

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
STANDARD contract only. A notice cuts BOTH ways: orders the scan flags may
be legitimate under the notice, and orders the scan does NOT flag may still
be wrong under it (the scan can only see the standard rules). Re-derive the
expectation yourself for EVERY order the notice covers, in both directions,
before submitting.
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

### Step 3: `get_notices`

Input:
```json
{}
```

Result:
```json
{
  "notices_markdown": "# Marketplace seller notices - July 2026\n\n**Notice 2026-07-05 - July Tech Promo.** Electronics orders PLACED between\n2026-07-08 and 2026-07-18 (inclusive, by order_date) receive a 2.0 percentage\npoint commission discount: classic 11% -> 9%, premium 16% -> 14%. The\ndiscount is applied automatically on your settlement statement. All other\ncharges (low-ticket fixed fee, seller shipping, refund and chargeback\ntreatment) are unchanged.\n"
}
```

### Step 4: `scan_mismatches`

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

### Step 5: `get_order`

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

### Step 6: `get_order`

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

### Step 7: `get_order`

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

### Step 8: `get_order`

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

### Step 9: `get_order`

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

### Step 10: `get_order`

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

### Step 11: `get_order`

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

### Step 12: `get_order`

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

### Step 13: `get_order`

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

### Step 14: `get_order`

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

### Step 15: `get_order`

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

### Step 16: `get_order`

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

### Step 17: `get_order`

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

### Step 18: `get_order`

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

### Step 19: `get_order`

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

### Step 20: `get_order`

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

### Step 21: `get_order`

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

### Step 22: `get_order`

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

### Step 23: `get_order`

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

### Step 24: `get_order`

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

### Step 25: `calc_expected`

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

### Step 26: `get_order_settlements`

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

### Step 27: `calc_expected`

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

### Step 28: `get_order_settlements`

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

### Step 29: `list_orders`

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

### Step 30: `list_orders`

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

### Step 31: `list_orders`

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

### Step 32: `list_orders`

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

### Step 33: `list_orders`

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

### Step 34: `list_orders`

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

### Step 35: `get_order_settlements`

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

### Step 36: `get_order_settlements`

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

### Step 37: `get_order_settlements`

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

### Step 38: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130044"
}
```

Result:
```json
{
  "order_id": "MLB-130044",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 39: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130045"
}
```

Result:
```json
{
  "order_id": "MLB-130045",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 40: `get_order_settlements`

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

### Step 41: `get_order_settlements`

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

### Step 42: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130129"
}
```

Result:
```json
{
  "order_id": "MLB-130129",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 43: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130143"
}
```

Result:
```json
{
  "order_id": "MLB-130143",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 44: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-130072"
}
```

Result:
```json
{
  "order_id": "MLB-130072",
  "rows": [
    {
      "sid": "ST-1300076",
      "oid": "MLB-130072",
      "date": "2026-07-26",
      "type": "payment",
      "gross": "6057.99",
      "fee": "-1029.86",
      "ship": "-21.90",
      "net": "5006.23"
    },
    {
      "sid": "ST-1300077",
      "oid": "MLB-130072",
      "date": "2026-08-07",
      "type": "chargeback",
      "gross": "-6057.99",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-6057.99"
    }
  ],
  "sums": {
    "gross": "0.00",
    "fee": "-1029.86",
    "ship": "-21.90",
    "net": "-1051.76"
  }
}
```

### Step 45: `calc_expected`

Input:
```json
{
  "order_id": "MLB-130072"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-130072",
    "date": "2026-07-23",
    "status": "chargeback",
    "cat": "toys",
    "listing": "premium",
    "weight": "standard",
    "unit": "2019.33",
    "qty": 3,
    "gross": "6057.99",
    "inst": 6,
    "refund": "0.00"
  },
  "commission_rate_pct": 17.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "6057.99",
      "fee": "-1029.86",
      "ship": "-21.90",
      "net": "5006.23"
    },
    {
      "type": "chargeback",
      "gross": "-6057.99",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-6057.99"
    }
  ],
  "expected_net_total": "-1051.76",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 46: `submit_findings`

Input:
```json
{
  "findings": [
    {
      "order_id": "MLB-130012",
      "type": "FEE_OVERCHARGE",
      "explanation": "Order placed 2026-07-17, electronics/premium, within the July Tech Promo window (2026-07-08 to 2026-07-18) which discounts premium electronics commission from 16% to 14%. Settlement charged commission of 67.89 (16% of gross 424.29), but the correct promo commission is 59.40 (14% of 424.29). Shipping (39.90, heavy) was correct. Expected net = 424.29 - 59.40 - 39.90 = 324.99, but observed net = 316.50, a shortfall of 8.49.",
      "impact_brl": "8.49"
    },
    {
      "order_id": "MLB-130052",
      "type": "REFUND_AMOUNT_MISMATCH",
      "explanation": "Partial refund of 3.59 on gross 17.93 (fashion, not covered by any promo). Per the refund rule, the marketplace_fee on the refund row must return round_half_up(total_fee_on_payment * refund%) = round_half_up(8.58 * (3.59/17.93)) = 1.72. The observed refund row shows fee=0.00, i.e. the commission was never returned to the seller. Expected order net total = 9.35 (payment) - 1.87 (refund) = 7.48; observed = 9.35 - 3.59 = 5.76, a shortfall of 1.72.",
      "impact_brl": "1.72"
    }
  ]
}
```

Result:
```json
{
  "accepted": true,
  "count": 2
}
```

## Final outcome

- Findings submitted: **2**
- API calls: 9
- Tokens: input=18, output=16,150, cache_read=134,409, cache_write=37,132

Findings:
```json
[
  {
    "order_id": "MLB-130012",
    "type": "FEE_OVERCHARGE",
    "explanation": "Order placed 2026-07-17, electronics/premium, within the July Tech Promo window (2026-07-08 to 2026-07-18) which discounts premium electronics commission from 16% to 14%. Settlement charged commission of 67.89 (16% of gross 424.29), but the correct promo commission is 59.40 (14% of 424.29). Shipping (39.90, heavy) was correct. Expected net = 424.29 - 59.40 - 39.90 = 324.99, but observed net = 316.50, a shortfall of 8.49.",
    "impact_brl": "8.49"
  },
  {
    "order_id": "MLB-130052",
    "type": "REFUND_AMOUNT_MISMATCH",
    "explanation": "Partial refund of 3.59 on gross 17.93 (fashion, not covered by any promo). Per the refund rule, the marketplace_fee on the refund row must return round_half_up(total_fee_on_payment * refund%) = round_half_up(8.58 * (3.59/17.93)) = 1.72. The observed refund row shows fee=0.00, i.e. the commission was never returned to the seller. Expected order net total = 9.35 (payment) - 1.87 (refund) = 7.48; observed = 9.35 - 3.59 = 5.76, a shortfall of 1.72.",
    "impact_brl": "1.72"
  }
]
```
