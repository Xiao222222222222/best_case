"""
Data Warehouse Agent — Tool functions for interacting with dev_dw.db (DuckDB).
"""

from typing import Any

import duckdb

DB_PATH = "dev_dw.db"


def get_warehouse_schema(db_path: str | None = None) -> dict[str, list[dict[str, str]]]:
    """
    Return the current schema of the warehouse.

    Parameters
    ----------
    db_path : str or None
        Path to the DuckDB file (defaults to dev_dw.db).

    Returns
    -------
    dict
        Key = table name, Value = list of column dicts:
            [{"name": "order_id", "type": "INTEGER"}, ...]
    """
    path = db_path or DB_PATH
    con = duckdb.connect(path, read_only=True)

    # list all tables in the current database
    tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]

    schema: dict[str, list[dict[str, str]]] = {}
    for tbl in tables:
        cols: list[dict[str, str]] = []
        for col_name, col_type, *_ in con.execute(f"DESCRIBE {tbl}").fetchall():
            cols.append({"name": col_name, "type": col_type})
        schema[tbl] = cols

    con.close()
    return schema


def execute_sql_query(sql: str, db_path: str | None = None) -> list[tuple[Any, ...]]:
    """
    Execute a SQL statement against the DuckDB warehouse.

    - DDL (CREATE / ALTER / DROP, etc.): executed directly, returns [].
    - DML (INSERT / UPDATE / DELETE): executed directly, returns [].
    - Query (SELECT / DESCRIBE / SHOW, etc.): returns all result rows.

    Parameters
    ----------
    sql : str
        The SQL statement to execute.
    db_path : str or None
        Path to the DuckDB file (defaults to dev_dw.db).

    Returns
    -------
    list[tuple]
        Rows returned by the query (empty list for DDL/DML).
    """
    path = db_path or DB_PATH
    con = duckdb.connect(path)

    sql_stripped = sql.strip()
    upper_keyword = sql_stripped.split(maxsplit=1)[0].upper() if sql_stripped else ""

    # Determine statement category
    DDL_KEYWORDS = {"CREATE", "ALTER", "DROP", "TRUNCATE"}
    DML_KEYWORDS = {"INSERT", "UPDATE", "DELETE"}

    if upper_keyword in DDL_KEYWORDS or upper_keyword in DML_KEYWORDS:
        con.execute(sql_stripped)
        con.close()
        return []

    # Anything else is treated as a query
    result = con.execute(sql_stripped).fetchall()
    con.close()
    return result


if __name__ == "__main__":
    # ---------- Quick self-test ----------
    schema = get_warehouse_schema()
    print("=== Warehouse Schema ===")
    for table, cols in schema.items():
        print(f"\n[{table}]")
        for c in cols:
            print(f"  {c['name']:20s} {c['type']}")

    print("\n=== Test Query: SELECT COUNT(*) FROM ods_users ===")
    rows = execute_sql_query("SELECT COUNT(*) FROM ods_users")
    print(f"  ods_users count = {rows[0][0]}")

    print("\n=== Test Query: Top 3 orders by amount ===")
    rows = execute_sql_query(
        "SELECT order_id, user_id, amount FROM ods_orders ORDER BY amount DESC LIMIT 3"
    )
    for r in rows:
        print(f"  {r}")
