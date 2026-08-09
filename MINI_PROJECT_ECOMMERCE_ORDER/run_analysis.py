"""
run_analysis.py
----------------
Executes every query in analysis.sql against database.db, prints a preview
of each result set, and saves full results to ./sql_outputs/*.csv
This is a convenience/verification script (not required by the assignment)
to prove every query in analysis.sql actually runs correctly.
"""
import sqlite3
import pandas as pd
import re
import os

os.makedirs("sql_outputs", exist_ok=True)

with open("analysis.sql", "r") as f:
    content = f.read()

# split on the numbered comment headers "-- N. Title"
blocks = re.split(r"\n-- (\d+)\. (.+?)\n-- -+\n", content)
# blocks[0] is preamble; then triples of (num, title, sql)
conn = sqlite3.connect("database.db")

results = []
for i in range(1, len(blocks), 3):
    num, title, sql = blocks[i], blocks[i+1], blocks[i+2]
    sql_clean = sql.strip()
    try:
        df = pd.read_sql_query(sql_clean, conn)
        fname = f"sql_outputs/q{int(num):02d}_{title.lower().replace(' ', '_').replace('/', '_')[:40]}.csv"
        df.to_csv(fname, index=False)
        print(f"Q{num}. {title:55s} -> {len(df):>5} rows  OK   ({fname})")
        results.append((num, title, len(df), "OK"))
    except Exception as e:
        print(f"Q{num}. {title:55s} -> ERROR: {e}")
        results.append((num, title, 0, f"ERROR: {e}"))

conn.close()

n_ok = sum(1 for r in results if r[3] == "OK")
print(f"\n{n_ok}/{len(results)} queries executed successfully.")
