# Trajectory: case_08 - agent v2

- **Model:** `claude-sonnet-5`
- **Source:** `case_08_agent_v2_sonnet-5.jsonl`

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
    "total": 200,
    "by_status": {
      "paid": 78,
      "delivered": 88,
      "partially_refunded": 10,
      "refunded": 13,
      "cancelled": 10,
      "chargeback": 1
    }
  },
  "settlement_rows": {
    "total": 232,
    "by_type": {
      "payment": 208,
      "refund": 23,
      "chargeback": 1
    }
  },
  "order_dates": {
    "first": "2026-07-01",
    "last": "2026-07-28"
  },
  "gross_total": "189050.01",
  "settlement_net_total": "135139.32"
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
      "order_id": "MLB-080191",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "2276.41",
      "observed_net": "4552.82",
      "delta": "2276.41",
      "rows_observed": 2
    },
    {
      "order_id": "MLB-080078",
      "status": "cancelled",
      "issue": "unexpected_rows",
      "expected_net": "0.00",
      "observed_net": "336.03",
      "delta": "336.03",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-080173",
      "status": "delivered",
      "issue": "no_rows",
      "expected_net": "78.91",
      "observed_net": "0.00",
      "delta": "-78.91",
      "rows_observed": 0
    },
    {
      "order_id": "MLB-080018",
      "status": "partially_refunded",
      "issue": "net_delta",
      "expected_net": "686.17",
      "observed_net": "644.79",
      "delta": "-41.38",
      "rows_observed": 2
    },
    {
      "order_id": "MLB-080068",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "425.75",
      "observed_net": "403.85",
      "delta": "-21.90",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-080113",
      "status": "delivered",
      "issue": "net_delta",
      "expected_net": "580.59",
      "observed_net": "566.34",
      "delta": "-14.25",
      "rows_observed": 1
    },
    {
      "order_id": "MLB-080086",
      "status": "paid",
      "issue": "net_delta",
      "expected_net": "3715.58",
      "observed_net": "3715.12",
      "delta": "-0.46",
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
  "order_id": "MLB-080191"
}
```

Result:
```json
{
  "id": "MLB-080191",
  "date": "2026-07-12",
  "status": "paid",
  "cat": "electronics",
  "listing": "classic",
  "weight": "heavy",
  "unit": "867.53",
  "qty": 3,
  "gross": "2602.59",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 5: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-080191"
}
```

Result:
```json
{
  "order_id": "MLB-080191",
  "rows": [
    {
      "sid": "ST-0800221",
      "oid": "MLB-080191",
      "date": "2026-07-15",
      "type": "payment",
      "gross": "2602.59",
      "fee": "-286.28",
      "ship": "-39.90",
      "net": "2276.41"
    },
    {
      "sid": "ST-0800233",
      "oid": "MLB-080191",
      "date": "2026-07-16",
      "type": "payment",
      "gross": "2602.59",
      "fee": "-286.28",
      "ship": "-39.90",
      "net": "2276.41"
    }
  ],
  "sums": {
    "gross": "5205.18",
    "fee": "-572.56",
    "ship": "-79.80",
    "net": "4552.82"
  }
}
```

### Step 6: `calc_expected`

Input:
```json
{
  "order_id": "MLB-080191"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-080191",
    "date": "2026-07-12",
    "status": "paid",
    "cat": "electronics",
    "listing": "classic",
    "weight": "heavy",
    "unit": "867.53",
    "qty": 3,
    "gross": "2602.59",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "2602.59",
      "fee": "-286.28",
      "ship": "-39.90",
      "net": "2276.41"
    }
  ],
  "expected_net_total": "2276.41",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 7: `get_order`

Input:
```json
{
  "order_id": "MLB-080078"
}
```

Result:
```json
{
  "id": "MLB-080078",
  "date": "2026-07-13",
  "status": "cancelled",
  "cat": "toys",
  "listing": "premium",
  "weight": "standard",
  "unit": "215.62",
  "qty": 2,
  "gross": "431.24",
  "inst": 10,
  "refund": "0.00"
}
```

### Step 8: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-080078"
}
```

Result:
```json
{
  "order_id": "MLB-080078",
  "rows": [
    {
      "sid": "ST-0800232",
      "oid": "MLB-080078",
      "date": "2026-07-16",
      "type": "payment",
      "gross": "431.24",
      "fee": "-73.31",
      "ship": "-21.90",
      "net": "336.03"
    }
  ],
  "sums": {
    "gross": "431.24",
    "fee": "-73.31",
    "ship": "-21.90",
    "net": "336.03"
  }
}
```

### Step 9: `calc_expected`

Input:
```json
{
  "order_id": "MLB-080078"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-080078",
    "date": "2026-07-13",
    "status": "cancelled",
    "cat": "toys",
    "listing": "premium",
    "weight": "standard",
    "unit": "215.62",
    "qty": 2,
    "gross": "431.24",
    "inst": 10,
    "refund": "0.00"
  },
  "commission_rate_pct": 17.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [],
  "expected_net_total": "0.00",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 10: `get_order`

Input:
```json
{
  "order_id": "MLB-080173"
}
```

Result:
```json
{
  "id": "MLB-080173",
  "date": "2026-07-07",
  "status": "delivered",
  "cat": "fashion",
  "listing": "classic",
  "weight": "standard",
  "unit": "65.12",
  "qty": 2,
  "gross": "130.24",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 11: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-080173"
}
```

Result:
```json
{
  "order_id": "MLB-080173",
  "rows": [],
  "sums": {
    "gross": "0.00",
    "fee": "0.00",
    "ship": "0.00",
    "net": "0.00"
  }
}
```

### Step 12: `calc_expected`

Input:
```json
{
  "order_id": "MLB-080173"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-080173",
    "date": "2026-07-07",
    "status": "delivered",
    "cat": "fashion",
    "listing": "classic",
    "weight": "standard",
    "unit": "65.12",
    "qty": 2,
    "gross": "130.24",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 13.0,
  "low_ticket_fee_applies": true,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "130.24",
      "fee": "-29.43",
      "ship": "-21.90",
      "net": "78.91"
    }
  ],
  "expected_net_total": "78.91",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 13: `get_order`

Input:
```json
{
  "order_id": "MLB-080018"
}
```

Result:
```json
{
  "id": "MLB-080018",
  "date": "2026-07-19",
  "status": "partially_refunded",
  "cat": "toys",
  "listing": "classic",
  "weight": "standard",
  "unit": "1149.47",
  "qty": 1,
  "gross": "1149.47",
  "inst": 1,
  "refund": "344.84"
}
```

### Step 14: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-080018"
}
```

Result:
```json
{
  "order_id": "MLB-080018",
  "rows": [
    {
      "sid": "ST-0800022",
      "oid": "MLB-080018",
      "date": "2026-07-22",
      "type": "payment",
      "gross": "1149.47",
      "fee": "-137.94",
      "ship": "-21.90",
      "net": "989.63"
    },
    {
      "sid": "ST-0800023",
      "oid": "MLB-080018",
      "date": "2026-07-29",
      "type": "refund",
      "gross": "-344.84",
      "fee": "0.00",
      "ship": "0.00",
      "net": "-344.84"
    }
  ],
  "sums": {
    "gross": "804.63",
    "fee": "-137.94",
    "ship": "-21.90",
    "net": "644.79"
  }
}
```

### Step 15: `calc_expected`

Input:
```json
{
  "order_id": "MLB-080018"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-080018",
    "date": "2026-07-19",
    "status": "partially_refunded",
    "cat": "toys",
    "listing": "classic",
    "weight": "standard",
    "unit": "1149.47",
    "qty": 1,
    "gross": "1149.47",
    "inst": 1,
    "refund": "344.84"
  },
  "commission_rate_pct": 12.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "1149.47",
      "fee": "-137.94",
      "ship": "-21.90",
      "net": "989.63"
    },
    {
      "type": "refund",
      "gross": "-344.84",
      "fee": "41.38",
      "ship": "0.00",
      "net": "-303.46"
    }
  ],
  "expected_net_total": "686.17",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 16: `get_order`

Input:
```json
{
  "order_id": "MLB-080068"
}
```

Result:
```json
{
  "id": "MLB-080068",
  "date": "2026-07-09",
  "status": "paid",
  "cat": "electronics",
  "listing": "premium",
  "weight": "heavy",
  "unit": "554.35",
  "qty": 1,
  "gross": "554.35",
  "inst": 12,
  "refund": "0.00"
}
```

### Step 17: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-080068"
}
```

Result:
```json
{
  "order_id": "MLB-080068",
  "rows": [
    {
      "sid": "ST-0800078",
      "oid": "MLB-080068",
      "date": "2026-07-12",
      "type": "payment",
      "gross": "554.35",
      "fee": "-88.70",
      "ship": "-61.80",
      "net": "403.85"
    }
  ],
  "sums": {
    "gross": "554.35",
    "fee": "-88.70",
    "ship": "-61.80",
    "net": "403.85"
  }
}
```

### Step 18: `calc_expected`

Input:
```json
{
  "order_id": "MLB-080068"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-080068",
    "date": "2026-07-09",
    "status": "paid",
    "cat": "electronics",
    "listing": "premium",
    "weight": "heavy",
    "unit": "554.35",
    "qty": 1,
    "gross": "554.35",
    "inst": 12,
    "refund": "0.00"
  },
  "commission_rate_pct": 16.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "554.35",
      "fee": "-88.70",
      "ship": "-39.90",
      "net": "425.75"
    }
  ],
  "expected_net_total": "425.75",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 19: `get_order`

Input:
```json
{
  "order_id": "MLB-080113"
}
```

Result:
```json
{
  "id": "MLB-080113",
  "date": "2026-07-16",
  "status": "delivered",
  "cat": "fashion",
  "listing": "premium",
  "weight": "standard",
  "unit": "734.75",
  "qty": 1,
  "gross": "734.75",
  "inst": 12,
  "refund": "0.00"
}
```

### Step 20: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-080113"
}
```

Result:
```json
{
  "order_id": "MLB-080113",
  "rows": [
    {
      "sid": "ST-0800128",
      "oid": "MLB-080113",
      "date": "2026-07-19",
      "type": "payment",
      "gross": "734.75",
      "fee": "-146.51",
      "ship": "-21.90",
      "net": "566.34"
    }
  ],
  "sums": {
    "gross": "734.75",
    "fee": "-146.51",
    "ship": "-21.90",
    "net": "566.34"
  }
}
```

### Step 21: `calc_expected`

Input:
```json
{
  "order_id": "MLB-080113"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-080113",
    "date": "2026-07-16",
    "status": "delivered",
    "cat": "fashion",
    "listing": "premium",
    "weight": "standard",
    "unit": "734.75",
    "qty": 1,
    "gross": "734.75",
    "inst": 12,
    "refund": "0.00"
  },
  "commission_rate_pct": 18.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "734.75",
      "fee": "-132.26",
      "ship": "-21.90",
      "net": "580.59"
    }
  ],
  "expected_net_total": "580.59",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 22: `get_order`

Input:
```json
{
  "order_id": "MLB-080086"
}
```

Result:
```json
{
  "id": "MLB-080086",
  "date": "2026-07-17",
  "status": "paid",
  "cat": "electronics",
  "listing": "classic",
  "weight": "heavy",
  "unit": "2109.82",
  "qty": 2,
  "gross": "4219.64",
  "inst": 1,
  "refund": "0.00"
}
```

### Step 23: `get_order_settlements`

Input:
```json
{
  "order_id": "MLB-080086"
}
```

Result:
```json
{
  "order_id": "MLB-080086",
  "rows": [
    {
      "sid": "ST-0800098",
      "oid": "MLB-080086",
      "date": "2026-07-20",
      "type": "payment",
      "gross": "4219.64",
      "fee": "-464.62",
      "ship": "-39.90",
      "net": "3715.12"
    }
  ],
  "sums": {
    "gross": "4219.64",
    "fee": "-464.62",
    "ship": "-39.90",
    "net": "3715.12"
  }
}
```

### Step 24: `calc_expected`

Input:
```json
{
  "order_id": "MLB-080086"
}
```

Result:
```json
{
  "order": {
    "id": "MLB-080086",
    "date": "2026-07-17",
    "status": "paid",
    "cat": "electronics",
    "listing": "classic",
    "weight": "heavy",
    "unit": "2109.82",
    "qty": 2,
    "gross": "4219.64",
    "inst": 1,
    "refund": "0.00"
  },
  "commission_rate_pct": 11.0,
  "low_ticket_fee_applies": false,
  "expected_lines": [
    {
      "type": "payment",
      "gross": "4219.64",
      "fee": "-464.16",
      "ship": "-39.90",
      "net": "3715.58"
    }
  ],
  "expected_net_total": "3715.58",
  "note": "Payment may legitimately arrive split across two rows (fees on the first)."
}
```

### Step 25: `submit_findings`

Input:
```json
{
  "findings": [
    {
      "order_id": "MLB-080191",
      "type": "DUPLICATE_SETTLEMENT",
      "explanation": "Order gross 2602.59 (electronics, classic, heavy) generates one expected payment row with fee -286.28 and shipping -39.90, net 2276.41. The settlement statement shows TWO identical payment rows (ST-0800221 and ST-0800233), each with the same full gross, fee and shipping, summing to net 4552.82 - double the expected amount. This is not a legitimate split (a split carries fees only on the first row); it's a straight duplicate of the same payment.",
      "impact_brl": "-2276.41"
    },
    {
      "order_id": "MLB-080078",
      "type": "CANCELLED_BUT_SETTLED",
      "explanation": "Order status is 'cancelled' (cancelled before payment), so per rule 6 it should have NO settlement rows and expected net is 0.00. However settlement row ST-0800232 shows a full payment of gross 431.24, fee -73.31, shipping -21.90, net 336.03 was settled to the seller.",
      "impact_brl": "-336.03"
    },
    {
      "order_id": "MLB-080173",
      "type": "MISSING_SETTLEMENT",
      "explanation": "Order is 'delivered', gross 130.24 (fashion, classic, unit_price<79 triggers low-ticket fee), expected payment row: fee -29.43, shipping -21.90, net 78.91. No settlement rows exist for this order at all (0 rows found).",
      "impact_brl": "78.91"
    },
    {
      "order_id": "MLB-080018",
      "type": "REFUND_AMOUNT_MISMATCH",
      "explanation": "Order partially refunded 344.84 of gross 1149.47 (toys, classic, 12% commission). Expected refund row: gross -344.84, fee +41.38 (commission returned = round(137.94*30%)), net -303.46. Observed refund row ST-0800023 has fee 0.00 and net -344.84, i.e. the commission credit of 41.38 was never returned to the seller. Total order net observed 644.79 vs expected 686.17 (diff 41.38).",
      "impact_brl": "41.38"
    },
    {
      "order_id": "MLB-080068",
      "type": "WRONG_SHIPPING_DEDUCTION",
      "explanation": "Order is heavy weight_class, gross 554.35 >=79, so seller should be charged the heavy shipping fee of 39.90. Settlement row ST-0800078 deducts shipping of 61.80 instead (=39.90+21.90, i.e. both standard and heavy rates summed). Fee/commission matches expected (-88.70), only shipping is wrong, causing net 403.85 vs expected 425.75 (diff 21.90).",
      "impact_brl": "21.90"
    },
    {
      "order_id": "MLB-080113",
      "type": "FEE_OVERCHARGE",
      "explanation": "Order is fashion/premium, gross 734.75, contractual commission rate 18% => expected fee -132.26 (734.75*0.18=132.255->132.26). Settlement row ST-0800128 charged fee -146.51, i.e. an effective rate of ~19.94%, 14.25 more than the contractual fee. Net observed 566.34 vs expected 580.59.",
      "impact_brl": "14.25"
    },
    {
      "order_id": "MLB-080086",
      "type": "FEE_OVERCHARGE",
      "explanation": "Order is electronics/classic, gross 4219.64, contractual commission rate 11% => expected fee -464.16 (4219.64*0.11=464.1604->4
... (truncated for readability; full data in the .jsonl)
```

Result:
```json
{
  "accepted": true,
  "count": 7
}
```

## Final outcome

- Findings submitted: **7**
- API calls: 4
- Tokens: input=8, output=5,374, cache_read=12,447, cache_write=6,892

Findings:
```json
[
  {
    "order_id": "MLB-080191",
    "type": "DUPLICATE_SETTLEMENT",
    "explanation": "Order gross 2602.59 (electronics, classic, heavy) generates one expected payment row with fee -286.28 and shipping -39.90, net 2276.41. The settlement statement shows TWO identical payment rows (ST-0800221 and ST-0800233), each with the same full gross, fee and shipping, summing to net 4552.82 - double the expected amount. This is not a legitimate split (a split carries fees only on the first row); it's a straight duplicate of the same payment.",
    "impact_brl": "-2276.41"
  },
  {
    "order_id": "MLB-080078",
    "type": "CANCELLED_BUT_SETTLED",
    "explanation": "Order status is 'cancelled' (cancelled before payment), so per rule 6 it should have NO settlement rows and expected net is 0.00. However settlement row ST-0800232 shows a full payment of gross 431.24, fee -73.31, shipping -21.90, net 336.03 was settled to the seller.",
    "impact_brl": "-336.03"
  },
  {
    "order_id": "MLB-080173",
    "type": "MISSING_SETTLEMENT",
    "explanation": "Order is 'delivered', gross 130.24 (fashion, classic, unit_price<79 triggers low-ticket fee), expected payment row: fee -29.43, shipping -21.90, net 78.91. No settlement rows exist for this order at all (0 rows found).",
    "impact_brl": "78.91"
  },
  {
    "order_id": "MLB-080018",
    "type": "REFUND_AMOUNT_MISMATCH",
    "explanation": "Order partially refunded 344.84 of gross 1149.47 (toys, classic, 12% commission). Expected refund row: gross -344.84, fee +41.38 (commission returned = round(137.94*30%)), net -303.46. Observed refund row ST-0800023 has fee 0.00 and net -344.84, i.e. the commission credit of 41.38 was never returned to the seller. Total order net observed 644.79 vs expected 686.17 (diff 41.38).",
    "impact_brl": "41.38"
  },
  {
    "order_id": "MLB-080068",
    "type": "WRONG_SHIPPING_DEDUCTION",
    "explanation": "Order is heavy weight_class, gross 554.35 >=79, so seller should be charged the heavy shipping fee of 39.90. Settlement row ST-0800078 deducts shipping of 61.80 instead (=39.90+21.90, i.e. both standard and heavy rates summed). Fee/commission matches expected (-88.70), only shipping is wrong, causing net 403.85 vs expected 425.75 (diff 21.90).",
    "impact_brl": "21.90"
  },
  {
    "order_id": "MLB-080113",
    "type": "FEE_OVERCHARGE",
    "explanation": "Order is fashion/premium, gross 734.75, contractual commission rate 18% => expected fee -132.26 (734.75*0.18=132.255->132.26). Settlement row ST-0800128 charged fee -146.51, i.e. an effective rate of ~19.94%, 14.25 more than the contractual fee. Net observed 566.34 vs expected 580.59.",
    "impact_brl": "14.25"
  },
  {
    "order_id": "MLB-080086",
    "type": "FEE_OVERCHARGE",
    "explanation": "Order is electronics/classic, gross 4219.64, contractual commission rate 11% => expected fee -464.16 (4219.64*0.11=464.1604->464.16). Settlement row ST-0800098 charged fee -464.62, 0.46 more than contractual, net observed 
... (truncated for readability; full data in the .jsonl)
```
