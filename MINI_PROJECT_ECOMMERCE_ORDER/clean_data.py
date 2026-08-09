"""
clean_data.py
-------------
Intern Mini Project - E-Commerce Order Analytics System
Author: Sumit Kumar Singh

Reads the raw CSVs from ./data/, cleans them, and writes the cleaned
versions to ./cleaned_data/. Also writes a plain-text issues report to
./reports/issues_report.txt summarizing everything that was found/fixed.

Functions (as required by the assignment):
    clean_orders()               -> fixes date formats, handles NULL customer_ids
    clean_products()              -> normalizes product names (trim + title case)
    validate_emails()             -> returns list of customer_ids with invalid emails
    check_referential_integrity() -> finds order_items referencing non-existent orders
"""

import os
import re
import pandas as pd
from datetime import datetime

DATA_DIR = "data"
OUT_DIR = "cleaned_data"
REPORT_DIR = "reports"

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(REPORT_DIR, exist_ok=True)

issues = []  # collects human-readable lines for the final report


def log(msg):
    print(msg)
    issues.append(msg)


# --------------------------------------------------------------------------
# 1. ORDERS
# --------------------------------------------------------------------------
def parse_mixed_date(value):
    """Try multiple known formats and normalize to YYYY-MM-DD HH:MM:SS."""
    if pd.isna(value) or str(value).strip() == "":
        return pd.NaT
    value = str(value).strip()
    formats = ["%Y-%m-%d %H:%M:%S", "%d-%m-%Y", "%d-%m-%Y %H:%M:%S", "%Y-%m-%d"]
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    # last resort: let pandas try to infer it
    try:
        return pd.to_datetime(value)
    except Exception:
        return pd.NaT


def clean_orders(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    total = len(df)

    # --- fix date formats ---
    bad_format_mask = ~df["order_date"].astype(str).str.match(
        r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
    )
    n_bad_dates = int(bad_format_mask.sum())
    df["order_date"] = df["order_date"].apply(parse_mixed_date)
    n_unparseable = int(df["order_date"].isna().sum())
    df["order_date"] = df["order_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    log(f"[orders] {n_bad_dates} rows had a non-standard date format -> normalized to YYYY-MM-DD HH:MM:SS")
    if n_unparseable:
        log(f"[orders] {n_unparseable} order_date values could not be parsed at all and were set to NULL")

    # --- future dates (flag only, don't delete: business decision) ---
    parsed = pd.to_datetime(df["order_date"], errors="coerce")
    future_mask = parsed > pd.Timestamp.now()
    n_future = int(future_mask.sum())
    if n_future:
        log(f"[orders] {n_future} orders have a order_date in the future (flagged, not removed)")

    # --- handle NULL customer_id ---
    df["customer_id"] = df["customer_id"].replace("", pd.NA)
    n_null_customer = int(df["customer_id"].isna().sum())
    log(f"[orders] {n_null_customer} / {total} orders ({n_null_customer/total:.1%}) have a missing customer_id -> kept as NULL, excluded from customer-level aggregates")
    # keep as nullable Int64 so it stays a whole number but supports NA
    df["customer_id"] = df["customer_id"].astype("Int64")

    # --- validate status values ---
    valid_status = {"PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"}
    bad_status = df[~df["status"].isin(valid_status)]
    if len(bad_status):
        log(f"[orders] {len(bad_status)} rows had an unrecognized status value")

    return df


# --------------------------------------------------------------------------
# 2. PRODUCTS
# --------------------------------------------------------------------------
def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    before = df["product_name"].copy()
    df["product_name"] = df["product_name"].astype(str).str.strip().str.title()
    n_changed = int((before.astype(str) != df["product_name"]).sum())
    log(f"[products] {n_changed} product names had extra spaces / inconsistent casing -> trimmed + title-cased")

    # normalize category / subcategory casing too, for consistency
    df["category"] = df["category"].astype(str).str.strip().str.title()
    df["subcategory"] = df["subcategory"].astype(str).str.strip().str.title()

    # sanity check on cost_price
    n_negative_cost = int((df["cost_price"] < 0).sum())
    if n_negative_cost:
        log(f"[products] {n_negative_cost} products had a negative cost_price (flagged)")

    return df


# --------------------------------------------------------------------------
# 3. CUSTOMERS / EMAIL VALIDATION
# --------------------------------------------------------------------------
EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validate_emails(df: pd.DataFrame) -> list:
    """Return list of customer_ids whose email is invalid (missing @ or domain)."""
    invalid_mask = ~df["email"].astype(str).str.match(EMAIL_REGEX)
    invalid_ids = df.loc[invalid_mask, "customer_id"].tolist()
    log(f"[customers] {len(invalid_ids)} / {len(df)} customers ({len(invalid_ids)/len(df):.1%}) have an invalid email address")
    return invalid_ids


def clean_customers(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["customer_name"] = df["customer_name"].astype(str).str.strip()
    df["registration_date"] = pd.to_datetime(df["registration_date"], errors="coerce")
    df["registration_date"] = df["registration_date"].dt.strftime("%Y-%m-%d %H:%M:%S")
    return df


# --------------------------------------------------------------------------
# 4. ORDER ITEMS / REFERENTIAL INTEGRITY
# --------------------------------------------------------------------------
def clean_order_items(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    n_negative = int((df["quantity"] < 0).sum())
    log(f"[order_items] {n_negative} rows have negative quantity -> treated as returns, kept in data")

    n_zero = int((df["quantity"] == 0).sum())
    if n_zero:
        log(f"[order_items] {n_zero} rows have quantity = 0 (flagged as invalid/no-op line items)")

    n_bad_discount = int(((df["discount_percent"] < 0) | (df["discount_percent"] > 100)).sum())
    if n_bad_discount:
        log(f"[order_items] {n_bad_discount} rows have discount_percent outside the valid 0-100 range -> clipped to [0, 100]")
        df["discount_percent"] = df["discount_percent"].clip(lower=0, upper=100)

    return df


def check_referential_integrity(order_items: pd.DataFrame, orders: pd.DataFrame) -> pd.DataFrame:
    """Return the rows of order_items whose order_id does not exist in orders."""
    valid_ids = set(orders["order_id"])
    orphans = order_items[~order_items["order_id"].isin(valid_ids)]
    log(f"[integrity] {len(orphans)} order_items rows reference an order_id that does not exist in orders.csv")
    return orphans


# --------------------------------------------------------------------------
# MAIN
# --------------------------------------------------------------------------
def main():
    log("=" * 70)
    log("E-COMMERCE DATA CLEANING REPORT")
    log(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log("=" * 70)

    orders_raw = pd.read_csv(f"{DATA_DIR}/orders.csv", dtype={"customer_id": "string"})
    order_items_raw = pd.read_csv(f"{DATA_DIR}/order_items.csv")
    products_raw = pd.read_csv(f"{DATA_DIR}/products.csv")
    customers_raw = pd.read_csv(f"{DATA_DIR}/customers.csv")

    log("\n--- Cleaning orders.csv ---")
    orders_clean = clean_orders(orders_raw)

    log("\n--- Cleaning products.csv ---")
    products_clean = clean_products(products_raw)

    log("\n--- Cleaning customers.csv ---")
    customers_clean = clean_customers(customers_raw)
    invalid_email_ids = validate_emails(customers_clean)

    log("\n--- Cleaning order_items.csv ---")
    order_items_clean = clean_order_items(order_items_raw)

    log("\n--- Referential integrity check ---")
    orphans = check_referential_integrity(order_items_clean, orders_clean)
    # remove orphan rows from the cleaned file since they can't join to any order
    order_items_clean = order_items_clean[~order_items_clean["item_id"].isin(orphans["item_id"])]
    log(f"[integrity] {len(orphans)} orphan rows removed from cleaned_data/order_items.csv")

    # --- write cleaned files ---
    orders_clean.to_csv(f"{OUT_DIR}/orders.csv", index=False)
    products_clean.to_csv(f"{OUT_DIR}/products.csv", index=False)
    customers_clean.to_csv(f"{OUT_DIR}/customers.csv", index=False)
    order_items_clean.to_csv(f"{OUT_DIR}/order_items.csv", index=False)

    log(f"\nCleaned files written to ./{OUT_DIR}/")
    log(f"  orders.csv       : {len(orders_clean)} rows")
    log(f"  order_items.csv  : {len(order_items_clean)} rows")
    log(f"  products.csv     : {len(products_clean)} rows")
    log(f"  customers.csv    : {len(customers_clean)} rows")

    if invalid_email_ids:
        log(f"\nCustomer IDs with invalid emails: {invalid_email_ids}")

    with open(f"{REPORT_DIR}/issues_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(issues))

    print(f"\nFull issues report saved -> {REPORT_DIR}/issues_report.txt")


if __name__ == "__main__":
    main()
