# Marketplace Settlement Rules

Synthetic ruleset modeled on typical Latin American marketplace terms (Mercado
Livre style). All amounts in BRL. These rules are the contract between the
marketplace and the seller; the settlement statement must follow them exactly.

## 1. Commission

- Each sale pays a commission: `commission = round_half_up(gross_amount * rate)`.
- The rate depends on `category` and `listing_type` (see `fee_schedule.json`):

| Category    | classic | premium |
|-------------|---------|---------|
| electronics | 11%     | 16%     |
| fashion     | 13%     | 18%     |
| home        | 12%     | 17%     |
| toys        | 12%     | 17%     |
| books       | 10%     | 15%     |

- Low-ticket fixed fee: when `unit_price < 79.00`, add `6.25 * quantity` to the
  commission.
- `premium` listings offer interest-free installments to the buyer; that cost
  is already built into the higher premium rate. The number of installments
  does NOT change any fee.

## 2. Shipping charged to the seller

- Orders with `gross_amount >= 79.00` ship free for the buyer and the SELLER
  pays shipping: `21.90` (weight_class `standard`) or `39.90` (`heavy`).
- Orders with `gross_amount < 79.00`: no shipping is deducted from the seller.

## 3. Sign convention on the settlement statement

Every settlement row satisfies `net_amount = gross_amount + marketplace_fee +
shipping_fee`. Fees appear as negative values on payment rows.

- `payment` row: `gross = +G`, `marketplace_fee = -commission`,
  `shipping_fee = -shipping`, `net = G - commission - shipping`.

## 4. Refunds

- Full refund (`status = refunded`): one `refund` row with `gross = -G`,
  `marketplace_fee = +commission` (commission is returned to the seller),
  `shipping_fee = 0` (shipping is NOT returned). `net = -G + commission`.
- Partial refund of p% (`status = partially_refunded`, see `refund_amount` on
  the order): `gross = -round_half_up(G * p%)`,
  `marketplace_fee = +round_half_up(commission * p%)`, `shipping_fee = 0`.

## 5. Chargebacks

- `chargeback` row: `gross = -G`, no commission or shipping returned.
  A legitimate chargeback is NOT a divergence.

## 6. Cancelled orders

- Orders cancelled before payment (`status = cancelled`) must have NO
  settlement rows at all.

## 7. Split settlements (IMPORTANT)

- A single order's `payment` MAY legitimately arrive split across two rows
  (installment funding): the first row carries all the fees, the second row
  carries the remaining gross with no fees. This is NOT a divergence when the
  summed values match the expected totals.

## 8. Tolerance

- Net differences of up to `0.02` per order are rounding noise, NOT
  divergences. Only report a divergence when the absolute impact exceeds 0.02.
