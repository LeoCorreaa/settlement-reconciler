# Trajectory: case_10 - agent v2

- **Model:** `claude-sonnet-5`
- **Source:** `case_10_agent_v2_sonnet-5.jsonl`

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
    "total": 300,
    "by_status": {
      "paid": 127,
      "delivered": 122,
      "partially_refunded": 15,
      "refunded": 20,
      "cancelled": 15,
      "chargeback": 1
    }
  },
  "settlement_rows": {
    "total": 338,
    "by_type": {
      "payment": 303,
      "refund": 34,
      "chargeback": 1
    }
  },
  "order_dates": {
    "first": "2026-07-01",
    "last": "2026-07-28"
  },
  "gross_total": "319994.73",
  "settlement_net_total": "228191.90"
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
      "order_id": "MLB-109378",
      "status": "NOT_IN_ORDER_BOOK",
      "issue": "orphan_rows",
      "expected_net": "0.00",
      "observed_net": "575.86",
      "delta": "575.86",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-100150",
      "status": "paid",
      "issue": "no_rows",
      "expected_net": "329.42",
      "observed_net": "0.00",
      "delta": "-329.42",
      "rows_observed": 0
    },
    {
      "order_id": "MLB-100045",
      "status": "cancelled",
      "issue": "unexpected_rows",
      "expected_net": "0.00",
      "observed_net": "41.07",
      "delta": "41.07",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-100069",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "336.81",
      "observed_net": "318.81",
      "delta": "-18.00",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-100060",
      "status": "refunded",
      "issue": "net_delta",
      "expected_net": "0.00",
      "observed_net": "-17.43",
      "delta": "-17.43",
      "rows_observed": 2
    },
    {
      "order_id": "MLB-100168",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "311.04",
      "observed_net": "299.63",
      "delta": "-11.41",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-100300",
      "status": "refunded",
      "issue": "net_delta",
      "expected_net": "0.00",
      "observed_net": "8.37",
      "delta": "8.37",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-100187",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "2001.50",
      "observed_net": "2000.82",
      "delta": "-0.68",
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
  "order_id": "MLB-109378"
}
```

Result:
```json
{
  "error": "order MLB-109378 not found in the seller's book"
}
```

### Step 5: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-109378"
}
```

Result:
```json
{
  "order_id": "MLB-109378",
  "rows": [
    {
      "sid": "ST-1000340",
      "oid": "MLB-109378",
      "date": "2026-07-21",
      "type": "payment",
      "gross": "661.91",
      "fee": "-86.05",
      "ship": "0.00",
      "net": "575.86"
    }
  ],
  "sums": {
    "gross": "661.91",
    "fee": "-86.05",
    "ship": "0.00",
    "net": "575.86"
  }
}
```

### Step 6: `get_order`

Input:
```json
{
  "order_id": "MLB-100150"
}
```

Result:
```json
{
  "id": "MLB-100150",
  "date": "2026-07-14",
  "status": "paid",
  "cat": "home",
  "listing": "classic",
  "weight": "heavy",
  "unit": "419.68",
  "qty": 1,
  "gross": "419.68",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 7: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-100150"
}
```

Result:
```json
{
  "order_id": "MLB-100150",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 8: `calc_expected`

Input:
```json
{
  "order_id": "MLB-100150"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-100150",
    "date": "2026-07-14",
    "status": "paid",
    "cat": "home",
    "listing": "classic",
    "weight": "heavy",
    "unit": "419.68",
    "qty": 1,
    "gross": "419.68",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 12.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "419.68",
      "fee": "-50.36",
      "ship": "-39.90",
      "net": "329.42"
    }
  ],
  "expected_net_total": "329.42",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 9: `get_order`

Input:
```json
{
  "order_id": "MLB-100045"
}
```

Result:
```json
{
  "id": "MLB-100045",
  "date": "2026-07-14",
  "status": "cancelled",
  "cat": "books",
  "listing": "classic",
  "weight": "standard",
  "unit": "52.58",
  "qty": 1,
  "gross": "52.58",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 10: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-100045"
}
```

Result:
```json
{
  "order_id": "MLB-100045",
  "rows": [
    {
      "sid": "ST-1000339",
      "oid": "MLB-100045",
      "date": "2026-07-17",
      "type": "payment",
      "gross": "52.58",
      "fee": "-11.51",
      "ship": "0.00",
      "net": "41.07"
    }
  ],
  "sums": {
    "gross": "52.58",
    "fee": "-11.51",
    "ship": "0.00",
    "net": "41.07"
  }
}
```

### Step 11: `get_order`

Input:
```json
{
  "order_id": "MLB-100069"
}
```

Result:
```json
{
  "id": "MLB-100069",
  "date": "2026-07-03",
  "status": "paid",
  "cat": "toys",
  "listing": "premium",
  "weight": "standard",
  "unit": "216.09",
  "qty": 2,
  "gross": "432.18",
  "inst": 6,
  "refund": "0.00"
}
```

### Step 12: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-100069"
}
```

Result:
```json
{
  "order_id": "MLB-100069",
  "rows": [
    {
      "sid": "ST-1000075",
      "oid": "MLB-100069",
      "date": "2026-07-06",
      "type": "payment",
      "gross": "432.18",
      "fee": "-73.47",
      "ship": "-39.90",
      "net": "318.81"
    }
  ],
  "sums": {
    "gross": "432.18",
    "fee": "-73.47",
    "ship": "-39.90",
    "net": "318.81"
  }
}
```

### Step 13: `calc_expected`

Input:
```json
{
  "order_id": "MLB-100069"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-100069",
    "date": "2026-07-03",
    "status": "paid",
    "cat": "toys",
    "listing": "premium",
    "weight": "standard",
    "unit": "216.09",
    "qty": 2,
    "gross": "432.18",
    "inst": 6,
    "refund": "0.00"
  },
  "commission_rate_pct": 17.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "432.18",
      "fee": "-73.47",
      "ship": "-21.90",
      "net": "336.81"
    }
  ],
  "expected_net_total": "336.81",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 14: `get_order`

Input:
```json
{
  "order_id": "MLB-100060"
}
```

Result:
```json
{
  "id": "MLB-100060",
  "date": "2026-07-10",
  "status": "refunded",
  "cat": "books",
  "listing": "premium",
  "weight": "standard",
  "unit": "74.56",
  "qty": 1,
  "gross": "74.56",
  "inst": 10,
  "refund": "74.56"
}
```

### Step 15: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-100060"
}
```

Result:
```json
{
  "order_id": "MLB-100060",
  "rows": [
    {
      "sid": "ST-1000065",
      "oid": "MLB-100060",
      "date": "2026-07-13",
      "type": "payment",
      "gross": "74.56",
      "fee": "-17.43",
      "ship": "0.00",
      "net": "57.13"
    },
    {
      "sid": "ST-1000066",
      "oid": "MLB-100060",
      "date": "2026-07-20",
      "type": "refund",
      "gross": "-74.56",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-74.56"
    }
  ],
  "sums": {
    "gross": "0.00",
    "fee": "-17.43",
    "ship": "0.00",
    "net": "-17.43"
  }
}
```

### Step 16: `calc_expected`

Input:
```json
{
  "order_id": "MLB-100060"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-100060",
    "date": "2026-07-10",
    "status": "refunded",
    "cat": "books",
    "listing": "premium",
    "weight": "standard",
    "unit": "74.56",
    "qty": 1,
    "gross": "74.56",
    "inst": 10,
    "refund": "74.56"
  },
  "commission_rate_pct": 15.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "74.56",
      "fee": "-17.43",
      "ship": "0.00",
      "net": "57.13"
    },
    {
      "type": "refund",
      "gross": "-74.56",
      "fee": "17.43",
      "ship": "0.00",
      "net": "-57.13"
    }
  ],
  "expected_net_total": "0.00",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 17: `get_order`

Input:
```json
{
  "order_id": "MLB-100168"
}
```

Result:
```json
{
  "id": "MLB-100168",
  "date": "2026-07-25",
  "status": "delivered",
  "cat": "fashion",
  "listing": "premium",
  "weight": "standard",
  "unit": "406.02",
  "qty": 1,
  "gross": "406.02",
  "inst": 10,
  "refund": "0.00"
}
```

### Step 18: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-100168"
}
```

Result:
```json
{
  "order_id": "MLB-100168",
  "rows": [
    {
      "sid": "ST-1000185",
      "oid": "MLB-100168",
      "date": "2026-07-28",
      "type": "payment",
      "gross": "406.02",
      "fee": "-84.49",
      "ship": "-21.90",
      "net": "299.63"
    }
  ],
  "sums": {
    "gross": "406.02",
    "fee": "-84.49",
    "ship": "-21.90",
    "net": "299.63"
  }
}
```

### Step 19: `calc_expected`

Input:
```json
{
  "order_id": "MLB-100168"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-100168",
    "date": "2026-07-25",
    "status": "delivered",
    "cat": "fashion",
    "listing": "premium",
    "weight": "standard",
    "unit": "406.02",
    "qty": 1,
    "gross": "406.02",
    "inst": 10,
    "refund": "0.00"
  },
  "commission_rate_pct": 18.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "406.02",
      "fee": "-73.08",
      "ship": "-21.90",
      "net": "311.04"
    }
  ],
  "expected_net_total": "311.04",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 20: `get_order`

Input:
```json
{
  "order_id": "MLB-100300"
}
```

Result:
```json
{
  "id": "MLB-100300",
  "date": "2026-07-11",
  "status": "refunded",
  "cat": "fashion",
  "listing": "premium",
  "weight": "standard",
  "unit": "17.83",
  "qty": 1,
  "gross": "17.83",
  "inst": 3,
  "refund": "17.83"
}
```

### Step 21: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-100300"
}
```

Result:
```json
{
  "order_id": "MLB-100300",
  "rows": [
    {
      "sid": "ST-1000337",
      "oid": "MLB-100300",
      "date": "2026-07-14",
      "type": "payment",
      "gross": "17.83",
      "fee": "-9.46",
      "ship": "0.00",
      "net": "8.37"
    }
  ],
  "sums": {
    "gross": "17.83",
    "fee": "-9.46",
    "ship": "0.00",
    "net": "8.37"
  }
}
```

### Step 22: `calc_expected`

Input:
```json
{
  "order_id": "MLB-100300"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-100300",
    "date": "2026-07-11",
    "status": "refunded",
    "cat": "fashion",
    "listing": "premium",
    "weight": "standard",
    "unit": "17.83",
    "qty": 1,
    "gross": "17.83",
    "inst": 3,
    "refund": "17.83"
  },
  "commission_rate_pct": 18.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "17.83",
      "fee": "-9.46",
      "ship": "0.00",
      "net": "8.37"
    },
    {
      "type": "refund",
      "gross": "-17.83",
      "fee": "9.46",
      "ship": "0.00",
      "net": "-8.37"
    }
  ],
  "expected_net_total": "0.00",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 23: `get_order`

Input:
```json
{
  "order_id": "MLB-100187"
}
```

Result:
```json
{
  "id": "MLB-100187",
  "date": "2026-07-08",
  "status": "delivered",
  "cat": "books",
  "listing": "premium",
  "weight": "standard",
  "unit": "2380.47",
  "qty": 1,
  "gross": "2380.47",
  "inst": 12,
  "refund": "0.00"
}
```

### Step 24: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-100187"
}
```

Result:
```json
{
  "order_id": "MLB-100187",
  "rows": [
    {
      "sid": "ST-1000205",
      "oid": "MLB-100187",
      "date": "2026-07-11",
      "type": "payment",
      "gross": "2380.47",
      "fee": "-357.75",
      "ship": "-21.90",
      "net": "2000.82"
    }
  ],
  "sums": {
    "gross": "2380.47",
    "fee": "-357.75",
    "ship": "-21.90",
    "net": "2000.82"
  }
}
```

### Step 25: `calc_expected`

Input:
```json
{
  "order_id": "MLB-100187"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-100187",
    "date": "2026-07-08",
    "status": "delivered",
    "cat": "books",
    "listing": "premium",
    "weight": "standard",
    "unit": "2380.47",
    "qty": 1,
    "gross": "2380.47",
    "inst": 12,
    "refund": "0.00"
  },
  "commission_rate_pct": 15.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "2380.47",
      "fee": "-357.07",
      "ship": "-21.90",
      "net": "2001.50"
    }
  ],
  "expected_net_total": "2001.50",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 26: `submit_findings`

Input:
```json
{
  "findings": [
    {
      "order_id": "MLB-109378",
      "type": "ORPHAN_SETTLEMENT",
      "explanation": "Settlement row ST-1000340 (gross 661.91, fee -86.05, net 575.86) references order MLB-109378 which does not exist anywhere in the seller's order book. There is no corresponding sale to justify this payout.",
      "impact_brl": "-575.86"
    },
    {
      "order_id": "MLB-100150",
      "type": "MISSING_SETTLEMENT",
      "explanation": "Order is status=paid, gross 419.68, home/classic, heavy shipping. Expected settlement: commission -50.36 (12%), shipping -39.90, net 329.42. No settlement rows exist at all for this order (observed net 0.00).",
      "impact_brl": "329.42"
    },
    {
      "order_id": "MLB-100045",
      "type": "CANCELLED_BUT_SETTLED",
      "explanation": "Order status is cancelled, which per rules must have NO settlement rows. However a payment row (ST-1000339) was settled: gross 52.58, fee -11.51, net 41.07.",
      "impact_brl": "-41.07"
    },
    {
      "order_id": "MLB-100069",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order weight_class is 'standard' so shipping should be 21.90, giving expected net 336.81 (gross 432.18, fee -73.47, ship -21.90). Settlement instead deducted the heavy rate of 39.90, producing observed net 318.81 (fee -73.47 matches, but ship -39.90). Difference of 18.00 = 39.90-21.90.",
      "impact_brl": "18.00"
    },
    {
      "order_id": "MLB-100060",
      "type": "REFUND_AMOUNT_MISMATCH",
      "explanation": "Order is a full refund (books/premium, gross 74.56, commission 17.43 incl. low-ticket fee). Rules require the refund row to credit back the commission: expected refund line gross -74.56, fee +17.43, net -57.13 (expected order total net = 0.00). Observed refund row ST-1000066 has fee 0.00, net -74.56, so the commission was never returned. Order total observed net -17.43 vs expected 0.00.",
      "impact_brl": "17.43"
    },
    {
      "order_id": "MLB-100168",
      "type": "FEE_OVERCHARGE",
      "explanation": "Fashion/premium listing, gross 406.02, correct commission rate 18% => expected fee -73.08 (round_half_up(406.02*0.18)=73.08), expected net 311.04 with shipping -21.90. Settlement row ST-1000185 charged fee -84.49 instead, producing observed net 299.63. Overcharge of 11.41.",
      "impact_brl": "11.41"
    },
    {
      "order_id": "MLB-100300",
      "type": "REFUND_NOT_SETTLED",
      "explanation": "Order status is refunded (100% refund, gross 17.83, fashion/premium, low-ticket fee applies). Expected: payment row net 8.37 plus refund row gross -17.83, fee +9.46, net -8.37, for an expected order total net of 0.00. Only the original payment row (net 8.37) is present; no refund row was ever settled, leaving the buyer's refund unprocessed on the statement.",
      "impact_brl": "-8.37"
    },
    {
      "order_id": "MLB-100187",
      "type": "FEE_OVERCHARGE",
      "explanation": "Books/premium listing, gross 2380.47, correct commission rate 15
... (truncated for readability; full data in the .jsonl)
```

Result:
```json
{
  "accepted": true,
  "count": 8
}
```

## Final outcome

- Findings submitted: **8**
- API calls: 4
- Tokens: input=8, output=6,820, cache_read=12,554, cache_write=6,982

Findings:
```json
[
  {
    "order_id": "MLB-109378",
    "type": "ORPHAN_SETTLEMENT",
    "explanation": "Settlement row ST-1000340 (gross 661.91, fee -86.05, net 575.86) references order MLB-109378 which does not exist anywhere in the seller's order book. There is no corresponding sale to justify this payout.",
    "impact_brl": "-575.86"
  },
  {
    "order_id": "MLB-100150",
    "type": "MISSING_SETTLEMENT",
    "explanation": "Order is status=paid, gross 419.68, home/classic, heavy shipping. Expected settlement: commission -50.36 (12%), shipping -39.90, net 329.42. No settlement rows exist at all for this order (observed net 0.00).",
    "impact_brl": "329.42"
  },
  {
    "order_id": "MLB-100045",
    "type": "CANCELLED_BUT_SETTLED",
    "explanation": "Order status is cancelled, which per rules must have NO settlement rows. However a payment row (ST-1000339) was settled: gross 52.58, fee -11.51, net 41.07.",
    "impact_brl": "-41.07"
  },
  {
    "order_id": "MLB-100069",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order weight_class is 'standard' so shipping should be 21.90, giving expected net 336.81 (gross 432.18, fee -73.47, ship -21.90). Settlement instead deducted the heavy rate of 39.90, producing observed net 318.81 (fee -73.47 matches, but ship -39.90). Difference of 18.00 = 39.90-21.90.",
    "impact_brl": "18.00"
  },
  {
    "order_id": "MLB-100060",
    "type": "REFUND_AMOUNT_MISMATCH",
    "explanation": "Order is a full refund (books/premium, gross 74.56, commission 17.43 incl. low-ticket fee). Rules require the refund row to credit back the commission: expected refund line gross -74.56, fee +17.43, net -57.13 (expected order total net = 0.00). Observed refund row ST-1000066 has fee 0.00, net -74.56, so the commission was never returned. Order total observed net -17.43 vs expected 0.00.",
    "impact_brl": "17.43"
  },
  {
    "order_id": "MLB-100168",
    "type": "FEE_OVERCHARGE",
    "explanation": "Fashion/premium listing, gross 406.02, correct commission rate 18% => expected fee -73.08 (round_half_up(406.02*0.18)=73.08), expected net 311.04 with shipping -21.90. Settlement row ST-1000185 charged fee -84.49 instead, producing observed net 299.63. Overcharge of 11.41.",
    "impact_brl": "11.41"
  },
  {
    "order_id": "MLB-100300",
    "type": "REFUND_NOT_SETTLED",
    "explanation": "Order status is refunded (100% refund, gross 17.83, fashion/premium, low-ticket fee applies). Expected: payment row net 8.37 plus refund row gross -17.83, fee +9.46, net -8.37, for an expected order total net of 0.00. Only the original payment row (net 8.37) is present; no refund row was ever settled, leaving the buyer's refund unprocessed on the statement.",
    "impact_brl": "-8.37"
  },
  {
    "order_id": "MLB-100187",
    "type": "FEE_OVERCHARGE",
    "explanation": "Books/premium listing, gross 2380.47, correct commission rate 15% => expected fee -357.07 (round_half_up(2380.47*0.15)), expected net 2001.50 with shipping -21.90. Settleme
... (truncated for readability; full data in the .jsonl)
```
