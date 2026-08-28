# Trajectory: case_04 - agent v2

- **Model:** `claude-sonnet-5`
- **Source:** `case_04_agent_v2_sonnet-5.jsonl`

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

### Step 12: `list_orders`

Input:
```json
{
  "status": "cancelled"
}
```

Result:
```json
{
  "total_matching": 3,
  "offset": 0,
  "returned": 3,
  "has_more": false,
  "orders": [
    {
      "id": "MLB-040004",
      "date": "2026-07-02",
      "status": "cancelled",
      "cat": "fashion",
      "listing": "premium",
      "weight": "standard",
      "unit": "1118.10",
      "qty": 1,
      "gross": "1118.10",
      "inst": 12,
      "refund": "0.00"
    },
    {
      "id": "MLB-040029",
      "date": "2026-07-21",
      "status": "cancelled",
      "cat": "toys",
      "listing": "classic",
      "weight": "standard",
      "unit": "90.56",
      "qty": 2,
      "gross": "181.12",
      "inst": 3,
      "refund": "0.00"
    },
    {
      "id": "MLB-040056",
      "date": "2026-07-13",
      "status": "cancelled",
      "cat": "electronics",
      "listing": "premium",
      "weight": "standard",
      "unit": "316.79",
      "qty": 3,
      "gross": "950.37",
      "inst": 1,
      "refund": "0.00"
    }
  ]
}
```

### Step 13: `list_orders`

Input:
```json
{
  "status": "refunded"
}
```

Result:
```json
{
  "total_matching": 4,
  "offset": 0,
  "returned": 4,
  "has_more": false,
  "orders": [
    {
      "id": "MLB-040017",
      "date": "2026-07-06",
      "status": "refunded",
      "cat": "home",
      "listing": "premium",
      "weight": "standard",
      "unit": "31.86",
      "qty": 1,
      "gross": "31.86",
      "inst": 1,
      "refund": "31.86"
    },
    {
      "id": "MLB-040025",
      "date": "2026-07-05",
      "status": "refunded",
      "cat": "fashion",
      "listing": "premium",
      "weight": "standard",
      "unit": "34.82",
      "qty": 1,
      "gross": "34.82",
      "inst": 1,
      "refund": "34.82"
    },
    {
      "id": "MLB-040032",
      "date": "2026-07-01",
      "status": "refunded",
      "cat": "toys",
      "listing": "classic",
      "weight": "standard",
      "unit": "957.62",
      "qty": 2,
      "gross": "1915.24",
      "inst": 3,
      "refund": "1915.24"
    },
    {
      "id": "MLB-040059",
      "date": "2026-07-12",
      "status": "refunded",
      "cat": "electronics",
      "listing": "classic",
      "weight": "standard",
      "unit": "22.03",
      "qty": 1,
      "gross": "22.03",
      "inst": 1,
      "refund": "22.03"
    }
  ]
}
```

### Step 14: `list_orders`

Input:
```json
{
  "status": "partially_refunded"
}
```

Result:
```json
{
  "total_matching": 3,
  "offset": 0,
  "returned": 3,
  "has_more": false,
  "orders": [
    {
      "id": "MLB-040014",
      "date": "2026-07-14",
      "status": "partially_refunded",
      "cat": "fashion",
      "listing": "classic",
      "weight": "standard",
      "unit": "1971.84",
      "qty": 1,
      "gross": "1971.84",
      "inst": 3,
      "refund": "788.74"
    },
    {
      "id": "MLB-040019",
      "date": "2026-07-07",
      "status": "partially_refunded",
      "cat": "home",
      "listing": "premium",
      "weight": "heavy",
      "unit": "2455.66",
      "qty": 1,
      "gross": "2455.66",
      "inst": 3,
      "refund": "1718.96"
    },
    {
      "id": "MLB-040043",
      "date": "2026-07-23",
      "status": "partially_refunded",
      "cat": "electronics",
      "listing": "classic",
      "weight": "heavy",
      "unit": "904.28",
      "qty": 3,
      "gross": "2712.84",
      "inst": 1,
      "refund": "542.57"
    }
  ]
}
```

### Step 15: `list_orders`

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
      "id": "MLB-040021",
      "date": "2026-07-14",
      "status": "chargeback",
      "cat": "electronics",
      "listing": "classic",
      "weight": "heavy",
      "unit": "431.01",
      "qty": 1,
      "gross": "431.01",
      "inst": 1,
      "refund": "0.00"
    }
  ]
}
```

### Step 16: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040004"
}
```

Result:
```json
{
  "order_id": "MLB-040004",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 17: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040029"
}
```

Result:
```json
{
  "order_id": "MLB-040029",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 18: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040056"
}
```

Result:
```json
{
  "order_id": "MLB-040056",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 19: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040017"
}
```

Result:
```json
{
  "order_id": "MLB-040017",
  "rows": [
    {
      "sid": "ST-0400017",
      "oid": "MLB-040017",
      "date": "2026-07-09",
      "type": "payment",
      "gross": "31.86",
      "fee": "-11.67",
      "ship": "0.00",
      "net": "20.19"
    },
    {
      "sid": "ST-0400018",
      "oid": "MLB-040017",
      "date": "2026-07-16",
      "type": "refund",
      "gross": "-31.86",
      "fee": "11.67",
      "ship": "0.00",
      "net": "-20.19"
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

### Step 20: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040025"
}
```

Result:
```json
{
  "order_id": "MLB-040025",
  "rows": [
    {
      "sid": "ST-0400028",
      "oid": "MLB-040025",
      "date": "2026-07-08",
      "type": "payment",
      "gross": "34.82",
      "fee": "-12.52",
      "ship": "0.00",
      "net": "22.30"
    },
    {
      "sid": "ST-0400029",
      "oid": "MLB-040025",
      "date": "2026-07-15",
      "type": "refund",
      "gross": "-34.82",
      "fee": "12.52",
      "ship": "0.00",
      "net": "-22.30"
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

### Step 21: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040032"
}
```

Result:
```json
{
  "order_id": "MLB-040032",
  "rows": [
    {
      "sid": "ST-0400036",
      "oid": "MLB-040032",
      "date": "2026-07-04",
      "type": "payment",
      "gross": "1915.24",
      "fee": "-229.83",
      "ship": "-21.90",
      "net": "1663.51"
    },
    {
      "sid": "ST-0400037",
      "oid": "MLB-040032",
      "date": "2026-07-11",
      "type": "refund",
      "gross": "-1915.24",
      "fee": "229.83",
      "ship": "0.00",
      "net": "-1685.41"
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

### Step 22: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040059"
}
```

Result:
```json
{
  "order_id": "MLB-040059",
  "rows": [
    {
      "sid": "ST-0400065",
      "oid": "MLB-040059",
      "date": "2026-07-15",
      "type": "payment",
      "gross": "22.03",
      "fee": "-8.67",
      "ship": "0.00",
      "net": "13.36"
    },
    {
      "sid": "ST-0400066",
      "oid": "MLB-040059",
      "date": "2026-07-22",
      "type": "refund",
      "gross": "-22.03",
      "fee": "8.67",
      "ship": "0.00",
      "net": "-13.36"
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

### Step 23: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040014"
}
```

Result:
```json
{
  "order_id": "MLB-040014",
  "rows": [
    {
      "sid": "ST-0400013",
      "oid": "MLB-040014",
      "date": "2026-07-17",
      "type": "payment",
      "gross": "1971.84",
      "fee": "-256.34",
      "ship": "-21.90",
      "net": "1693.60"
    },
    {
      "sid": "ST-0400014",
      "oid": "MLB-040014",
      "date": "2026-07-24",
      "type": "refund",
      "gross": "-788.74",
      "fee": "102.54",
      "ship": "0.00",
      "net": "-686.20"
    }
  ],
  "sums": {
    "gross": "1183.10",
    "fee": "-153.80",
    "ship": "-21.90",
    "net": "1007.40"
  }
}
```

### Step 24: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040019"
}
```

Result:
```json
{
  "order_id": "MLB-040019",
  "rows": [
    {
      "sid": "ST-0400020",
      "oid": "MLB-040019",
      "date": "2026-07-10",
      "type": "payment",
      "gross": "2455.66",
      "fee": "-417.46",
      "ship": "-39.90",
      "net": "1998.30"
    },
    {
      "sid": "ST-0400021",
      "oid": "MLB-040019",
      "date": "2026-07-17",
      "type": "refund",
      "gross": "-1718.96",
      "fee": "292.22",
      "ship": "0.00",
      "net": "-1426.74"
    }
  ],
  "sums": {
    "gross": "736.70",
    "fee": "-125.24",
    "ship": "-39.90",
    "net": "571.56"
  }
}
```

### Step 25: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040043"
}
```

Result:
```json
{
  "order_id": "MLB-040043",
  "rows": [
    {
      "sid": "ST-0400048",
      "oid": "MLB-040043",
      "date": "2026-07-26",
      "type": "payment",
      "gross": "2712.84",
      "fee": "-298.41",
      "ship": "-39.90",
      "net": "2374.53"
    },
    {
      "sid": "ST-0400049",
      "oid": "MLB-040043",
      "date": "2026-08-02",
      "type": "refund",
      "gross": "-542.57",
      "fee": "59.68",
      "ship": "0.00",
      "net": "-482.89"
    }
  ],
  "sums": {
    "gross": "2170.27",
    "fee": "-238.73",
    "ship": "-39.90",
    "net": "1891.64"
  }
}
```

### Step 26: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-040021"
}
```

Result:
```json
{
  "order_id": "MLB-040021",
  "rows": [
    {
      "sid": "ST-0400023",
      "oid": "MLB-040021",
      "date": "2026-07-17",
      "type": "payment",
      "gross": "431.01",
      "fee": "-47.41",
      "ship": "-39.90",
      "net": "343.70"
    },
    {
      "sid": "ST-0400024",
      "oid": "MLB-040021",
      "date": "2026-07-29",
      "type": "chargeback",
      "gross": "-431.01",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-431.01"
    }
  ],
  "sums": {
    "gross": "0.00",
    "fee": "-47.41",
    "ship": "-39.90",
    "net": "-87.31"
  }
}
```

### Step 27: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040017"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040017",
    "date": "2026-07-06",
    "status": "refunded",
    "cat": "home",
    "listing": "premium",
    "weight": "standard",
    "unit": "31.86",
    "qty": 1,
    "gross": "31.86",
    "inst": 1,
    "refund": "31.86"
  },
  "commission_rate_pct": 17.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "31.86",
      "fee": "-11.67",
      "ship": "0.00",
      "net": "20.19"
    },
    {
      "type": "refund",
      "gross": "-31.86",
      "fee": "11.67",
      "ship": "0.00",
      "net": "-20.19"
    }
  ],
  "expected_net_total": "0.00",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 28: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040025"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040025",
    "date": "2026-07-05",
    "status": "refunded",
    "cat": "fashion",
    "listing": "premium",
    "weight": "standard",
    "unit": "34.82",
    "qty": 1,
    "gross": "34.82",
    "inst": 1,
    "refund": "34.82"
  },
  "commission_rate_pct": 18.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "34.82",
      "fee": "-12.52",
      "ship": "0.00",
      "net": "22.30"
    },
    {
      "type": "refund",
      "gross": "-34.82",
      "fee": "12.52",
      "ship": "0.00",
      "net": "-22.30"
    }
  ],
  "expected_net_total": "0.00",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 29: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040032"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040032",
    "date": "2026-07-01",
    "status": "refunded",
    "cat": "toys",
    "listing": "classic",
    "weight": "standard",
    "unit": "957.62",
    "qty": 2,
    "gross": "1915.24",
    "inst": 3,
    "refund": "1915.24"
  },
  "commission_rate_pct": 12.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "1915.24",
      "fee": "-229.83",
      "ship": "-21.90",
      "net": "1663.51"
    },
    {
      "type": "refund",
      "gross": "-1915.24",
      "fee": "229.83",
      "ship": "0.00",
      "net": "-1685.41"
    }
  ],
  "expected_net_total": "-21.90",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 30: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040059"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040059",
    "date": "2026-07-12",
    "status": "refunded",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "22.03",
    "qty": 1,
    "gross": "22.03",
    "inst": 1,
    "refund": "22.03"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "22.03",
      "fee": "-8.67",
      "ship": "0.00",
      "net": "13.36"
    },
    {
      "type": "refund",
      "gross": "-22.03",
      "fee": "8.67",
      "ship": "0.00",
      "net": "-13.36"
    }
  ],
  "expected_net_total": "0.00",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 31: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040014"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040014",
    "date": "2026-07-14",
    "status": "partially_refunded",
    "cat": "fashion",
    "listing": "classic",
    "weight": "standard",
    "unit": "1971.84",
    "qty": 1,
    "gross": "1971.84",
    "inst": 3,
    "refund": "788.74"
  },
  "commission_rate_pct": 13.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "1971.84",
      "fee": "-256.34",
      "ship": "-21.90",
      "net": "1693.60"
    },
    {
      "type": "refund",
      "gross": "-788.74",
      "fee": "102.54",
      "ship": "0.00",
      "net": "-686.20"
    }
  ],
  "expected_net_total": "1007.40",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 32: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040019"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040019",
    "date": "2026-07-07",
    "status": "partially_refunded",
    "cat": "home",
    "listing": "premium",
    "weight": "heavy",
    "unit": "2455.66",
    "qty": 1,
    "gross": "2455.66",
    "inst": 3,
    "refund": "1718.96"
  },
  "commission_rate_pct": 17.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "2455.66",
      "fee": "-417.46",
      "ship": "-39.90",
      "net": "1998.30"
    },
    {
      "type": "refund",
      "gross": "-1718.96",
      "fee": "292.22",
      "ship": "0.00",
      "net": "-1426.74"
    }
  ],
  "expected_net_total": "571.56",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 33: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040043"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040043",
    "date": "2026-07-23",
    "status": "partially_refunded",
    "cat": "electronics",
    "listing": "classic",
    "weight": "heavy",
    "unit": "904.28",
    "qty": 3,
    "gross": "2712.84",
    "inst": 1,
    "refund": "542.57"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "2712.84",
      "fee": "-298.41",
      "ship": "-39.90",
      "net": "2374.53"
    },
    {
      "type": "refund",
      "gross": "-542.57",
      "fee": "59.68",
      "ship": "0.00",
      "net": "-482.89"
    }
  ],
  "expected_net_total": "1891.64",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 34: `calc_expected`

Input:
```json
{
  "order_id": "MLB-040021"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-040021",
    "date": "2026-07-14",
    "status": "chargeback",
    "cat": "electronics",
    "listing": "classic",
    "weight": "heavy",
    "unit": "431.01",
    "qty": 1,
    "gross": "431.01",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "431.01",
      "fee": "-47.41",
      "ship": "-39.90",
      "net": "343.70"
    },
    {
      "type": "chargeback",
      "gross": "-431.01",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-431.01"
    }
  ],
  "expected_net_total": "-87.31",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 35: `submit_findings`

Input:
```json
{
  "findings": [
    {
      "order_id": "MLB-049648",
      "type": "ORPHAN_SETTLEMENT",
      "explanation": "Settlement row ST-0400068 (payment, gross=214.15, fee=-27.84, net=186.31) references order MLB-049648, which does not exist anywhere in the seller's order book. There is no corresponding order to justify this payout, so it is an orphan settlement row with no expected counterpart (expected net = 0.00 vs observed net = 186.31).",
      "impact_brl": "-186.31"
    },
    {
      "order_id": "MLB-040050",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order MLB-040050 is weight_class 'heavy', so per the fee rules the seller shipping deduction should be 39.90 (expected net = 3043.08 - 517.32 - 39.90 = 2485.86). The settlement row ST-0400057 instead deducted 61.80 in shipping (net = 2463.96), which equals 21.90 + 39.90 - i.e. both the standard and heavy shipping rates were charged. This overcharged the seller by 21.90 (2485.86 - 2463.96 = 21.90).",
      "impact_brl": "21.90"
    },
    {
      "order_id": "MLB-040060",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order MLB-040060 is weight_class 'standard', so the correct seller shipping deduction is 21.90 (expected net = 882.88 - 88.29 - 21.90 = 772.69). The settlement row ST-0400067 deducted 39.90 (the 'heavy' rate) instead, giving net = 754.69, an overcharge of 18.00 (772.69 - 754.69 = 18.00).",
      "impact_brl": "18.00"
    }
  ]
}
```

Result:
```json
{
  "accepted": true,
  "count": 3
}
```

## Final outcome

- Findings submitted: **3**
- API calls: 7
- Tokens: input=14, output=6,054, cache_read=38,649, cache_write=12,565

Findings:
```json
[
  {
    "order_id": "MLB-049648",
    "type": "ORPHAN_SETTLEMENT",
    "explanation": "Settlement row ST-0400068 (payment, gross=214.15, fee=-27.84, net=186.31) references order MLB-049648, which does not exist anywhere in the seller's order book. There is no corresponding order to justify this payout, so it is an orphan settlement row with no expected counterpart (expected net = 0.00 vs observed net = 186.31).",
    "impact_brl": "-186.31"
  },
  {
    "order_id": "MLB-040050",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order MLB-040050 is weight_class 'heavy', so per the fee rules the seller shipping deduction should be 39.90 (expected net = 3043.08 - 517.32 - 39.90 = 2485.86). The settlement row ST-0400057 instead deducted 61.80 in shipping (net = 2463.96), which equals 21.90 + 39.90 - i.e. both the standard and heavy shipping rates were charged. This overcharged the seller by 21.90 (2485.86 - 2463.96 = 21.90).",
    "impact_brl": "21.90"
  },
  {
    "order_id": "MLB-040060",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order MLB-040060 is weight_class 'standard', so the correct seller shipping deduction is 21.90 (expected net = 882.88 - 88.29 - 21.90 = 772.69). The settlement row ST-0400067 deducted 39.90 (the 'heavy' rate) instead, giving net = 754.69, an overcharge of 18.00 (772.69 - 754.69 = 18.00).",
    "impact_brl": "18.00"
  }
]
```
