"""Deterministic synthetic case generator.

Each case is a folder under cases/ containing:
  orders.csv      what the seller sees in the marketplace panel
  settlement.csv  what the payment processor actually paid out
  truth.json      ground truth of planted divergences (EVALUATION ONLY -
                  solvers must never read this file)
  case.json       case metadata

Settlements are first built 100% correct via engine.expected_settlement_lines,
then a per-case corruption plan plants divergences and records the ground
truth. Fixed seeds make every byte reproducible: run it twice, get identical
files.

Usage:
    python -m datagen.generate
"""

from __future__ import annotations

import copy
import csv
import json
import random
import shutil
from datetime import date, timedelta
from pathlib import Path

import config
from engine import (
    PAID_STATUSES,
    commission_cents,
    expected_settlement_lines,
    half_up,
    load_fee_schedule,
    money,
    shipping_cents,
)

CATEGORIES = ["electronics", "fashion", "home", "toys", "books"]
LISTING_TYPES = ["classic", "premium"]
BASE_DATE = date(2026, 7, 1)

# (case_id, n_orders, difficulty, [divergence types to plant])
#
# Sizes mirror real monthly volumes: a small store settles tens of orders, a
# mid-size one settles hundreds. Baseline probing (see changelog) showed a
# single-prompt approach saturates around ~40 orders and collapses by ~80, so
# the case set spans 40-400 to expose the scale curve honestly.
CASE_SPECS: list[tuple[str, int, str, list[str]]] = [
    ("case_01", 40, "clean", []),
    ("case_02", 150, "clean", []),
    ("case_03", 50, "normal", ["MISSING_SETTLEMENT", "FEE_OVERCHARGE", "FEE_OVERCHARGE", "DUPLICATE_SETTLEMENT"]),
    ("case_04", 60, "normal", ["WRONG_SHIPPING_DEDUCTION", "WRONG_SHIPPING_DEDUCTION", "ORPHAN_SETTLEMENT"]),
    ("case_05", 80, "normal", ["REFUND_NOT_SETTLED", "FEE_OVERCHARGE", "MISSING_SETTLEMENT", "CANCELLED_BUT_SETTLED", "REFUND_AMOUNT_MISMATCH"]),
    ("case_06", 120, "normal", ["REFUND_AMOUNT_MISMATCH", "DUPLICATE_SETTLEMENT", "WRONG_SHIPPING_DEDUCTION", "FEE_OVERCHARGE", "MISSING_SETTLEMENT", "COMBO_FEE_SHIP"]),
    ("case_07", 160, "normal", ["FEE_OVERCHARGE", "ORPHAN_SETTLEMENT", "REFUND_NOT_SETTLED", "MISSING_SETTLEMENT", "WRONG_SHIPPING_DEDUCTION", "CANCELLED_BUT_SETTLED"]),
    ("case_08", 200, "normal", ["CANCELLED_BUT_SETTLED", "REFUND_AMOUNT_MISMATCH", "FEE_OVERCHARGE", "DUPLICATE_SETTLEMENT", "MISSING_SETTLEMENT", "WRONG_SHIPPING_DEDUCTION", "FEE_OVERCHARGE_SUBTLE"]),
    ("case_09", 250, "normal", ["DUPLICATE_SETTLEMENT", "MISSING_SETTLEMENT", "ORPHAN_SETTLEMENT", "FEE_OVERCHARGE", "REFUND_NOT_SETTLED", "WRONG_SHIPPING_DEDUCTION", "FEE_OVERCHARGE", "COMBO_REFUND_FEE"]),
    ("case_10", 300, "normal", ["WRONG_SHIPPING_DEDUCTION", "REFUND_NOT_SETTLED", "CANCELLED_BUT_SETTLED", "REFUND_AMOUNT_MISMATCH", "FEE_OVERCHARGE", "MISSING_SETTLEMENT", "ORPHAN_SETTLEMENT", "FEE_OVERCHARGE_SUBTLE"]),
    ("case_11", 350, "normal", ["MISSING_SETTLEMENT", "DUPLICATE_SETTLEMENT", "FEE_OVERCHARGE", "REFUND_AMOUNT_MISMATCH", "WRONG_SHIPPING_DEDUCTION", "CANCELLED_BUT_SETTLED", "REFUND_NOT_SETTLED", "COMBO_FEE_SHIP"]),
    # Hard case: real mid-size monthly volume, subtle and compound
    # divergences, and a combo order that is partially refunded AND
    # split-settled AND shorted on the refunded commission.
    ("case_12", 400, "hard", [
        "MISSING_SETTLEMENT", "DUPLICATE_SETTLEMENT", "ORPHAN_SETTLEMENT",
        "FEE_OVERCHARGE", "FEE_OVERCHARGE", "WRONG_SHIPPING_DEDUCTION",
        "WRONG_SHIPPING_DEDUCTION", "REFUND_NOT_SETTLED",
        "CANCELLED_BUT_SETTLED", "REFUND_AMOUNT_MISMATCH",
        "COMBO_REFUND_FEE", "FEE_OVERCHARGE_SUBTLE",
    ]),
]


# ------------------------------------------------------------------- orders

def build_statuses(rng: random.Random, n: int) -> list[str]:
    quotas = {
        "refunded": max(3, n // 15),
        "partially_refunded": max(2, n // 20),
        "cancelled": max(2, n // 20),
        "chargeback": 1,
    }
    statuses = [s for s, q in quotas.items() for _ in range(q)]
    remainder = n - len(statuses)
    statuses += ["delivered" if rng.random() < 0.5 else "paid" for _ in range(remainder)]
    rng.shuffle(statuses)
    return statuses


def build_orders(rng: random.Random, case_num: int, n: int) -> list[dict]:
    orders = []
    statuses = build_statuses(rng, n)
    for seq, status in enumerate(statuses, start=1):
        category = rng.choice(CATEGORIES)
        listing_type = rng.choice(LISTING_TYPES)
        unit_price_cents = rng.choice([
            rng.randint(1500, 7899),        # low ticket
            rng.randint(7900, 45000),       # mid
            rng.randint(45001, 250000),     # high
        ])
        quantity = rng.choice([1, 1, 1, 2, 3])
        gross_cents = unit_price_cents * quantity
        heavy = category in ("electronics", "home") and unit_price_cents > 40000
        weight_class = "heavy" if heavy else "standard"
        installments = rng.choice([1, 1, 3, 6, 10, 12]) if listing_type == "premium" else rng.choice([1, 1, 1, 3])
        refund_pct = rng.choice([20, 30, 40, 50, 60, 70]) if status == "partially_refunded" else (100 if status == "refunded" else 0)
        order_date = BASE_DATE + timedelta(days=rng.randint(0, 27))
        orders.append({
            "order_id": f"MLB-{case_num:02d}{seq:04d}",
            "order_date": order_date.isoformat(),
            "status": status,
            "category": category,
            "listing_type": listing_type,
            "weight_class": weight_class,
            "unit_price_cents": unit_price_cents,
            "quantity": quantity,
            "gross_cents": gross_cents,
            "installments": installments,
            "refund_pct": refund_pct,
        })
    return orders


# --------------------------------------------------------------- settlements

class SettlementBook:
    def __init__(self, case_num: int):
        self.case_num = case_num
        self.counter = 0
        self.rows: list[dict] = []

    def add(self, order_id: str, row_date: date, line_type: str,
            gross: int, fee: int, shipping: int) -> dict:
        self.counter += 1
        row = {
            "settlement_id": f"ST-{self.case_num:02d}{self.counter:05d}",
            "order_id": order_id,
            "settlement_date": row_date.isoformat(),
            "type": line_type,
            "gross_cents": gross,
            "fee_cents": fee,
            "shipping_cents": shipping,
            "net_cents": gross + fee + shipping,
        }
        self.rows.append(row)
        return row


def build_settlements(orders: list[dict], schedule: dict, rng: random.Random,
                      case_num: int, force_split: set[str]) -> SettlementBook:
    book = SettlementBook(case_num)
    for order in orders:
        base = date.fromisoformat(order["order_date"])
        lines = expected_settlement_lines(order, schedule)
        for line in lines:
            offset = {"payment": 3, "refund": 10, "chargeback": 15}[line["type"]]
            row_date = base + timedelta(days=offset)
            is_payment = line["type"] == "payment"
            split = is_payment and (
                order["order_id"] in force_split
                or (order["status"] in PAID_STATUSES and rng.random() < 0.10)
            )
            if split:
                gross_1 = half_up(line["gross_cents"] * 60, 100)
                gross_2 = line["gross_cents"] - gross_1
                book.add(order["order_id"], row_date, "payment",
                         gross_1, line["fee_cents"], line["shipping_cents"])
                book.add(order["order_id"], row_date + timedelta(days=7), "payment",
                         gross_2, 0, 0)
            else:
                book.add(order["order_id"], row_date, line["type"],
                         line["gross_cents"], line["fee_cents"], line["shipping_cents"])
    return book


# --------------------------------------------------------------- corruptions

def rows_of(book: SettlementBook, order_id: str, line_type: str | None = None) -> list[dict]:
    return [r for r in book.rows
            if r["order_id"] == order_id and (line_type is None or r["type"] == line_type)]


def pick(rng: random.Random, orders: list[dict], used: set[str], predicate) -> dict | None:
    pool = [o for o in orders if o["order_id"] not in used and predicate(o)]
    if not pool:
        return None
    choice = rng.choice(pool)
    used.add(choice["order_id"])
    return choice


def apply_corruption(kind: str, orders: list[dict], book: SettlementBook,
                     schedule: dict, rng: random.Random, used: set[str],
                     case_num: int, prefer_order: str | None = None) -> dict:
    """Mutate the book to plant divergence `kind`; return truth entry/entries.

    Compound kinds (COMBO_*) corrupt one order in two distinct ways and return
    TWO truth entries - the scan sees a single net delta and the agent must
    decompose it into both root causes. FEE_OVERCHARGE_SUBTLE plants a
    cents-sized overcharge that looks like rounding noise but is above the
    contractual tolerance.
    """

    def truth(order_id: str, impact_cents: int, note: str, type_: str | None = None) -> dict:
        return {"order_id": order_id, "type": type_ or kind,
                "impact_brl": money(impact_cents), "note": note}

    if kind == "MISSING_SETTLEMENT":
        order = pick(rng, orders, used,
                     lambda o: o["status"] in PAID_STATUSES and len(rows_of(book, o["order_id"])) == 1)
        assert order, "no eligible order for MISSING_SETTLEMENT"
        removed = rows_of(book, order["order_id"])
        book.rows = [r for r in book.rows if r["order_id"] != order["order_id"]]
        net = sum(r["net_cents"] for r in removed)
        return truth(order["order_id"], net,
                     f"paid order has no settlement rows; seller is owed {money(net)}")

    if kind == "DUPLICATE_SETTLEMENT":
        order = pick(rng, orders, used,
                     lambda o: o["status"] in PAID_STATUSES and len(rows_of(book, o["order_id"])) == 1)
        assert order, "no eligible order for DUPLICATE_SETTLEMENT"
        src = rows_of(book, order["order_id"], "payment")[0]
        dup_date = date.fromisoformat(src["settlement_date"]) + timedelta(days=1)
        book.add(order["order_id"], dup_date, "payment",
                 src["gross_cents"], src["fee_cents"], src["shipping_cents"])
        return truth(order["order_id"], -src["net_cents"],
                     f"payment settled twice; {money(src['net_cents'])} will be clawed back")

    if kind == "ORPHAN_SETTLEMENT":
        ghost_id = f"MLB-{case_num:02d}9{rng.randint(100, 999)}"
        gross = rng.randint(8000, 90000)
        fee = half_up(gross * 1300, 10000)
        row = book.add(ghost_id, BASE_DATE + timedelta(days=rng.randint(5, 25)),
                       "payment", gross, -fee, 0)
        return truth(ghost_id, -row["net_cents"],
                     "settlement row references an order that does not exist in the seller's book")

    if kind == "FEE_OVERCHARGE":
        order = pick(rng, orders, used,
                     lambda o: o["status"] in PAID_STATUSES
                     and len(rows_of(book, o["order_id"], "payment")) == 1
                     and o["gross_cents"] >= 10000)
        assert order, "no eligible order for FEE_OVERCHARGE"
        row = rows_of(book, order["order_id"], "payment")[0]
        extra_bp = rng.randint(150, 300)
        extra = half_up(order["gross_cents"] * extra_bp, 10000)
        row["fee_cents"] -= extra
        row["net_cents"] -= extra
        return truth(order["order_id"], extra,
                     f"commission charged {extra_bp / 100:.2f} pp above the contracted rate ({money(extra)} extra)")

    if kind == "WRONG_SHIPPING_DEDUCTION":
        order = pick(rng, orders, used,
                     lambda o: o["status"] in PAID_STATUSES
                     and len(rows_of(book, o["order_id"], "payment")) == 1)
        assert order, "no eligible order for WRONG_SHIPPING_DEDUCTION"
        row = rows_of(book, order["order_id"], "payment")[0]
        expected_ship = shipping_cents(order, schedule)
        if expected_ship == 0:
            delta = schedule["shipping_cost_cents"]["standard"]
            note = "shipping deducted on an order below the free-shipping threshold"
        elif order["weight_class"] == "standard":
            delta = schedule["shipping_cost_cents"]["heavy"] - expected_ship
            note = "charged the heavy shipping rate for a standard-weight order"
        else:
            delta = schedule["shipping_cost_cents"]["standard"]
            note = "shipping deducted twice"
        row["shipping_cents"] -= delta
        row["net_cents"] -= delta
        return truth(order["order_id"], delta, f"{note} ({money(delta)} extra)")

    if kind == "REFUND_NOT_SETTLED":
        order = pick(rng, orders, used,
                     lambda o: o["status"] in ("refunded", "partially_refunded")
                     and len(rows_of(book, o["order_id"], "refund")) == 1)
        assert order, "no eligible order for REFUND_NOT_SETTLED"
        refund_row = rows_of(book, order["order_id"], "refund")[0]
        book.rows.remove(refund_row)
        return truth(order["order_id"], refund_row["net_cents"],
                     f"order was refunded but no refund row exists; {money(-refund_row['net_cents'])} was never debited")

    if kind == "REFUND_AMOUNT_MISMATCH":
        order = pick(rng, orders, used,
                     lambda o: (o["order_id"] == prefer_order) if prefer_order else
                     (o["status"] in ("refunded", "partially_refunded")
                      and len(rows_of(book, o["order_id"], "refund")) == 1))
        assert order, "no eligible order for REFUND_AMOUNT_MISMATCH"
        row = rows_of(book, order["order_id"], "refund")[0]
        shorted = row["fee_cents"]  # commission that should have come back
        row["fee_cents"] = 0
        row["net_cents"] -= shorted
        return truth(order["order_id"], shorted,
                     f"refund debited the gross but did not return the commission ({money(shorted)} shorted)")

    if kind == "FEE_OVERCHARGE_SUBTLE":
        order = pick(rng, orders, used,
                     lambda o: o["status"] in PAID_STATUSES
                     and len(rows_of(book, o["order_id"], "payment")) == 1
                     and o["gross_cents"] >= 50000)
        assert order, "no eligible order for FEE_OVERCHARGE_SUBTLE"
        row = rows_of(book, order["order_id"], "payment")[0]
        extra = rng.randint(30, 80)  # cents: looks like rounding, is not
        row["fee_cents"] -= extra
        row["net_cents"] -= extra
        return truth(order["order_id"], extra,
                     f"subtle commission overcharge of {money(extra)} on a "
                     f"{money(order['gross_cents'])} order (above the 0.02 tolerance)",
                     type_="FEE_OVERCHARGE")

    if kind == "COMBO_FEE_SHIP":
        order = pick(rng, orders, used,
                     lambda o: o["status"] in PAID_STATUSES
                     and len(rows_of(book, o["order_id"], "payment")) == 1
                     and o["gross_cents"] >= 10000
                     and o["weight_class"] == "standard"
                     and shipping_cents(o, schedule) > 0)
        assert order, "no eligible order for COMBO_FEE_SHIP"
        row = rows_of(book, order["order_id"], "payment")[0]
        extra_bp = rng.randint(150, 300)
        extra = half_up(order["gross_cents"] * extra_bp, 10000)
        row["fee_cents"] -= extra
        row["net_cents"] -= extra
        ship_delta = (schedule["shipping_cost_cents"]["heavy"]
                      - schedule["shipping_cost_cents"]["standard"])
        row["shipping_cents"] -= ship_delta
        row["net_cents"] -= ship_delta
        return [
            truth(order["order_id"], extra,
                  f"commission charged {extra_bp / 100:.2f} pp above the rate "
                  f"({money(extra)} extra) - compound with a shipping error",
                  type_="FEE_OVERCHARGE"),
            truth(order["order_id"], ship_delta,
                  f"charged the heavy shipping rate on a standard-weight order "
                  f"({money(ship_delta)} extra) - compound with a fee error",
                  type_="WRONG_SHIPPING_DEDUCTION"),
        ]

    if kind == "COMBO_REFUND_FEE":
        order = pick(rng, orders, used,
                     lambda o: o["status"] in ("refunded", "partially_refunded")
                     and len(rows_of(book, o["order_id"], "payment")) == 1
                     and len(rows_of(book, o["order_id"], "refund")) == 1
                     and o["gross_cents"] >= 10000)
        assert order, "no eligible order for COMBO_REFUND_FEE"
        payment_row = rows_of(book, order["order_id"], "payment")[0]
        extra_bp = rng.randint(150, 300)
        extra = half_up(order["gross_cents"] * extra_bp, 10000)
        payment_row["fee_cents"] -= extra
        payment_row["net_cents"] -= extra
        refund_row = rows_of(book, order["order_id"], "refund")[0]
        shorted = refund_row["fee_cents"]
        refund_row["fee_cents"] = 0
        refund_row["net_cents"] -= shorted
        return [
            truth(order["order_id"], extra,
                  f"commission on the payment charged {extra_bp / 100:.2f} pp above "
                  f"the rate ({money(extra)} extra) - compound with a refund error",
                  type_="FEE_OVERCHARGE"),
            truth(order["order_id"], shorted,
                  f"refund debited the gross but did not return the commission "
                  f"({money(shorted)} shorted) - compound with a fee error",
                  type_="REFUND_AMOUNT_MISMATCH"),
        ]

    if kind == "CANCELLED_BUT_SETTLED":
        order = pick(rng, orders, used, lambda o: o["status"] == "cancelled")
        assert order, "no eligible order for CANCELLED_BUT_SETTLED"
        fee = commission_cents(order, schedule)
        ship = shipping_cents(order, schedule)
        row = book.add(order["order_id"],
                       date.fromisoformat(order["order_date"]) + timedelta(days=3),
                       "payment", order["gross_cents"], -fee, -ship)
        return truth(order["order_id"], -row["net_cents"],
                     "cancelled order was settled as if sold; expect a clawback")

    raise ValueError(f"unknown divergence kind: {kind}")


# ------------------------------------------------------------------- writing

ORDER_COLUMNS = ["order_id", "order_date", "status", "category", "listing_type",
                 "weight_class", "unit_price", "quantity", "gross_amount",
                 "installments", "refund_amount"]
SETTLEMENT_COLUMNS = ["settlement_id", "order_id", "settlement_date", "type",
                      "gross_amount", "marketplace_fee", "shipping_fee", "net_amount"]


def write_case(case_dir: Path, orders: list[dict], book: SettlementBook,
               truths: list[dict], meta: dict) -> None:
    case_dir.mkdir(parents=True, exist_ok=True)

    with (case_dir / "orders.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(ORDER_COLUMNS)
        for o in orders:
            refund_amount = half_up(o["gross_cents"] * o["refund_pct"], 100)
            writer.writerow([
                o["order_id"], o["order_date"], o["status"], o["category"],
                o["listing_type"], o["weight_class"], money(o["unit_price_cents"]),
                o["quantity"], money(o["gross_cents"]), o["installments"],
                money(refund_amount),
            ])

    rows = sorted(book.rows, key=lambda r: (r["settlement_date"], r["settlement_id"]))
    with (case_dir / "settlement.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(SETTLEMENT_COLUMNS)
        for r in rows:
            writer.writerow([
                r["settlement_id"], r["order_id"], r["settlement_date"], r["type"],
                money(r["gross_cents"]), money(r["fee_cents"]),
                money(r["shipping_cents"]), money(r["net_cents"]),
            ])

    truths = sorted(truths, key=lambda t: (t["order_id"], t["type"]))
    (case_dir / "truth.json").write_text(
        json.dumps({"case_id": meta["case_id"], "divergences": truths}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    (case_dir / "case.json").write_text(json.dumps(meta, indent=2) + "\n",
                                        encoding="utf-8", newline="\n")


def generate_case(spec: tuple[str, int, str, list[str]], schedule: dict) -> int:
    case_id, n_orders, difficulty, plan = spec
    case_num = int(case_id.split("_")[1])
    rng = random.Random(1000 + case_num)

    orders = build_orders(rng, case_num, n_orders)

    force_split: set[str] = set()
    prefer_order: str | None = None
    if difficulty == "hard":
        # The combo order: partially refunded AND split-settled AND (via the
        # corruption plan below) shorted on the refunded commission.
        combos = [o for o in orders if o["status"] == "partially_refunded"]
        combo = max(combos, key=lambda o: o["gross_cents"])
        force_split.add(combo["order_id"])
        prefer_order = combo["order_id"]

    book = build_settlements(orders, schedule, rng, case_num, force_split)

    used: set[str] = set()
    truths = []
    for kind in plan:
        prefer = prefer_order if kind == "REFUND_AMOUNT_MISMATCH" else None
        result = apply_corruption(kind, orders, book, schedule, rng, used,
                                  case_num, prefer_order=prefer)
        truths.extend(result if isinstance(result, list) else [result])

    meta = {
        "case_id": case_id,
        "seed": 1000 + case_num,
        "n_orders": n_orders,
        "n_settlement_rows": len(book.rows),
        "n_divergences": len(truths),
        "difficulty": difficulty,
    }
    write_case(config.CASES_DIR / case_id, orders, book, truths, meta)
    print(f"{case_id}: {n_orders} orders, {len(book.rows)} settlement rows, "
          f"{len(truths)} divergences ({difficulty})")
    return len(truths)


# ------------------------------------------------- case_13: generalization
#
# The standard cases test execution under complete knowledge: every tool knows
# the full contract. case_13 tests JUDGMENT under acknowledged-incomplete
# knowledge: a commission promo announced only in a plain-text notice. The
# settlement applies the promo correctly, but the calculator tools compute
# from the standard contract, so the deterministic scan flags every eligible
# promo order as a false candidate. The solver must read the notice, dismiss
# the noise, and still find the 2 real divergences hidden in it.
#
# The v3 verifier is NOT used here by design: its canonical impacts encode the
# standard contract, so under a promo it would fight the truth - that limit is
# documented in the README.

PROMO_START = "2026-07-08"
PROMO_END = "2026-07-18"
PROMO_DISCOUNT_BP = 200

NOTICE_TEXT = """# Marketplace seller notices - July 2026

**Notice 2026-07-05 - July Tech Promo.** Electronics orders PLACED between
2026-07-08 and 2026-07-18 (inclusive, by order_date) receive a 2.0 percentage
point commission discount: classic 11% -> 9%, premium 16% -> 14%. The
discount is applied automatically on your settlement statement. All other
charges (low-ticket fixed fee, seller shipping, refund and chargeback
treatment) are unchanged.
"""


def promo_applies(order: dict) -> bool:
    return (order["category"] == "electronics"
            and PROMO_START <= order["order_date"] <= PROMO_END)


def generate_case13(schedule: dict) -> int:
    case_id, case_num, n_orders = "case_13", 13, 150
    rng = random.Random(1013)
    orders = build_orders(rng, case_num, n_orders)

    # Guarantee a meaningful pool of promo-eligible paid orders (the noise).
    eligible = [o for o in orders if o["status"] in PAID_STATUSES][:12]
    for i, order in enumerate(eligible):
        order["category"] = "electronics"
        order["order_date"] = f"2026-07-{8 + (i % 11):02d}"
        order["weight_class"] = "heavy" if order["unit_price_cents"] > 40000 else "standard"

    promo_schedule = copy.deepcopy(schedule)
    for listing in promo_schedule["rates_bp"]["electronics"]:
        promo_schedule["rates_bp"]["electronics"][listing] -= PROMO_DISCOUNT_BP

    book = SettlementBook(case_num)
    for order in orders:
        effective = promo_schedule if promo_applies(order) else schedule
        base = date.fromisoformat(order["order_date"])
        for line in expected_settlement_lines(order, effective):
            offset = {"payment": 3, "refund": 10, "chargeback": 15}[line["type"]]
            book.add(order["order_id"], base + timedelta(days=offset), line["type"],
                     line["gross_cents"], line["fee_cents"], line["shipping_cents"])

    truths = []
    # Real divergence 1: one eligible order was charged the STANDARD rate,
    # i.e. the promised promo discount was not applied.
    victim = eligible[rng.randrange(len(eligible))]
    row = rows_of(book, victim["order_id"], "payment")[0]
    extra = commission_cents(victim, schedule) - commission_cents(victim, promo_schedule)
    row["fee_cents"] = -commission_cents(victim, schedule)
    row["net_cents"] = row["gross_cents"] + row["fee_cents"] + row["shipping_cents"]
    truths.append({"order_id": victim["order_id"], "type": "FEE_OVERCHARGE",
                   "impact_brl": money(extra),
                   "note": "July Tech Promo discount was NOT applied: charged the standard "
                           f"rate instead of the promotional one ({money(extra)} extra)"})

    # Real divergence 2: a plain refund shorted on a NON-electronics order.
    refunded = [o for o in orders
                if o["status"] in ("refunded", "partially_refunded")
                and o["category"] != "electronics"
                and len(rows_of(book, o["order_id"], "refund")) == 1]
    target = rng.choice(refunded)
    refund_row = rows_of(book, target["order_id"], "refund")[0]
    shorted = refund_row["fee_cents"]
    refund_row["fee_cents"] = 0
    refund_row["net_cents"] -= shorted
    truths.append({"order_id": target["order_id"], "type": "REFUND_AMOUNT_MISMATCH",
                   "impact_brl": money(shorted),
                   "note": f"refund debited the gross but did not return the commission "
                           f"({money(shorted)} shorted)"})

    meta = {
        "case_id": case_id, "seed": 1013, "n_orders": n_orders,
        "n_settlement_rows": len(book.rows), "n_divergences": len(truths),
        "difficulty": "generalization",
        "promo_eligible_orders": sorted(o["order_id"] for o in eligible),
    }
    write_case(config.CASES_DIR / case_id, orders, book, truths, meta)
    (config.CASES_DIR / case_id / "notices.md").write_text(NOTICE_TEXT, encoding="utf-8",
                                                           newline="\n")
    print(f"{case_id}: {n_orders} orders, {len(book.rows)} settlement rows, "
          f"{len(truths)} REAL divergences + {len(eligible)} promo orders as scan noise "
          f"(generalization)")
    return len(truths)


def main() -> None:
    schedule = load_fee_schedule()
    if config.CASES_DIR.exists():
        shutil.rmtree(config.CASES_DIR)
    total = sum(generate_case(spec, schedule) for spec in CASE_SPECS)
    total += generate_case13(schedule)
    print(f"\n{len(CASE_SPECS) + 1} cases, {total} planted divergences total.")


if __name__ == "__main__":
    main()
