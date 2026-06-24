"""
Data Warehouse Agent — Core agent that orchestrates LLM + DuckDB.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from anthropic import Anthropic

from agent_tools import execute_sql_query, get_warehouse_schema

# ---------- Anthropic client (DeepSeek-compatible endpoint) ----------
client = Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    base_url=os.environ["ANTHROPIC_BASE_URL"],
)

# ---------- System prompt (bilingual for robustness) ----------
SYSTEM_PROMPT = (
    "你是一个精通维度建模的顶级大数据架构师与数仓开发专家。\n"
    "\n"
    "你必须严格遵守以下规范：\n"
    "1. 汇总层表名前缀必须为 dws_；\n"
    "2. 所有 SQL 关键字（如 SELECT, FROM, JOIN, GROUP BY）必须大写；\n"
    "3. 只能输出纯粹的、可直接执行的 SQL 语句，不要包含任何 Markdown 格式包裹（如 ```sql），"
    "不要包含任何解释性文字。"
)


def run_dw_agent(user_requirement: str) -> None:
    """
    Orchestrate the Data Warehouse Agent:

    1. Retrieve current warehouse schema.
    2. Send schema + requirement to the LLM for SQL generation.
    3. Print and execute the returned SQL against DuckDB.
    """
    # ----- Step 1: Get schema -----
    print("=" * 60)
    print("[Step 1] Fetching warehouse schema ...")
    schema = get_warehouse_schema()

    schema_text_lines = ["Current warehouse tables and columns:"]
    for table, cols in schema.items():
        col_list = ", ".join(f"{c['name']} {c['type']}" for c in cols)
        schema_text_lines.append(f"  - {table}({col_list})")
    schema_text = "\n".join(schema_text_lines)
    print(schema_text)

    # ----- Step 2: Call LLM -----
    print("\n[Step 2] Asking LLM to generate SQL ...")
    user_message = (
        f"{schema_text}\n\n"
        f"User requirement:\n{user_requirement}"
    )

    response = client.messages.create(
        model="deepseek-v4-pro",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )

    # Collect text from all TextBlock items (skip ThinkingBlock)
    sql_parts = [
        block.text for block in response.content if block.type == "text"
    ]
    sql = "".join(sql_parts).strip()

    if not sql:
        print("ERROR: LLM returned no text content. Full response:")
        print(response.content)
        return
    print(f"\n--- LLM generated SQL ---\n{sql}\n{'─' * 40}")

    # ----- Step 3: Execute SQL -----
    print("\n[Step 3] Executing SQL against dev_dw.db ...")
    result = execute_sql_query(sql)
    print(f"  Execution done, {len(result)} rows returned/affected.")

    # ----- Optional: verify the new table -----
    if sql.upper().startswith("CREATE"):
        updated_schema = get_warehouse_schema()
        print(f"\n  Updated schema now has {len(updated_schema)} table(s):")
        for t in updated_schema:
            print(f"    - {t}")


if __name__ == "__main__":
    requirement = (
        "帮我统计每个城市的总销售额，按照销售额从高到低排序，"
        "并在数仓中创建一张名为 dws_city_sales 的汇总表。"
    )
    run_dw_agent(requirement)
