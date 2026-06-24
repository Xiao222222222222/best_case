"""
Data Warehouse Agent — Initialize local DuckDB warehouse.
Creates dev_dw.db with ODS-layer mock data.
"""

import random
import duckdb
from datetime import datetime, timedelta

DB_PATH = "dev_dw.db"

# ---------- City pool ----------
CITIES = ["Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Hangzhou",
          "Chengdu", "Wuhan", "Nanjing", "Xian", "Chongqing"]

# ---------- Name parts ----------
SURNAMES = ["Zhang", "Li", "Wang", "Liu", "Chen", "Yang",
            "Zhao", "Huang", "Zhou", "Wu", "Xu", "Sun", "Ma", "Zhu", "Hu"]
GIVENS  = ["Wei", "Fang", "Na", "Min", "Jing", "Qiang", "Lei",
           "Yang2", "Yong", "Yan", "Tao", "Jun", "Jie", "Xiuying", "Hua"]

# ---------- Time range ----------
NOW = datetime.now()
START_REG = NOW - timedelta(days=730)   # registrations from 2 years ago
START_ORD = NOW - timedelta(days=180)   # orders from 6 months ago


def gen_users(n: int = 500) -> list[tuple]:
    """Generate N user records."""
    rows = []
    for uid in range(1, n + 1):
        name = random.choice(SURNAMES) + " " + random.choice(GIVENS)
        city = random.choice(CITIES)
        reg_time = START_REG + timedelta(
            days=random.randint(0, 730),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        rows.append((uid, name, city, reg_time))
    return rows


def gen_orders(n: int = 2000, user_count: int = 500) -> list[tuple]:
    """Generate N order records, randomly linked to existing users."""
    rows = []
    for oid in range(1, n + 1):
        uid = random.randint(1, user_count)
        amount = round(random.uniform(9.9, 2999.0), 2)
        ord_time = START_ORD + timedelta(
            days=random.randint(0, 180),
            hours=random.randint(0, 23),
            minutes=random.randint(0, 59),
        )
        rows.append((oid, uid, amount, ord_time))
    return rows


def main():
    print("[1/3] Connecting to DuckDB ...")
    con = duckdb.connect(DB_PATH)

    print("[2/3] Creating ODS tables ...")
    con.execute("""
        CREATE OR REPLACE TABLE ods_users (
            user_id        INTEGER PRIMARY KEY,
            user_name      VARCHAR,
            city           VARCHAR,
            register_time  TIMESTAMP
        )
    """)
    con.execute("""
        CREATE OR REPLACE TABLE ods_orders (
            order_id    INTEGER PRIMARY KEY,
            user_id     INTEGER,
            amount      DOUBLE,
            order_time  TIMESTAMP
        )
    """)

    print("[3/3] Inserting mock data ...")
    users = gen_users(500)
    orders = gen_orders(2000, user_count=500)

    con.executemany("INSERT INTO ods_users VALUES (?, ?, ?, ?)", users)
    con.executemany("INSERT INTO ods_orders VALUES (?, ?, ?, ?)", orders)

    # Verify
    user_cnt = con.execute("SELECT COUNT(*) FROM ods_users").fetchone()[0]
    order_cnt = con.execute("SELECT COUNT(*) FROM ods_orders").fetchone()[0]
    sample = con.execute("SELECT * FROM ods_orders LIMIT 5").fetchall()

    print(f"\n[Done] DB initialized: {DB_PATH}")
    print(f"   ods_users  : {user_cnt} rows")
    print(f"   ods_orders : {order_cnt} rows")
    print(f"   Sample orders:")
    for row in sample:
        print(f"     {row}")

    con.close()


if __name__ == "__main__":
    main()
