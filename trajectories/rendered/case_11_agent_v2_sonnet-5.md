# Trajectory: case_11 - agent v2

- **Model:** `claude-sonnet-5`
- **Source:** `case_11_agent_v2_sonnet-5.jsonl`

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
    "total": 350,
    "by_status": {
      "delivered": 165,
      "paid": 127,
      "cancelled": 17,
      "partially_refunded": 17,
      "refunded": 23,
      "chargeback": 1
    }
  },
  "settlement_rows": {
    "total": 396,
    "by_type": {
      "payment": 356,
      "refund": 39,
      "chargeback": 1
    }
  },
  "order_dates": {
    "first": "2026-07-01",
    "last": "2026-07-28"
  },
  "gross_total": "380447.94",
  "settlement_net_total": "287713.80"
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
      "order_id": "MLB-110271",
      "status": "cancelled",
      "issue": "unexpected_rows",
      "expected_net": "0.00",
      "observed_net": "1249.58",
      "delta": "1249.58",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-110089",
      "status": "paid",
      "issue": "no_rows",
      "expected_net": "692.04",
      "observed_net": "0.00",
      "delta": "-692.04",
      "rows_observed": 0
    },
    {
      "order_id": "MLB-110328",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "220.18",
      "observed_net": "440.36",
      "delta": "220.18",
      "rows_observed": 2
    },
    {
      "order_id": "MLB-110334",
      "status": "partially_refunded",
      "issue": "net_delta",
      "expected_net": "757.34",
      "observed_net": "956.65",
      "delta": "199.31",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-110166",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "1288.38",
      "observed_net": "1245.69",
      "delta": "-42.69",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-110151",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "146.88",
      "observed_net": "125.46",
      "delta": "-21.42",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-110265",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "1556.96",
      "observed_net": "1538.96",
      "delta": "-18.00",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-110100",
      "status": "partially_refunded",
      "issue": "net_delta",
      "expected_net": "64.41",
      "observed_net": "49.18",
      "delta": "-15.23",
      "rows_observed": 2
    }
  ],
  "note": "Deltas only - causes are NOT determined. Investigate each candidate before reporting."
}
```

### Step 4: `get_order`

Input:
```json
{
  "order_id": "MLB-110271"
}
```

Result:
```json
{
  "id": "MLB-110271",
  "date": "2026-07-11",
  "status": "cancelled",
  "cat": "home",
  "listing": "classic",
  "weight": "heavy",
  "unit": "488.44",
  "qty": 3,
  "gross": "1465.32",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 5: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-110271"
}
```

Result:
```json
{
  "order_id": "MLB-110271",
  "rows": [
    {
      "sid": "ST-1100398",
      "oid": "MLB-110271",
      "date": "2026-07-14",
      "type": "payment",
      "gross": "1465.32",
      "fee": "-175.84",
      "ship": "-39.90",
      "net": "1249.58"
    }
  ],
  "sums": {
    "gross": "1465.32",
    "fee": "-175.84",
    "ship": "-39.90",
    "net": "1249.58"
  }
}
```

### Step 6: `get_order`

Input:
```json
{
  "order_id": "MLB-110089"
}
```

Result:
```json
{
  "id": "MLB-110089",
  "date": "2026-07-14",
  "status": "paid",
  "cat": "toys",
  "listing": "classic",
  "weight": "standard",
  "unit": "405.65",
  "qty": 2,
  "gross": "811.30",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 7: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-110089"
}
```

Result:
```json
{
  "order_id": "MLB-110089",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 8: `get_order`

Input:
```json
{
  "order_id": "MLB-110328"
}
```

Result:
```json
{
  "id": "MLB-110328",
  "date": "2026-07-06",
  "status": "delivered",
  "cat": "electronics",
  "listing": "classic",
  "weight": "standard",
  "unit": "272.00",
  "qty": 1,
  "gross": "272.00",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 9: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-110328"
}
```

Result:
```json
{
  "order_id": "MLB-110328",
  "rows": [
    {
      "sid": "ST-1100368",
      "oid": "MLB-110328",
      "date": "2026-07-09",
      "type": "payment",
      "gross": "272.00",
      "fee": "-29.92",
      "ship": "-21.90",
      "net": "220.18"
    },
    {
      "sid": "ST-1100397",
      "oid": "MLB-110328",
      "date": "2026-07-10",
      "type": "payment",
      "gross": "272.00",
      "fee": "-29.92",
      "ship": "-21.90",
      "net": "220.18"
    }
  ],
  "sums": {
    "gross": "544.00",
    "fee": "-59.84",
    "ship": "-43.80",
    "net": "440.36"
  }
}
```

### Step 10: `calc_expected`

Input:
```json
{
  "order_id": "MLB-110328"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-110328",
    "date": "2026-07-06",
    "status": "delivered",
    "cat": "electronics",
    "listing": "classic",
    "weight": "standard",
    "unit": "272.00",
    "qty": 1,
    "gross": "272.00",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "272.00",
      "fee": "-29.92",
      "ship": "-21.90",
      "net": "220.18"
    }
  ],
  "expected_net_total": "220.18",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 11: `get_order`

Input:
```json
{
  "order_id": "MLB-110334"
}
```

Result:
```json
{
  "id": "MLB-110334",
  "date": "2026-07-25",
  "status": "partially_refunded",
  "cat": "home",
  "listing": "premium",
  "weight": "heavy",
  "unit": "400.22",
  "qty": 3,
  "gross": "1200.66",
  "inst": 10,
  "refund": "240.13"
}
```

### Step 12: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-110334"
}
```

Result:
```json
{
  "order_id": "MLB-110334",
  "rows": [
    {
      "sid": "ST-1100375",
      "oid": "MLB-110334",
      "date": "2026-07-28",
      "type": "payment",
      "gross": "1200.66",
      "fee": "-204.11",
      "ship": "-39.90",
      "net": "956.65"
    }
  ],
  "sums": {
    "gross": "1200.66",
    "fee": "-204.11",
    "ship": "-39.90",
    "net": "956.65"
  }
}
```

### Step 13: `calc_expected`

Input:
```json
{
  "order_id": "MLB-110334"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-110334",
    "date": "2026-07-25",
    "status": "partially_refunded",
    "cat": "home",
    "listing": "premium",
    "weight": "heavy",
    "unit": "400.22",
    "qty": 3,
    "gross": "1200.66",
    "inst": 10,
    "refund": "240.13"
  },
  "commission_rate_pct": 17.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "1200.66",
      "fee": "-204.11",
      "ship": "-39.90",
      "net": "956.65"
    },
    {
      "type": "refund",
      "gross": "-240.13",
      "fee": "40.82",
      "ship": "0.00",
      "net": "-199.31"
    }
  ],
  "expected_net_total": "757.34",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 14: `get_order`

Input:
```json
{
  "order_id": "MLB-110166"
}
```

Result:
```json
{
  "id": "MLB-110166",
  "date": "2026-07-11",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "heavy",
  "unit": "1581.29",
  "qty": 1,
  "gross": "1581.29",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 15: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-110166"
}
```

Result:
```json
{
  "order_id": "MLB-110166",
  "rows": [
    {
      "sid": "ST-1100185",
      "oid": "MLB-110166",
      "date": "2026-07-14",
      "type": "payment",
      "gross": "1581.29",
      "fee": "-295.70",
      "ship": "-39.90",
      "net": "1245.69"
    }
  ],
  "sums": {
    "gross": "1581.29",
    "fee": "-295.70",
    "ship": "-39.90",
    "net": "1245.69"
  }
}
```

### Step 16: `calc_expected`

Input:
```json
{
  "order_id": "MLB-110166"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-110166",
    "date": "2026-07-11",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "heavy",
    "unit": "1581.29",
    "qty": 1,
    "gross": "1581.29",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "1581.29",
      "fee": "-253.01",
      "ship": "-39.90",
      "net": "1288.38"
    }
  ],
  "expected_net_total": "1288.38",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 17: `get_order`

Input:
```json
{
  "order_id": "MLB-110151"
}
```

Result:
```json
{
  "id": "MLB-110151",
  "date": "2026-07-02",
  "status": "delivered",
  "cat": "toys",
  "listing": "premium",
  "weight": "standard",
  "unit": "203.35",
  "qty": 1,
  "gross": "203.35",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 18: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-110151"
}
```

Result:
```json
{
  "order_id": "MLB-110151",
  "rows": [
    {
      "sid": "ST-1100167",
      "oid": "MLB-110151",
      "date": "2026-07-05",
      "type": "payment",
      "gross": "203.35",
      "fee": "-37.99",
      "ship": "-39.90",
      "net": "125.46"
    }
  ],
  "sums": {
    "gross": "203.35",
    "fee": "-37.99",
    "ship": "-39.90",
    "net": "125.46"
  }
}
```

### Step 19: `calc_expected`

Input:
```json
{
  "order_id": "MLB-110151"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-110151",
    "date": "2026-07-02",
    "status": "delivered",
    "cat": "toys",
    "listing": "premium",
    "weight": "standard",
    "unit": "203.35",
    "qty": 1,
    "gross": "203.35",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 17.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "203.35",
      "fee": "-34.57",
      "ship": "-21.90",
      "net": "146.88"
    }
  ],
  "expected_net_total": "146.88",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 20: `get_order`

Input:
```json
{
  "order_id": "MLB-110265"
}
```

Result:
```json
{
  "id": "MLB-110265",
  "date": "2026-07-18",
  "status": "delivered",
  "cat": "fashion",
  "listing": "premium",
  "weight": "standard",
  "unit": "962.72",
  "qty": 2,
  "gross": "1925.44",
  "inst": 3,
  "refund": "0.00"
}
```

### Step 21: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-110265"
}
```

Result:
```json
{
  "order_id": "MLB-110265",
  "rows": [
    {
      "sid": "ST-1100296",
      "oid": "MLB-110265",
      "date": "2026-07-21",
      "type": "payment",
      "gross": "1925.44",
      "fee": "-346.58",
      "ship": "-39.90",
      "net": "1538.96"
    }
  ],
  "sums": {
    "gross": "1925.44",
    "fee": "-346.58",
    "ship": "-39.90",
    "net": "1538.96"
  }
}
```

### Step 22: `calc_expected`

Input:
```json
{
  "order_id": "MLB-110265"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-110265",
    "date": "2026-07-18",
    "status": "delivered",
    "cat": "fashion",
    "listing": "premium",
    "weight": "standard",
    "unit": "962.72",
    "qty": 2,
    "gross": "1925.44",
    "inst": 3,
    "refund": "0.00"
  },
  "commission_rate_pct": 18.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "1925.44",
      "fee": "-346.58",
      "ship": "-21.90",
      "net": "1556.96"
    }
  ],
  "expected_net_total": "1556.96",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 23: `get_order`

Input:
```json
{
  "order_id": "MLB-110100"
}
```

Result:
```json
{
  "id": "MLB-110100",
  "date": "2026-07-08",
  "status": "partially_refunded",
  "cat": "books",
  "listing": "premium",
  "weight": "standard",
  "unit": "203.09",
  "qty": 1,
  "gross": "203.09",
  "inst": 3,
  "refund": "101.55"
}
```

### Step 24: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-110100"
}
```

Result:
```json
{
  "order_id": "MLB-110100",
  "rows": [
    {
      "sid": "ST-1100108",
      "oid": "MLB-110100",
      "date": "2026-07-11",
      "type": "payment",
      "gross": "203.09",
      "fee": "-30.46",
      "ship": "-21.90",
      "net": "150.73"
    },
    {
      "sid": "ST-1100109",
      "oid": "MLB-110100",
      "date": "2026-07-18",
      "type": "refund",
      "gross": "-101.55",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-101.55"
    }
  ],
  "sums": {
    "gross": "101.54",
    "fee": "-30.46",
    "ship": "-21.90",
    "net": "49.18"
  }
}
```

### Step 25: `calc_expected`

Input:
```json
{
  "order_id": "MLB-110100"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-110100",
    "date": "2026-07-08",
    "status": "partially_refunded",
    "cat": "books",
    "listing": "premium",
    "weight": "standard",
    "unit": "203.09",
    "qty": 1,
    "gross": "203.09",
    "inst": 3,
    "refund": "101.55"
  },
  "commission_rate_pct": 15.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "203.09",
      "fee": "-30.46",
      "ship": "-21.90",
      "net": "150.73"
    },
    {
      "type": "refund",
      "gross": "-101.55",
      "fee": "15.23",
      "ship": "0.00",
      "net": "-86.32"
    }
  ],
  "expected_net_total": "64.41",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 26: `submit_findings`

Input:
```json
{
  "findings": [
    {
      "order_id": "MLB-110271",
      "type": "CANCELLED_BUT_SETTLED",
      "explanation": "Order status is 'cancelled' (cancelled-before-payment orders must have zero settlement rows per rule #6), yet settlement row ST-1100398 shows a full payment: gross 1465.32, fee -175.84, ship -39.90, net 1249.58. Expected net was 0.00.",
      "impact_brl": "-1249.58"
    },
    {
      "order_id": "MLB-110089",
      "type": "MISSING_SETTLEMENT",
      "explanation": "Order is 'paid' (toys, classic, gross 811.30) with expected net settlement of 692.04 (11% commission... actually 12% toys classic = 97.36 commission, ship 21.90), but zero settlement rows exist for this order.",
      "impact_brl": "692.04"
    },
    {
      "order_id": "MLB-110328",
      "type": "DUPLICATE_SETTLEMENT",
      "explanation": "Order gross is 272.00 (electronics classic, expected single payment net 220.18: fee -29.92, ship -21.90). Two identical payment rows (ST-1100368 and ST-1100397) each carry gross 272.00, fee -29.92, ship -21.90 - a legitimate split would only charge fees once on one row. The full order was settled twice, summing gross 544.00 and net 440.36 instead of 220.18.",
      "impact_brl": "-220.18"
    },
    {
      "order_id": "MLB-110334",
      "type": "REFUND_NOT_SETTLED",
      "explanation": "Order is partially_refunded with refund_amount 240.13 (20% of gross 1200.66). Expected settlement includes payment row (net 956.65) plus a refund row (gross -240.13, fee +40.82, net -199.31), for expected total net 757.34. Only the payment row (net 956.65) exists; no refund row was ever settled, leaving the seller holding the refunded amount.",
      "impact_brl": "-199.31"
    },
    {
      "order_id": "MLB-110166",
      "type": "FEE_OVERCHARGE",
      "explanation": "Order is electronics/premium, gross 1581.29, correct commission rate 16% => expected fee -253.01 (net 1288.38 after -39.90 heavy shipping, which matches observed shipping). Observed fee charged was -295.70, i.e. 42.69 more commission than the contractual 16% rate allows.",
      "impact_brl": "42.69"
    },
    {
      "order_id": "MLB-110151",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order weight_class is 'standard', so expected shipping deduction is -21.90. Settlement row ST-1100167 deducted -39.90 (the 'heavy' rate) instead, a 18.00 overcharge on shipping.",
      "impact_brl": "18.00"
    },
    {
      "order_id": "MLB-110151",
      "type": "FEE_OVERCHARGE",
      "explanation": "Order is toys/premium, gross 203.35, correct commission rate 17% => expected fee -34.57. Settlement row ST-1100167 shows fee -37.99, which is 3.42 more than the contractual rate produces.",
      "impact_brl": "3.42"
    },
    {
      "order_id": "MLB-110265",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order weight_class is 'standard' (gross 1925.44 >=79), so expected shipping deduction is -21.90 (commission of -346.58 matches observed exactly). Settl
... (truncated for readability; full data in the .jsonl)
```

Result:
```json
{
  "accepted": true,
  "count": 9
}
```

## Final outcome

- Findings submitted: **9**
- API calls: 5
- Tokens: input=10, output=9,360, cache_read=19,069, cache_write=8,371

Findings:
```json
[
  {
    "order_id": "MLB-110271",
    "type": "CANCELLED_BUT_SETTLED",
    "explanation": "Order status is 'cancelled' (cancelled-before-payment orders must have zero settlement rows per rule #6), yet settlement row ST-1100398 shows a full payment: gross 1465.32, fee -175.84, ship -39.90, net 1249.58. Expected net was 0.00.",
    "impact_brl": "-1249.58"
  },
  {
    "order_id": "MLB-110089",
    "type": "MISSING_SETTLEMENT",
    "explanation": "Order is 'paid' (toys, classic, gross 811.30) with expected net settlement of 692.04 (11% commission... actually 12% toys classic = 97.36 commission, ship 21.90), but zero settlement rows exist for this order.",
    "impact_brl": "692.04"
  },
  {
    "order_id": "MLB-110328",
    "type": "DUPLICATE_SETTLEMENT",
    "explanation": "Order gross is 272.00 (electronics classic, expected single payment net 220.18: fee -29.92, ship -21.90). Two identical payment rows (ST-1100368 and ST-1100397) each carry gross 272.00, fee -29.92, ship -21.90 - a legitimate split would only charge fees once on one row. The full order was settled twice, summing gross 544.00 and net 440.36 instead of 220.18.",
    "impact_brl": "-220.18"
  },
  {
    "order_id": "MLB-110334",
    "type": "REFUND_NOT_SETTLED",
    "explanation": "Order is partially_refunded with refund_amount 240.13 (20% of gross 1200.66). Expected settlement includes payment row (net 956.65) plus a refund row (gross -240.13, fee +40.82, net -199.31), for expected total net 757.34. Only the payment row (net 956.65) exists; no refund row was ever settled, leaving the seller holding the refunded amount.",
    "impact_brl": "-199.31"
  },
  {
    "order_id": "MLB-110166",
    "type": "FEE_OVERCHARGE",
    "explanation": "Order is electronics/premium, gross 1581.29, correct commission rate 16% => expected fee -253.01 (net 1288.38 after -39.90 heavy shipping, which matches observed shipping). Observed fee charged was -295.70, i.e. 42.69 more commission than the contractual 16% rate allows.",
    "impact_brl": "42.69"
  },
  {
    "order_id": "MLB-110151",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order weight_class is 'standard', so expected shipping deduction is -21.90. Settlement row ST-1100167 deducted -39.90 (the 'heavy' rate) instead, a 18.00 overcharge on shipping.",
    "impact_brl": "18.00"
  },
  {
    "order_id": "MLB-110151",
    "type": "FEE_OVERCHARGE",
    "explanation": "Order is toys/premium, gross 203.35, correct commission rate 17% => expected fee -34.57. Settlement row ST-1100167 shows fee -37.99, which is 3.42 more than the contractual rate produces.",
    "impact_brl": "3.42"
  },
  {
    "order_id": "MLB-110265",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order weight_class is 'standard' (gross 1925.44 >=79), so expected shipping deduction is -21.90 (commission of -346.58 matches observed exactly). Settlement row ST-1100296 instead deducted -39.90 (heavy rate), overcharging shipping by 18.00.",
    "impact_brl
... (truncated for readability; full data in the .jsonl)
```
