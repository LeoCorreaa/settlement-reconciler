# Trajectory: case_12 - agent v2

- **Model:** `claude-sonnet-5`
- **Source:** `case_12_agent_v2_sonnet-5.jsonl`

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
    "total": 400,
    "by_status": {
      "paid": 172,
      "delivered": 161,
      "refunded": 26,
      "cancelled": 20,
      "partially_refunded": 20,
      "chargeback": 1
    }
  },
  "settlement_rows": {
    "total": 460,
    "by_type": {
      "payment": 414,
      "refund": 45,
      "chargeback": 1
    }
  },
  "order_dates": {
    "first": "2026-07-01",
    "last": "2026-07-28"
  },
  "gross_total": "335544.43",
  "settlement_net_total": "236276.14"
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
      "order_id": "MLB-120328",
      "status": "paid",
      "issue": "no_rows",
      "expected_net": "1264.67",
      "observed_net": "0.00",
      "delta": "-1264.67",
      "rows_observed": 0
    },
    {
      "order_id": "MLB-129910",
      "status": "NOT_IN_ORDER_BOOK",
      "issue": "orphan_rows",
      "expected_net": "0.00",
      "observed_net": "395.02",
      "delta": "395.02",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-120052",
      "status": "partially_refunded",
      "issue": "net_delta",
      "expected_net": "4270.90",
      "observed_net": "4110.54",
      "delta": "-160.36",
      "rows_observed": 3
    },
    {
      "order_id": "MLB-120224",
      "status": "cancelled",
      "issue": "unexpected_rows",
      "expected_net": "0.00",
      "observed_net": "153.01",
      "delta": "153.01",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-120103",
      "status": "refunded",
      "issue": "net_delta",
      "expected_net": "-21.90",
      "observed_net": "114.66",
      "delta": "136.56",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-120048",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "59.61",
      "observed_net": "119.22",
      "delta": "59.61",
      "rows_observed": 2
    },
    {
      "order_id": "MLB-120115",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "321.10",
      "observed_net": "303.10",
      "delta": "-18.00",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-120185",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "492.43",
      "observed_net": "474.43",
      "delta": "-18.00",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-120125",
      "status": "refunded",
      "issue": "net_delta",
      "expected_net": "-21.90",
      "observed_net": "-35.39",
      "delta": "-13.49",
      "rows_observed": 2
    },
    {
      "order_id": "MLB-120264",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "532.65",
      "observed_net": "523.07",
      "delta": "-9.58",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-120236",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "287.33",
      "observed_net": "280.05",
      "delta": "-7.28",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-120018",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "1765.84",
      "observed_net": "1765.47",
      "delta": "-0.37",
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
  "order_id": "MLB-120328"
}
```

Result:
```json
{
  "id": "MLB-120328",
  "date": "2026-07-28",
  "status": "paid",
  "cat": "home",
  "listing": "classic",
  "weight": "heavy",
  "unit": "1482.47",
  "qty": 1,
  "gross": "1482.47",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 5: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120328"
}
```

Result:
```json
{
  "order_id": "MLB-120328",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 6: `get_order`

Input:
```json
{
  "order_id": "MLB-129910"
}
```

Result:
```json
{
  "error": "order MLB-129910 not found in the seller's book"
}
```

### Step 7: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-129910"
}
```

Result:
```json
{
  "order_id": "MLB-129910",
  "rows": [
    {
      "sid": "ST-1200461",
      "oid": "MLB-129910",
      "date": "2026-07-06",
      "type": "payment",
      "gross": "454.05",
      "fee": "-59.03",
      "ship": "0.00",
      "net": "395.02"
    }
  ],
  "sums": {
    "gross": "454.05",
    "fee": "-59.03",
    "ship": "0.00",
    "net": "395.02"
  }
}
```

### Step 8: `get_order`

Input:
```json
{
  "order_id": "MLB-120052"
}
```

Result:
```json
{
  "id": "MLB-120052",
  "date": "2026-07-17",
  "status": "partially_refunded",
  "cat": "fashion",
  "listing": "classic",
  "weight": "standard",
  "unit": "2055.94",
  "qty": 3,
  "gross": "6167.82",
  "inst": 1,
  "refund": "1233.56"
}
```

### Step 9: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120052"
}
```

Result:
```json
{
  "order_id": "MLB-120052",
  "rows": [
    {
      "sid": "ST-1200060",
      "oid": "MLB-120052",
      "date": "2026-07-20",
      "type": "payment",
      "gross": "3700.69",
      "fee": "-801.82",
      "ship": "-21.90",
      "net": "2876.97"
    },
    {
      "sid": "ST-1200061",
      "oid": "MLB-120052",
      "date": "2026-07-27",
      "type": "payment",
      "gross": "2467.13",
      "fee": "0.00",
      "ship": "0.00",
      "net": "2467.13"
    },
    {
      "sid": "ST-1200062",
      "oid": "MLB-120052",
      "date": "2026-07-27",
      "type": "refund",
      "gross": "-1233.56",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-1233.56"
    }
  ],
  "sums": {
    "gross": "4934.26",
    "fee": "-801.82",
    "ship": "-21.90",
    "net": "4110.54"
  }
}
```

### Step 10: `get_order`

Input:
```json
{
  "order_id": "MLB-120224"
}
```

Result:
```json
{
  "id": "MLB-120224",
  "date": "2026-07-06",
  "status": "cancelled",
  "cat": "electronics",
  "listing": "classic",
  "weight": "standard",
  "unit": "72.53",
  "qty": 3,
  "gross": "217.59",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 11: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120224"
}
```

Result:
```json
{
  "order_id": "MLB-120224",
  "rows": [
    {
      "sid": "ST-1200462",
      "oid": "MLB-120224",
      "date": "2026-07-09",
      "type": "payment",
      "gross": "217.59",
      "fee": "-42.68",
      "ship": "-21.90",
      "net": "153.01"
    }
  ],
  "sums": {
    "gross": "217.59",
    "fee": "-42.68",
    "ship": "-21.90",
    "net": "153.01"
  }
}
```

### Step 12: `get_order`

Input:
```json
{
  "order_id": "MLB-120103"
}
```

Result:
```json
{
  "id": "MLB-120103",
  "date": "2026-07-24",
  "status": "refunded",
  "cat": "books",
  "listing": "classic",
  "weight": "standard",
  "unit": "151.73",
  "qty": 1,
  "gross": "151.73",
  "inst": 3,
  "refund": "151.73"
}
```

### Step 13: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120103"
}
```

Result:
```json
{
  "order_id": "MLB-120103",
  "rows": [
    {
      "sid": "ST-1200122",
      "oid": "MLB-120103",
      "date": "2026-07-27",
      "type": "payment",
      "gross": "151.73",
      "fee": "-15.17",
      "ship": "-21.90",
      "net": "114.66"
    }
  ],
  "sums": {
    "gross": "151.73",
    "fee": "-15.17",
    "ship": "-21.90",
    "net": "114.66"
  }
}
```

### Step 14: `get_order`

Input:
```json
{
  "order_id": "MLB-120048"
}
```

Result:
```json
{
  "id": "MLB-120048",
  "date": "2026-07-19",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "standard",
  "unit": "78.41",
  "qty": 1,
  "gross": "78.41",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 15: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120048"
}
```

Result:
```json
{
  "order_id": "MLB-120048",
  "rows": [
    {
      "sid": "ST-1200056",
      "oid": "MLB-120048",
      "date": "2026-07-22",
      "type": "payment",
      "gross": "78.41",
      "fee": "-18.80",
      "ship": "0.00",
      "net": "59.61"
    },
    {
      "sid": "ST-1200460",
      "oid": "MLB-120048",
      "date": "2026-07-23",
      "type": "payment",
      "gross": "78.41",
      "fee": "-18.80",
      "ship": "0.00",
      "net": "59.61"
    }
  ],
  "sums": {
    "gross": "156.82",
    "fee": "-37.60",
    "ship": "0.00",
    "net": "119.22"
  }
}
```

### Step 16: `get_order`

Input:
```json
{
  "order_id": "MLB-120115"
}
```

Result:
```json
{
  "id": "MLB-120115",
  "date": "2026-07-14",
  "status": "paid",
  "cat": "electronics",
  "listing": "classic",
  "weight": "standard",
  "unit": "385.39",
  "qty": 1,
  "gross": "385.39",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 17: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120115"
}
```

Result:
```json
{
  "order_id": "MLB-120115",
  "rows": [
    {
      "sid": "ST-1200136",
      "oid": "MLB-120115",
      "date": "2026-07-17",
      "type": "payment",
      "gross": "385.39",
      "fee": "-42.39",
      "ship": "-39.90",
      "net": "303.10"
    }
  ],
  "sums": {
    "gross": "385.39",
    "fee": "-42.39",
    "ship": "-39.90",
    "net": "303.10"
  }
}
```

### Step 18: `get_order`

Input:
```json
{
  "order_id": "MLB-120185"
}
```

Result:
```json
{
  "id": "MLB-120185",
  "date": "2026-07-01",
  "status": "paid",
  "cat": "fashion",
  "listing": "classic",
  "weight": "standard",
  "unit": "295.59",
  "qty": 2,
  "gross": "591.18",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 19: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120185"
}
```

Result:
```json
{
  "order_id": "MLB-120185",
  "rows": [
    {
      "sid": "ST-1200219",
      "oid": "MLB-120185",
      "date": "2026-07-04",
      "type": "payment",
      "gross": "591.18",
      "fee": "-76.85",
      "ship": "-39.90",
      "net": "474.43"
    }
  ],
  "sums": {
    "gross": "591.18",
    "fee": "-76.85",
    "ship": "-39.90",
    "net": "474.43"
  }
}
```

### Step 20: `get_order`

Input:
```json
{
  "order_id": "MLB-120125"
}
```

Result:
```json
{
  "id": "MLB-120125",
  "date": "2026-07-06",
  "status": "refunded",
  "cat": "electronics",
  "listing": "classic",
  "weight": "standard",
  "unit": "106.40",
  "qty": 1,
  "gross": "106.40",
  "inst": 1,
  "refund": "106.40"
}
```

### Step 21: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120125"
}
```

Result:
```json
{
  "order_id": "MLB-120125",
  "rows": [
    {
      "sid": "ST-1200146",
      "oid": "MLB-120125",
      "date": "2026-07-09",
      "type": "payment",
      "gross": "106.40",
      "fee": "-13.49",
      "ship": "-21.90",
      "net": "71.01"
    },
    {
      "sid": "ST-1200147",
      "oid": "MLB-120125",
      "date": "2026-07-16",
      "type": "refund",
      "gross": "-106.40",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-106.40"
    }
  ],
  "sums": {
    "gross": "0.00",
    "fee": "-13.49",
    "ship": "-21.90",
    "net": "-35.39"
  }
}
```

### Step 22: `get_order`

Input:
```json
{
  "order_id": "MLB-120264"
}
```

Result:
```json
{
  "id": "MLB-120264",
  "date": "2026-07-17",
  "status": "delivered",
  "cat": "toys",
  "listing": "classic",
  "weight": "standard",
  "unit": "630.17",
  "qty": 1,
  "gross": "630.17",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 23: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120264"
}
```

Result:
```json
{
  "order_id": "MLB-120264",
  "rows": [
    {
      "sid": "ST-1200308",
      "oid": "MLB-120264",
      "date": "2026-07-20",
      "type": "payment",
      "gross": "630.17",
      "fee": "-85.20",
      "ship": "-21.90",
      "net": "523.07"
    }
  ],
  "sums": {
    "gross": "630.17",
    "fee": "-85.20",
    "ship": "-21.90",
    "net": "523.07"
  }
}
```

### Step 24: `get_order`

Input:
```json
{
  "order_id": "MLB-120236"
}
```

Result:
```json
{
  "id": "MLB-120236",
  "date": "2026-07-20",
  "status": "paid",
  "cat": "books",
  "listing": "classic",
  "weight": "standard",
  "unit": "343.59",
  "qty": 1,
  "gross": "343.59",
  "inst": 3,
  "refund": "0.00"
}
```

### Step 25: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120236"
}
```

Result:
```json
{
  "order_id": "MLB-120236",
  "rows": [
    {
      "sid": "ST-1200277",
      "oid": "MLB-120236",
      "date": "2026-07-23",
      "type": "payment",
      "gross": "343.59",
      "fee": "-41.64",
      "ship": "-21.90",
      "net": "280.05"
    }
  ],
  "sums": {
    "gross": "343.59",
    "fee": "-41.64",
    "ship": "-21.90",
    "net": "280.05"
  }
}
```

### Step 26: `get_order`

Input:
```json
{
  "order_id": "MLB-120018"
}
```

Result:
```json
{
  "id": "MLB-120018",
  "date": "2026-07-17",
  "status": "paid",
  "cat": "toys",
  "listing": "classic",
  "weight": "standard",
  "unit": "1015.76",
  "qty": 2,
  "gross": "2031.52",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 27: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-120018"
}
```

Result:
```json
{
  "order_id": "MLB-120018",
  "rows": [
    {
      "sid": "ST-1200022",
      "oid": "MLB-120018",
      "date": "2026-07-20",
      "type": "payment",
      "gross": "2031.52",
      "fee": "-244.15",
      "ship": "-21.90",
      "net": "1765.47"
    }
  ],
  "sums": {
    "gross": "2031.52",
    "fee": "-244.15",
    "ship": "-21.90",
    "net": "1765.47"
  }
}
```

### Step 28: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120328"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120328",
    "date": "2026-07-28",
    "status": "paid",
    "cat": "home",
    "listing": "classic",
    "weight": "heavy",
    "unit": "1482.47",
    "qty": 1,
    "gross": "1482.47",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 12.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "1482.47",
      "fee": "-177.90",
      "ship": "-39.90",
      "net": "1264.67"
    }
  ],
  "expected_net_total": "1264.67",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 29: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120052"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120052",
    "date": "2026-07-17",
    "status": "partially_refunded",
    "cat": "fashion",
    "listing": "classic",
    "weight": "standard",
    "unit": "2055.94",
    "qty": 3,
    "gross": "6167.82",
    "inst": 1,
    "refund": "1233.56"
  },
  "commission_rate_pct": 13.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "6167.82",
      "fee": "-801.82",
      "ship": "-21.90",
      "net": "5344.10"
    },
    {
      "type": "refund",
      "gross": "-1233.56",
      "fee": "160.36",
      "ship": "0.00",
      "net": "-1073.20"
    }
  ],
  "expected_net_total": "4270.90",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 30: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120224"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120224",
    "date": "2026-07-06",
    "status": "cancelled",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "72.53",
    "qty": 3,
    "gross": "217.59",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [],
  "expected_net_total": "0.00",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 31: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120103"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120103",
    "date": "2026-07-24",
    "status": "refunded",
    "cat": "books",
    "listing": "classic",
    "weight": "standard",
    "unit": "151.73",
    "qty": 1,
    "gross": "151.73",
    "inst": 3,
    "refund": "151.73"
  },
  "commission_rate_pct": 10.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "151.73",
      "fee": "-15.17",
      "ship": "-21.90",
      "net": "114.66"
    },
    {
      "type": "refund",
      "gross": "-151.73",
      "fee": "15.17",
      "ship": "0.00",
      "net": "-136.56"
    }
  ],
  "expected_net_total": "-21.90",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 32: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120048"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120048",
    "date": "2026-07-19",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "standard",
    "unit": "78.41",
    "qty": 1,
    "gross": "78.41",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "78.41",
      "fee": "-18.80",
      "ship": "0.00",
      "net": "59.61"
    }
  ],
  "expected_net_total": "59.61",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 33: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120115"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120115",
    "date": "2026-07-14",
    "status": "paid",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "385.39",
    "qty": 1,
    "gross": "385.39",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "385.39",
      "fee": "-42.39",
      "ship": "-21.90",
      "net": "321.10"
    }
  ],
  "expected_net_total": "321.10",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 34: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120185"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120185",
    "date": "2026-07-01",
    "status": "paid",
    "cat": "fashion",
    "listing": "classic",
    "weight": "standard",
    "unit": "295.59",
    "qty": 2,
    "gross": "591.18",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 13.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "591.18",
      "fee": "-76.85",
      "ship": "-21.90",
      "net": "492.43"
    }
  ],
  "expected_net_total": "492.43",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 35: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120125"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120125",
    "date": "2026-07-06",
    "status": "refunded",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "106.40",
    "qty": 1,
    "gross": "106.40",
    "inst": 1,
    "refund": "106.40"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "106.40",
      "fee": "-11.70",
      "ship": "-21.90",
      "net": "72.80"
    },
    {
      "type": "refund",
      "gross": "-106.40",
      "fee": "11.70",
      "ship": "0.00",
      "net": "-94.70"
    }
  ],
  "expected_net_total": "-21.90",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 36: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120264"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120264",
    "date": "2026-07-17",
    "status": "delivered",
    "cat": "toys",
    "listing": "classic",
    "weight": "standard",
    "unit": "630.17",
    "qty": 1,
    "gross": "630.17",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 12.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "630.17",
      "fee": "-75.62",
      "ship": "-21.90",
      "net": "532.65"
    }
  ],
  "expected_net_total": "532.65",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 37: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120236"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120236",
    "date": "2026-07-20",
    "status": "paid",
    "cat": "books",
    "listing": "classic",
    "weight": "standard",
    "unit": "343.59",
    "qty": 1,
    "gross": "343.59",
    "inst": 3,
    "refund": "0.00"
  },
  "commission_rate_pct": 10.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "343.59",
      "fee": "-34.36",
      "ship": "-21.90",
      "net": "287.33"
    }
  ],
  "expected_net_total": "287.33",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 38: `calc_expected`

Input:
```json
{
  "order_id": "MLB-120018"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-120018",
    "date": "2026-07-17",
    "status": "paid",
    "cat": "toys",
    "listing": "classic",
    "weight": "standard",
    "unit": "1015.76",
    "qty": 2,
    "gross": "2031.52",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 12.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "2031.52",
      "fee": "-243.78",
      "ship": "-21.90",
      "net": "1765.84"
    }
  ],
  "expected_net_total": "1765.84",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 39: `submit_findings`

Input:
```json
{
  "findings": [
    {
      "order_id": "MLB-120328",
      "type": "MISSING_SETTLEMENT",
      "explanation": "Order is 'paid' with expected net 1264.67 (gross 1482.47, commission -177.90 at 12% home/classic, shipping -39.90 heavy) but has zero settlement rows on the statement.",
      "impact_brl": "1264.67"
    },
    {
      "order_id": "MLB-129910",
      "type": "ORPHAN_SETTLEMENT",
      "explanation": "Settlement row ST-1200461 (payment, gross 454.05, fee -59.03, net 395.02) references order MLB-129910 which does not exist anywhere in the seller's order book.",
      "impact_brl": "-395.02"
    },
    {
      "order_id": "MLB-120052",
      "type": "REFUND_AMOUNT_MISMATCH",
      "explanation": "Partial refund of 20% (1233.56 of 6167.82) should carry fee=+160.36 (20% of the 801.82 commission) per rules, giving refund net -1073.20. Observed refund row ST-1200062 has fee=0.00 and net=-1233.56, so the commission was never returned to the seller. Total order net observed 4110.54 vs expected 4270.90.",
      "impact_brl": "160.36"
    },
    {
      "order_id": "MLB-120224",
      "type": "CANCELLED_BUT_SETTLED",
      "explanation": "Order status is 'cancelled' (cancelled before payment), which per rules must have NO settlement rows. Row ST-1200462 nonetheless settled gross 217.59, fee -42.68, ship -21.90, net 153.01.",
      "impact_brl": "-153.01"
    },
    {
      "order_id": "MLB-120103",
      "type": "REFUND_NOT_SETTLED",
      "explanation": "Order status is 'refunded' (full refund of 151.73). Expected two rows: payment net 114.66 and refund net -136.56, totaling -21.90. Only the payment row (net 114.66) appears on the statement; the refund clawback row is missing entirely.",
      "impact_brl": "-136.56"
    },
    {
      "order_id": "MLB-120048",
      "type": "DUPLICATE_SETTLEMENT",
      "explanation": "Expected single payment row: gross 78.41, fee -18.80 (16% commission + 6.25 low-ticket fee), net 59.61. The identical row was settled twice (ST-1200056 and ST-1200460), doubling gross/fee/net to 156.82/-37.60/119.22.",
      "impact_brl": "-59.61"
    },
    {
      "order_id": "MLB-120115",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order weight_class is 'standard' so shipping should be -21.90, giving expected net 321.10. Settlement row ST-1200136 deducted -39.90 (the 'heavy' rate) instead, giving net 303.10.",
      "impact_brl": "18.00"
    },
    {
      "order_id": "MLB-120185",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order weight_class is 'standard' so shipping should be -21.90, giving expected net 492.43. Settlement row ST-1200219 deducted -39.90 (the 'heavy' rate) instead, giving net 474.43.",
      "impact_brl": "18.00"
    },
    {
      "order_id": "MLB-120125",
      "type": "FEE_OVERCHARGE",
      "explanation": "Electronics/classic commission on gross 106.40 should be 11% = 11.70. Payment row ST-1200146 charged fee -13.49, an overcharge of 1.79.",
      "impact_brl": "1.
... (truncated for readability; full data in the .jsonl)
```

Result:
```json
{
  "accepted": true,
  "count": 13
}
```

## Final outcome

- Findings submitted: **13**
- API calls: 5
- Tokens: input=10, output=12,722, cache_read=22,321, cache_write=14,174

Findings:
```json
[
  {
    "order_id": "MLB-120328",
    "type": "MISSING_SETTLEMENT",
    "explanation": "Order is 'paid' with expected net 1264.67 (gross 1482.47, commission -177.90 at 12% home/classic, shipping -39.90 heavy) but has zero settlement rows on the statement.",
    "impact_brl": "1264.67"
  },
  {
    "order_id": "MLB-129910",
    "type": "ORPHAN_SETTLEMENT",
    "explanation": "Settlement row ST-1200461 (payment, gross 454.05, fee -59.03, net 395.02) references order MLB-129910 which does not exist anywhere in the seller's order book.",
    "impact_brl": "-395.02"
  },
  {
    "order_id": "MLB-120052",
    "type": "REFUND_AMOUNT_MISMATCH",
    "explanation": "Partial refund of 20% (1233.56 of 6167.82) should carry fee=+160.36 (20% of the 801.82 commission) per rules, giving refund net -1073.20. Observed refund row ST-1200062 has fee=0.00 and net=-1233.56, so the commission was never returned to the seller. Total order net observed 4110.54 vs expected 4270.90.",
    "impact_brl": "160.36"
  },
  {
    "order_id": "MLB-120224",
    "type": "CANCELLED_BUT_SETTLED",
    "explanation": "Order status is 'cancelled' (cancelled before payment), which per rules must have NO settlement rows. Row ST-1200462 nonetheless settled gross 217.59, fee -42.68, ship -21.90, net 153.01.",
    "impact_brl": "-153.01"
  },
  {
    "order_id": "MLB-120103",
    "type": "REFUND_NOT_SETTLED",
    "explanation": "Order status is 'refunded' (full refund of 151.73). Expected two rows: payment net 114.66 and refund net -136.56, totaling -21.90. Only the payment row (net 114.66) appears on the statement; the refund clawback row is missing entirely.",
    "impact_brl": "-136.56"
  },
  {
    "order_id": "MLB-120048",
    "type": "DUPLICATE_SETTLEMENT",
    "explanation": "Expected single payment row: gross 78.41, fee -18.80 (16% commission + 6.25 low-ticket fee), net 59.61. The identical row was settled twice (ST-1200056 and ST-1200460), doubling gross/fee/net to 156.82/-37.60/119.22.",
    "impact_brl": "-59.61"
  },
  {
    "order_id": "MLB-120115",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order weight_class is 'standard' so shipping should be -21.90, giving expected net 321.10. Settlement row ST-1200136 deducted -39.90 (the 'heavy' rate) instead, giving net 303.10.",
    "impact_brl": "18.00"
  },
  {
    "order_id": "MLB-120185",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order weight_class is 'standard' so shipping should be -21.90, giving expected net 492.43. Settlement row ST-1200219 deducted -39.90 (the 'heavy' rate) instead, giving net 474.43.",
    "impact_brl": "18.00"
  },
  {
    "order_id": "MLB-120125",
    "type": "FEE_OVERCHARGE",
    "explanation": "Electronics/classic commission on gross 106.40 should be 11% = 11.70. Payment row ST-1200146 charged fee -13.49, an overcharge of 1.79.",
    "impact_brl": "1.79"
  },
  {
    "order_id": "MLB-120125",
    "type": "REFUND_AMOUNT_MISMATCH",
    "explanation": "Full refund on this o
... (truncated for readability; full data in the .jsonl)
```
