"""
generate_data.py
-----------------
Intern Mini Project - E-Commerce Order Analytics System
Author: Sumit Kumar Singh
Intern: Celebal Excellence Intern (CEI), Celebal Technologies

Generates 4 raw CSV files (orders, order_items, products, customers) with
realistic fake data AND intentionally injected data-quality issues so that
the cleaning step (clean_data.py) has real problems to solve.

Intentional issues injected (as required by the assignment):
  - 5% of orders have a NULL customer_id
  - 3% of order_items have negative quantity (treated as returns)
  - Some orders have order_date in the wrong format (DD-MM-YYYY instead of
    YYYY-MM-DD HH:MM:SS)
  - Some product names have extra spaces / mixed case
  - 2% of customer emails are invalid (missing '@' or missing domain)

Referential integrity for order_items -> orders is guaranteed by always
sampling order_id from the pool of order_ids that were actually generated
in orders.csv (see build_order_items()).
"""

import csv
import random
from datetime import datetime, timedelta

from faker import Faker

fake = Faker("en_IN")
Faker.seed(42)
random.seed(42)

N_CUSTOMERS = 600
N_PRODUCTS = 150
N_ORDERS = 3000
N_ORDER_ITEMS = 7500

STATUSES = ["PLACED", "SHIPPED", "DELIVERED", "CANCELLED", "RETURNED"]
STATUS_WEIGHTS = [0.15, 0.20, 0.45, 0.10, 0.10]
REGIONS = ["NORTH", "SOUTH", "EAST", "WEST", "CENTRAL"]
CUSTOMER_TYPES = ["REGULAR", "PREMIUM", "VIP"]
CUSTOMER_TYPE_WEIGHTS = [0.65, 0.25, 0.10]

CATEGORIES = {
    "Electronics": ["Mobiles", "Laptops", "Accessories", "Cameras", "Audio"],
    "Clothing": ["Men", "Women", "Kids", "Footwear", "Winterwear"],
    "Home": ["Kitchen", "Furniture", "Decor", "Appliances", "Storage"],
    "Books": ["Fiction", "Non-Fiction", "Academic", "Comics", "Self-Help"],
}

PRODUCT_NAME_POOL = {
    "Mobiles": ["Smartphone X1", "Smartphone Pro Max", "Budget Phone Lite"],
    "Laptops": ["Ultrabook Air", "Gaming Laptop Z", "Business Notebook"],
    "Accessories": ["Wireless Mouse", "Bluetooth Keyboard", "USB-C Hub"],
    "Cameras": ["DSLR Camera 200D", "Action Camera Go", "Instant Camera Mini"],
    "Audio": ["Bluetooth Speaker", "Noise Cancelling Headphones", "Earbuds Pro"],
    "Men": ["Cotton T-Shirt", "Formal Shirt", "Denim Jeans"],
    "Women": ["Cotton Kurti", "Summer Dress", "Ethnic Saree"],
    "Kids": ["Kids T-Shirt", "School Backpack", "Kids Shoes"],
    "Footwear": ["Running Shoes", "Leather Sandals", "Sports Sneakers"],
    "Winterwear": ["Woolen Sweater", "Puffer Jacket", "Fleece Hoodie"],
    "Kitchen": ["Non-Stick Pan", "Electric Kettle", "Mixer Grinder"],
    "Furniture": ["Study Table", "Office Chair", "Bookshelf"],
    "Decor": ["Wall Clock", "Table Lamp", "Photo Frame Set"],
    "Appliances": ["Microwave Oven", "Air Fryer", "Room Heater"],
    "Storage": ["Plastic Storage Box", "Wardrobe Organizer", "Shoe Rack"],
    "Fiction": ["The Silent Valley", "Whispers of Time", "Beyond the Horizon"],
    "Non-Fiction": ["The Growth Mindset", "Atomic Habits Guide", "Money Matters"],
    "Academic": ["Data Structures Handbook", "SQL for Beginners", "Python Crash Course"],
    "Comics": ["Superhero Chronicles Vol 1", "Manga Adventures", "Classic Comic Pack"],
    "Self-Help": ["Focus and Flow", "The Productivity Code", "Mindful Living"],
}


def messy_name(name: str) -> str:
    """Randomly mess up a product name with extra spaces / mixed case."""
    r = random.random()
    if r < 0.15:
        name = "  " + name + "   "
    if r < 0.10:
        name = name.upper()
    elif 0.10 <= r < 0.20:
        name = name.lower()
    return name


def build_customers():
    rows = []
    for cid in range(1, N_CUSTOMERS + 1):
        name = fake.name()
        email = f"{name.lower().replace(' ', '.')}{cid}@example.com"

        # 2% invalid emails
        if random.random() < 0.02:
            bad_type = random.choice(["no_at", "no_domain"])
            if bad_type == "no_at":
                email = email.replace("@", "")
            else:
                email = email.split("@")[0] + "@"

        reg_date = fake.date_time_between(start_date="-3y", end_date="-1M")
        ctype = random.choices(CUSTOMER_TYPES, weights=CUSTOMER_TYPE_WEIGHTS)[0]

        rows.append({
            "customer_id": cid,
            "customer_name": name,
            "email": email,
            "registration_date": reg_date.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_type": ctype,
        })
    return rows


def build_products():
    rows = []
    pid = 1
    all_subcats = [(cat, sub) for cat, subs in CATEGORIES.items() for sub in subs]
    while pid <= N_PRODUCTS:
        cat, sub = random.choice(all_subcats)
        base_name = random.choice(PRODUCT_NAME_POOL[sub])
        name = f"{base_name} {random.choice(['', 'V2', 'Plus', 'Lite', '2026'])}".strip()
        name = messy_name(name)
        cost_price = round(random.uniform(99, 45000), 2)
        rows.append({
            "product_id": pid,
            "product_name": name,
            "category": cat,
            "subcategory": sub,
            "cost_price": cost_price,
        })
        pid += 1
    return rows


def build_orders(customers):
    rows = []
    customer_ids = [c["customer_id"] for c in customers]
    for oid in range(1, N_ORDERS + 1):
        # 5% missing customer_id
        if random.random() < 0.05:
            cust_id = ""  # empty -> will be read as NaN/NULL by pandas
        else:
            cust_id = random.choice(customer_ids)

        order_dt = fake.date_time_between(start_date="-13M", end_date="now")

        # some orders in the future (edge case testing)
        if random.random() < 0.005:
            order_dt = datetime.now() + timedelta(days=random.randint(1, 30))

        # ~8% of dates written in wrong format DD-MM-YYYY (no time component)
        if random.random() < 0.08:
            date_str = order_dt.strftime("%d-%m-%Y")
        else:
            date_str = order_dt.strftime("%Y-%m-%d %H:%M:%S")

        status = random.choices(STATUSES, weights=STATUS_WEIGHTS)[0]
        region = random.choice(REGIONS)

        rows.append({
            "order_id": oid,
            "customer_id": cust_id,
            "order_date": date_str,
            "status": status,
            "region_code": region,
        })
    return rows


def build_order_items(orders, products):
    rows = []
    order_ids = [o["order_id"] for o in orders]
    product_ids = [p["product_id"] for p in products]

    for item_id in range(1, N_ORDER_ITEMS + 1):
        order_id = random.choice(order_ids)  # guarantees referential integrity
        product_id = random.choice(product_ids)
        quantity = random.randint(1, 5)

        # 3% negative quantity -> represents a return
        if random.random() < 0.03:
            quantity = -abs(quantity)

        # occasional zero quantity edge case
        if random.random() < 0.005:
            quantity = 0

        unit_price = round(random.uniform(50, 50000), 2)
        discount_percent = random.choice([0, 0, 0, 5, 10, 15, 20, 25, 30])

        # rare invalid discount > 100 (edge case testing)
        if random.random() < 0.003:
            discount_percent = random.choice([120, 150])

        rows.append({
            "item_id": item_id,
            "order_id": order_id,
            "product_id": product_id,
            "quantity": quantity,
            "unit_price": unit_price,
            "discount_percent": discount_percent,
        })

    # inject a handful of order_items that reference a NON-existent order
    # (so check_referential_integrity() has something real to catch)
    max_order_id = max(order_ids)
    for extra in range(5):
        rows.append({
            "item_id": N_ORDER_ITEMS + extra + 1,
            "order_id": max_order_id + 1000 + extra,  # does not exist in orders.csv
            "product_id": random.choice(product_ids),
            "quantity": random.randint(1, 3),
            "unit_price": round(random.uniform(50, 5000), 2),
            "discount_percent": random.choice([0, 10, 20]),
        })

    return rows


def write_csv(path, rows, fieldnames):
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"  wrote {len(rows):>6} rows -> {path}")


def main():
    print("Generating raw e-commerce data...")
    customers = build_customers()
    products = build_products()
    orders = build_orders(customers)
    order_items = build_order_items(orders, products)

    write_csv("data/customers.csv", customers,
              ["customer_id", "customer_name", "email", "registration_date", "customer_type"])
    write_csv("data/products.csv", products,
              ["product_id", "product_name", "category", "subcategory", "cost_price"])
    write_csv("data/orders.csv", orders,
              ["order_id", "customer_id", "order_date", "status", "region_code"])
    write_csv("data/order_items.csv", order_items,
              ["item_id", "order_id", "product_id", "quantity", "unit_price", "discount_percent"])

    print("\nDone. Raw files are in ./data/")


if __name__ == "__main__":
    main()
