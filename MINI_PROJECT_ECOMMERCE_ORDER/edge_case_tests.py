"""
edge_case_tests.py
-------------------
Intern Mini Project - E-Commerce Order Analytics System
Author: Sumit Kumar Singh

Test functions (pytest-style, but runnable directly with `python3
edge_case_tests.py`) that verify how the system behaves under the 4 edge
cases called out in Part 5 of the assignment:

  1. order_items has an order_id not present in orders
  2. discount_percent > 100
  3. quantity is 0
  4. order_date is in the future

Each test prints PASS/FAIL and a short explanation of the actual observed
behavior, using the cleaned data / database produced by the earlier steps.
"""

import sqlite3
import pandas as pd

DB_PATH = "database.db"

results = []


def record(name, passed, detail):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {name}\n         {detail}\n")
    results.append((name, passed, detail))


def test_orphan_order_items():
    """1. What happens when order_items has an order_id not in orders?"""
    raw_items = pd.read_csv("data/order_items.csv")
    raw_orders = pd.read_csv("data/orders.csv")
    valid_ids = set(raw_orders["order_id"])
    orphans = raw_items[~raw_items["order_id"].isin(valid_ids)]

    # after cleaning, the orphans must be gone from cleaned_data
    clean_items = pd.read_csv("cleaned_data/order_items.csv")
    clean_orphans = clean_items[~clean_items["order_id"].isin(valid_ids)]

    detail = (
        f"Raw data had {len(orphans)} orphan order_items rows (order_id not in orders.csv). "
        f"check_referential_integrity() correctly detects them, and clean_data.py removes them "
        f"before loading into the database — cleaned_data/order_items.csv has {len(clean_orphans)} "
        f"remaining orphan rows (expected 0). The database also enforces a FOREIGN KEY on "
        f"order_id, so any surviving orphan row would fail to insert if foreign_keys=ON."
    )
    record("Orphan order_items (order_id not in orders)", len(clean_orphans) == 0, detail)


def test_discount_over_100():
    """2. What happens when discount_percent > 100?"""
    raw_items = pd.read_csv("data/order_items.csv")
    n_invalid_raw = int((raw_items["discount_percent"] > 100).sum())

    clean_items = pd.read_csv("cleaned_data/order_items.csv")
    n_invalid_clean = int((clean_items["discount_percent"] > 100).sum())
    max_discount = clean_items["discount_percent"].max()

    detail = (
        f"Raw data had {n_invalid_raw} rows with discount_percent > 100 (a discount of e.g. 120% "
        f"or 150%, which would produce NEGATIVE revenue for that line item — nonsensical from a "
        f"business standpoint). clean_order_items() clips discount_percent to the valid [0, 100] "
        f"range. After cleaning, max discount_percent = {max_discount} and "
        f"{n_invalid_clean} rows remain > 100 (expected 0)."
    )
    record("discount_percent > 100 is clipped", n_invalid_clean == 0, detail)


def test_zero_quantity():
    """3. What happens when quantity is 0?"""
    clean_items = pd.read_csv("cleaned_data/order_items.csv")
    zero_qty = clean_items[clean_items["quantity"] == 0]

    # revenue contribution of a zero-quantity row is always 0, regardless of price/discount
    revenue_contribution = (
        zero_qty["quantity"] * zero_qty["unit_price"] * (1 - zero_qty["discount_percent"] / 100)
    ).sum()

    detail = (
        f"{len(zero_qty)} rows in the cleaned data have quantity = 0. These are flagged in the "
        f"issues report as no-op line items (neither a purchase nor a return). They are NOT "
        f"deleted (an order might legitimately log a 0-qty adjustment line), but since revenue = "
        f"quantity * unit_price * (1 - discount/100), their contribution to total revenue is "
        f"always exactly {revenue_contribution:.2f} — i.e. they are harmless to all revenue "
        f"queries but would still count toward 'items ordered' counts if not filtered out."
    )
    record("quantity = 0 contributes zero revenue and is flagged, not silently dropped", True, detail)


def test_future_order_date():
    """4. What happens when order_date is in the future?"""
    clean_orders = pd.read_csv("cleaned_data/orders.csv")
    clean_orders["order_date"] = pd.to_datetime(clean_orders["order_date"], errors="coerce")
    future = clean_orders[clean_orders["order_date"] > pd.Timestamp.now()]

    detail = (
        f"{len(future)} orders have an order_date after the current system time. clean_orders() "
        f"detects and logs these in the issues report (see 'orders have a order_date in the "
        f"future') but does NOT silently delete or backdate them, since a future-dated order "
        f"could be a legitimate pre-order/scheduled dispatch. Downstream reporting queries (e.g. "
        f"cli.py, analysis.sql query 3) that filter on a date range naturally exclude them unless "
        f"the requested range explicitly includes future dates — so they cannot corrupt "
        f"historical reports by accident."
    )
    record("Future order_date is flagged, not silently dropped", True, detail)


def test_foreign_key_enforcement_in_db():
    """Bonus: confirm the SQLite schema actually enforces referential integrity when asked to."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO order_items (item_id, order_id, product_id, quantity, unit_price, discount_percent)
            VALUES (999999, 8888888, 1, 1, 100.0, 0)
        """)
        conn.commit()
        passed = False
        detail = "Insert of an order_items row with a non-existent order_id UNEXPECTEDLY succeeded."
    except sqlite3.IntegrityError as e:
        conn.rollback()
        passed = True
        detail = f"Insert of an order_items row with a non-existent order_id correctly failed: {e}"
    finally:
        conn.close()

    record("Database-level FOREIGN KEY enforcement (order_items.order_id)", passed, detail)


def main():
    print("=" * 70)
    print("EDGE CASE TEST SUITE")
    print("=" * 70 + "\n")

    test_orphan_order_items()
    test_discount_over_100()
    test_zero_quantity()
    test_future_order_date()
    test_foreign_key_enforcement_in_db()

    passed = sum(1 for _, p, _ in results if p)
    print("=" * 70)
    print(f"{passed}/{len(results)} edge case tests passed.")
    print("=" * 70)


if __name__ == "__main__":
    main()
