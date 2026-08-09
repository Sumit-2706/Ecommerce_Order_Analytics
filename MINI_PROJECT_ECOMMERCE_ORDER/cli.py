"""
cli.py
------
Intern Mini Project - E-Commerce Order Analytics System
Author: Sumit Kumar Singh

A simple command-line tool that:
  1. Takes user input for report type (daily/weekly/monthly)
  2. Takes a date range as input
  3. Connects to the SQLite database
  4. Generates a summary report: total orders, revenue, unique customers,
     top 3 products, and a % comparison with the equivalent previous period

Uses ONLY the standard library (sqlite3, datetime, argparse) as required
by the assignment ("No external libraries except sqlite3").
"""

import sqlite3
import sys
import argparse
from datetime import datetime, timedelta

DB_PATH = "database.db"


def parse_date(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d")


def get_period_stats(conn, start: str, end: str):
    """Return (total_orders, total_revenue, unique_customers, top_3_products) for [start, end)."""
    cur = conn.cursor()

    cur.execute("""
        SELECT COUNT(DISTINCT o.order_id), COUNT(DISTINCT o.customer_id)
        FROM orders o
        WHERE date(o.order_date) >= date(?) AND date(o.order_date) < date(?)
    """, (start, end))
    total_orders, unique_customers = cur.fetchone()
    total_orders = total_orders or 0
    unique_customers = unique_customers or 0

    cur.execute("""
        SELECT COALESCE(SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)), 0)
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        WHERE date(o.order_date) >= date(?) AND date(o.order_date) < date(?)
    """, (start, end))
    total_revenue = cur.fetchone()[0] or 0

    cur.execute("""
        SELECT p.product_name,
               SUM(oi.quantity * oi.unit_price * (1 - oi.discount_percent / 100.0)) AS rev
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.order_id
        JOIN products p ON p.product_id = oi.product_id
        WHERE date(o.order_date) >= date(?) AND date(o.order_date) < date(?)
        GROUP BY p.product_name
        ORDER BY rev DESC
        LIMIT 3
    """, (start, end))
    top_products = [row[0] for row in cur.fetchall()]

    return total_orders, total_revenue, unique_customers, top_products


def pct_change(current, previous):
    if previous in (0, None):
        return None
    return ((current - previous) / previous) * 100.0


def previous_period(start_dt: datetime, end_dt: datetime):
    """Given [start, end), return the immediately preceding period of equal length."""
    length = end_dt - start_dt
    prev_end = start_dt
    prev_start = start_dt - length
    return prev_start, prev_end


def generate_report(report_type: str, start_date: str, end_date: str):
    start_dt = parse_date(start_date)
    end_dt = parse_date(end_date) + timedelta(days=1)  # make end inclusive

    prev_start_dt, prev_end_dt = previous_period(start_dt, end_dt)

    conn = sqlite3.connect(DB_PATH)

    orders, revenue, customers, top3 = get_period_stats(
        conn, start_dt.strftime("%Y-%m-%d"), end_dt.strftime("%Y-%m-%d"))
    p_orders, p_revenue, p_customers, _ = get_period_stats(
        conn, prev_start_dt.strftime("%Y-%m-%d"), prev_end_dt.strftime("%Y-%m-%d"))

    conn.close()

    orders_change = pct_change(orders, p_orders)
    revenue_change = pct_change(revenue, p_revenue)
    customers_change = pct_change(customers, p_customers)

    print("=" * 55)
    print("ECOMMERCE ORDER ANALYTICS")
    print("=" * 55)
    print(f"\nReport Type : {report_type.capitalize()}")
    print(f"\nStart Date  : {start_date}")
    print(f"End Date    : {end_date}")
    print("\n" + "-" * 55)
    print(f"\nTotal Orders      : {orders}")
    print(f"Total Revenue     : Rs. {revenue:,.2f}")
    print(f"Unique Customers  : {customers}")
    print("\nTop 3 Products")
    if top3:
        for i, name in enumerate(top3, 1):
            print(f"{i}. {name}")
    else:
        print("  (no orders in this period)")

    print("\nComparison with Previous Period")
    print(f"Previous period    : {prev_start_dt.strftime('%Y-%m-%d')} to "
          f"{(prev_end_dt - timedelta(days=1)).strftime('%Y-%m-%d')}")

    def fmt_change(c):
        return f"{c:+.2f}%" if c is not None else "N/A (no prior data)"

    print(f"Orders Change      : {fmt_change(orders_change)}")
    print(f"Revenue Change     : {fmt_change(revenue_change)}")
    print(f"Customers Change   : {fmt_change(customers_change)}")
    print("=" * 55)


def interactive_mode():
    print("=" * 55)
    print("ECOMMERCE ORDER ANALYTICS - CLI REPORT TOOL")
    print("=" * 55)
    report_type = input("\nReport type (daily/weekly/monthly): ").strip().lower()
    while report_type not in ("daily", "weekly", "monthly"):
        report_type = input("Please enter daily, weekly, or monthly: ").strip().lower()

    start_date = input("Start date (YYYY-MM-DD): ").strip()
    end_date = input("End date (YYYY-MM-DD): ").strip()

    try:
        generate_report(report_type, start_date, end_date)
    except ValueError as e:
        print(f"\nInvalid date format. Please use YYYY-MM-DD. Details: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="E-commerce order analytics CLI report tool")
    parser.add_argument("--type", choices=["daily", "weekly", "monthly"], help="Report type")
    parser.add_argument("--start", help="Start date YYYY-MM-DD")
    parser.add_argument("--end", help="End date YYYY-MM-DD")
    args = parser.parse_args()

    if args.type and args.start and args.end:
        generate_report(args.type, args.start, args.end)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()
