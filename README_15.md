# 🛒 E-Commerce Order Analytics System

**Intern Mini Project — Celebal Excellence Intern (CEI) Program**
**Celebal Technologies Private Limited**

**Author:** Sumit Kumar Singh
**Duration:** 3–4 weeks
**Skills Tested:** Python, SQL, Problem Solving
**Phase:** Build everything using Python and SQL (local environment)

---

## 📌 Project Overview

This project simulates a real-world scenario: a company processes online
orders, but the raw data arriving from multiple sources is messy. The goal
is to **generate**, **clean**, **model**, and **analyze** that data end to
end using nothing but Python and SQL (SQLite).

The project covers:

- Synthetic data generation with intentionally injected data-quality issues
- Data cleaning & validation with Python/pandas
- Relational database design in SQLite
- 16 SQL analysis queries — basic, intermediate, and advanced (window
  functions, CTEs, self-joins)
- A command-line report-generation tool (stdlib `sqlite3` only)
- An automated edge-case test suite

---

## 📂 Project Structure

```
ecom_project/
│
├── data/                       # raw, messy CSVs (as generated)
│   ├── customers.csv
│   ├── products.csv
│   ├── orders.csv
│   └── order_items.csv
│
├── cleaned_data/                # cleaned CSVs (output of clean_data.py)
│   ├── customers.csv
│   ├── products.csv
│   ├── orders.csv
│   └── order_items.csv
│
├── reports/
│   └── issues_report.txt        # full log of every issue found & fixed
│
├── sql_outputs/                 # CSV result of every query in analysis.sql
│   └── q01 ... q16 ...csv
│
├── database.db                  # SQLite database (schema + cleaned data loaded)
│
├── generate_data.py             # Part 1: Data Generation
├── clean_data.py                # Part 2: Data Cleaning
├── create_database.py           # loads cleaned_data/*.csv into database.db
├── analysis.sql                 # Part 3: 16 SQL analysis queries
├── run_analysis.py              # runs every query in analysis.sql, saves results
├── cli.py                       # Part 4: Python + SQL CLI report tool
├── edge_case_tests.py           # Part 5: Edge case test suite
├── test_database.py             # sanity-checks the built database
│
└── README.md
```

---

## 🗄 Database Schema

**customers**
| Column | Type |
|---|---|
| customer_id (PK) | INTEGER |
| customer_name | TEXT |
| email | TEXT |
| registration_date | TEXT |
| customer_type | TEXT — REGULAR / PREMIUM / VIP |

**products**
| Column | Type |
|---|---|
| product_id (PK) | INTEGER |
| product_name | TEXT |
| category | TEXT |
| subcategory | TEXT |
| cost_price | REAL |

**orders**
| Column | Type |
|---|---|
| order_id (PK) | INTEGER |
| customer_id (FK → customers) | INTEGER, nullable |
| order_date | TEXT (YYYY-MM-DD HH:MM:SS) |
| status | TEXT — PLACED / SHIPPED / DELIVERED / CANCELLED / RETURNED |
| region_code | TEXT |

**order_items**
| Column | Type |
|---|---|
| item_id (PK) | INTEGER |
| order_id (FK → orders) | INTEGER |
| product_id (FK → products) | INTEGER |
| quantity | INTEGER (can be negative = return) |
| unit_price | REAL |
| discount_percent | REAL (0–100) |

`revenue = quantity * unit_price * (1 - discount_percent / 100)` is the
formula used everywhere in `analysis.sql` and `cli.py`.

---

## 🧪 Intentional Data Issues (Part 1)

`generate_data.py` deliberately injects the following, so that the cleaning
step has real problems to solve:

| Issue | Where |
|---|---|
| ~5% missing `customer_id` | orders.csv |
| ~3% negative `quantity` (returns) | order_items.csv |
| ~8% of dates in `DD-MM-YYYY` instead of `YYYY-MM-DD HH:MM:SS` | orders.csv |
| Extra spaces / mixed case in product names | products.csv |
| ~2% invalid emails (missing `@` or domain) | customers.csv |
| A handful of `order_items` rows pointing at an `order_id` that doesn't exist | order_items.csv |
| A few future-dated orders, zero-quantity rows, and >100% discounts | orders.csv / order_items.csv |

**Referential integrity for order_items → orders** is guaranteed at
generation time by always sampling `order_id` from the pool of IDs that
actually exist in `orders.csv` — except for 5 rows added on purpose at the
end, to give `check_referential_integrity()` something real to catch.

---

## 🧹 Data Cleaning (Part 2)

`clean_data.py` implements exactly the four required functions:

- **`clean_orders()`** — normalizes every date format to
  `YYYY-MM-DD HH:MM:SS`, flags future-dated orders, converts empty/blank
  `customer_id` to a proper nullable integer `NULL`.
- **`clean_products()`** — trims whitespace and title-cases product,
  category, and subcategory names.
- **`validate_emails()`** — regex-validates every customer email and
  returns the list of `customer_id`s with an invalid address.
- **`check_referential_integrity()`** — finds every `order_items` row whose
  `order_id` doesn't exist in `orders`; these orphan rows are then dropped
  before loading into the database.

Every issue found is logged to **`reports/issues_report.txt`**.

### Actual results from a real run:

```
[orders] 246 rows had a non-standard date format -> normalized
[orders] 14 orders have an order_date in the future (flagged, not removed)
[orders] 140 / 3000 orders (4.7%) have a missing customer_id -> kept as NULL
[products] 45 product names had extra spaces / inconsistent casing -> fixed
[customers] 5 / 600 customers (0.8%) have an invalid email address
[order_items] 230 rows have negative quantity -> treated as returns
[order_items] 40 rows have quantity = 0 (flagged)
[order_items] 18 rows have discount_percent outside 0-100 -> clipped
[integrity] 5 order_items rows reference a non-existent order_id -> removed
```

---

## 📈 SQL Analysis (Part 3)

`analysis.sql` contains all 16 required queries, grouped as:

**Basic** — revenue per category, top 10 customers, month-wise order count
**Intermediate** — never-delivered customers, over-returned products,
category return rate
**Advanced** — running totals (window functions), `DENSE_RANK` product
ranking, `LAG` gap analysis with "At Risk" flag, multi-level CTEs, `NTILE`
quartile segmentation, YoY comparison, `FIRST_VALUE`/`LAST_VALUE` category
shift, cumulative revenue distribution, cohort retention analysis, and a
self-join "frequently bought together" query.

Run every query and save results to `sql_outputs/`:

```bash
python3 run_analysis.py
```

Sample real output (category revenue, Query 1):

| category | total_revenue |
|---|---|
| Electronics | 128,419,510.61 |
| Books | 120,060,407.53 |
| Home | 119,866,320.10 |
| Clothing | 98,014,838.26 |

Sample real output (return rate per category, Query 6):

| category | returned_items | total_items | return_rate_percent |
|---|---|---|---|
| Home | 197 | 5705 | 3.45% |
| Electronics | 178 | 6066 | 2.93% |
| Clothing | 138 | 4740 | 2.91% |
| Books | 159 | 5743 | 2.77% |

---

## 🖥 CLI Report Tool (Part 4)

`cli.py` uses **only** the Python standard library (`sqlite3`, `argparse`,
`datetime`) — no pandas.

Interactive mode:
```bash
python3 cli.py
```

Non-interactive mode (for scripting):
```bash
python3 cli.py --type monthly --start 2026-06-01 --end 2026-07-31
```

### Real sample output

```
=======================================================
ECOMMERCE ORDER ANALYTICS
=======================================================

Report Type : Monthly

Start Date  : 2026-06-01
End Date    : 2026-07-31

-------------------------------------------------------

Total Orders      : 417
Total Revenue     : Rs. 65,796,831.48
Unique Customers  : 300

Top 3 Products
1. Table Lamp Plus
2. Wall Clock Plus
3. Puffer Jacket V2

Comparison with Previous Period
Previous period    : 2026-04-01 to 2026-05-31
Orders Change      : -12.58%
Revenue Change     : -13.29%
Customers Change   : -1.96%
=======================================================
```

---

## 🧪 Edge Case Testing (Part 5)

`edge_case_tests.py` verifies system behavior for all 4 required cases,
plus a bonus check that the database itself enforces referential integrity
via `FOREIGN KEY` constraints:

```bash
python3 edge_case_tests.py
```

| # | Edge case | Behavior verified |
|---|---|---|
| 1 | `order_items.order_id` not in `orders` | Detected by `check_referential_integrity()`, orphan rows dropped before DB load; DB-level FK also rejects any that slip through |
| 2 | `discount_percent > 100` | Detected and clipped to `[0, 100]` so revenue never goes negative |
| 3 | `quantity = 0` | Flagged as a no-op line item, kept (not silently dropped), contributes exactly ₹0 revenue |
| 4 | `order_date` in the future | Flagged in the issues report, kept as-is (could be a legit pre-order), naturally excluded from historical date-range reports |

All 5 tests pass on the generated dataset.

---

## ⚙️ How to Run (full pipeline, in order)

```bash
# 1. Generate raw messy data (4 CSVs, 500+ rows each)
python3 generate_data.py

# 2. Clean the data + produce issues report
python3 clean_data.py

# 3. Build the SQLite database from cleaned data
python3 create_database.py

# 4. Verify the database loaded correctly
python3 test_database.py

# 5. Run all 16 SQL analysis queries
python3 run_analysis.py

# 6. Generate a report with the CLI tool
python3 cli.py --type monthly --start 2026-01-01 --end 2026-06-30

# 7. Run the edge case test suite
python3 edge_case_tests.py
```

---

## 🛠 Technologies Used

- Python 3.12
- pandas
- SQLite3 (via Python's built-in `sqlite3` module)
- Faker (for realistic synthetic data)
- Standard SQL — JOINs, GROUP BY, HAVING, CASE WHEN, CTEs, window functions
  (`ROW_NUMBER`, `DENSE_RANK`, `NTILE`, `LAG`, `FIRST_VALUE`, `LAST_VALUE`)

---

## 📊 Key Learnings

- Designing a normalized relational schema with primary/foreign keys
- Writing realistic, intentionally-flawed synthetic data generators
- Data validation and cleaning strategies with pandas
- Advanced SQL: CTEs, window functions, self-joins, cohort analysis
- Building a CLI tool with only the standard library
- Systematic edge-case thinking and automated verification

---

## 🔮 Possible Future Enhancements

- Interactive dashboard (Flask / Streamlit)
- Automated chart generation for each SQL report
- Export reports to PDF/Excel
- Move from SQLite to PostgreSQL for a multi-user setup
- Scheduled/automated report generation

---

**Sumit Kumar Singh**<br>
Celebal Excellence Intern (CEI) — Data Engineering Track
Celebal Technologies Private Limited
