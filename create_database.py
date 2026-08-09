"""
create_database.py
-------------------
Intern Mini Project - E-Commerce Order Analytics System
Author: Sumit Kumar Singh

Loads the cleaned CSVs from ./cleaned_data/ into a SQLite database
(database.db) with a proper schema, primary keys, foreign keys and
indexes so the analysis queries in analysis.sql run efficiently.
"""

import sqlite3
import pandas as pd
import os

DB_PATH = "database.db"
CLEAN_DIR = "cleaned_data"

SCHEMA = """
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    customer_id       INTEGER PRIMARY KEY,
    customer_name      TEXT NOT NULL,
    email               TEXT,
    registration_date   TEXT,
    customer_type       TEXT CHECK (customer_type IN ('REGULAR','PREMIUM','VIP'))
);

CREATE TABLE products (
    product_id     INTEGER PRIMARY KEY,
    product_name    TEXT NOT NULL,
    category        TEXT,
    subcategory     TEXT,
    cost_price      REAL
);

CREATE TABLE orders (
    order_id      INTEGER PRIMARY KEY,
    customer_id    INTEGER,
    order_date     TEXT,
    status         TEXT CHECK (status IN ('PLACED','SHIPPED','DELIVERED','CANCELLED','RETURNED')),
    region_code    TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE order_items (
    item_id            INTEGER PRIMARY KEY,
    order_id            INTEGER NOT NULL,
    product_id          INTEGER,
    quantity             INTEGER,
    unit_price           REAL,
    discount_percent     REAL,
    FOREIGN KEY (order_id) REFERENCES orders(order_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE INDEX idx_orders_customer ON orders(customer_id);
CREATE INDEX idx_orders_date ON orders(order_date);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_items_order ON order_items(order_id);
CREATE INDEX idx_items_product ON order_items(product_id);
"""


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.executescript(SCHEMA)
    conn.commit()
    print("Schema created (customers, products, orders, order_items + indexes).")

    customers = pd.read_csv(f"{CLEAN_DIR}/customers.csv")
    products = pd.read_csv(f"{CLEAN_DIR}/products.csv")
    orders = pd.read_csv(f"{CLEAN_DIR}/orders.csv")
    order_items = pd.read_csv(f"{CLEAN_DIR}/order_items.csv")

    customers.to_sql("customers", conn, if_exists="append", index=False)
    products.to_sql("products", conn, if_exists="append", index=False)
    orders.to_sql("orders", conn, if_exists="append", index=False)
    order_items.to_sql("order_items", conn, if_exists="append", index=False)
    conn.commit()

    for table in ["customers", "products", "orders", "order_items"]:
        count = cur.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  loaded {table:<14}: {count} rows")

    conn.close()
    print(f"\nDatabase ready -> {DB_PATH}")


if __name__ == "__main__":
    main()
