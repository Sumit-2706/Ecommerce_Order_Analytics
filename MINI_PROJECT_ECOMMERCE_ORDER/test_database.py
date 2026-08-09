"""
test_database.py
-----------------
Intern Mini Project - E-Commerce Order Analytics System
Author: Sumit Kumar Singh

Quick sanity check on database.db: confirms tables exist, row counts match
the cleaned CSVs, and foreign keys are internally consistent.
Run this right after create_database.py.
"""

import sqlite3
import pandas as pd

DB_PATH = "database.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    print("=" * 60)
    print("DATABASE VERIFICATION")
    print("=" * 60)

    # 1. tables exist
    tables = [r[0] for r in cur.execute(
        "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    expected = {"customers", "products", "orders", "order_items"}
    print(f"\nTables found: {tables}")
    assert expected.issubset(set(tables)), "Missing expected tables!"
    print("  [OK] all 4 expected tables exist")

    # 2. row counts match the cleaned CSVs
    for table, csv_path in [
        ("customers", "cleaned_data/customers.csv"),
        ("products", "cleaned_data/products.csv"),
        ("orders", "cleaned_data/orders.csv"),
        ("order_items", "cleaned_data/order_items.csv"),
    ]:
        db_count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        csv_count = len(pd.read_csv(csv_path))
        status = "OK" if db_count == csv_count else "MISMATCH"
        print(f"  [{status}] {table}: db={db_count} csv={csv_count}")

    # 3. referential integrity inside the DB
    orphan_items = cur.execute("""
        SELECT COUNT(*) FROM order_items oi
        LEFT JOIN orders o ON o.order_id = oi.order_id
        WHERE o.order_id IS NULL
    """).fetchone()[0]
    print(f"\n  [{'OK' if orphan_items == 0 else 'FAIL'}] orphan order_items in DB: {orphan_items} (expected 0)")

    orphan_orders_customers = cur.execute("""
        SELECT COUNT(*) FROM orders o
        LEFT JOIN customers c ON c.customer_id = o.customer_id
        WHERE o.customer_id IS NOT NULL AND c.customer_id IS NULL
    """).fetchone()[0]
    print(f"  [{'OK' if orphan_orders_customers == 0 else 'FAIL'}] orders with unknown customer_id: {orphan_orders_customers} (expected 0)")

    # 4. quick row samples
    print("\nSample rows from each table:")
    for table in ["customers", "products", "orders", "order_items"]:
        print(f"\n-- {table} --")
        for row in cur.execute(f"SELECT * FROM {table} LIMIT 3").fetchall():
            print(" ", row)

    conn.close()
    print("\n" + "=" * 60)
    print("Database verification complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
