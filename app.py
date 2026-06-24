"""
Streamlit Web App — Data Warehouse Agent Visual Platform
Dual-agent (Dev + QA) collaborative SQL generation with live trace.
"""

import streamlit as st
from agent_tools import get_warehouse_schema
from agent import run_dw_agent_stream

# ---------- Page config ----------
st.set_page_config(
    page_title="DW Agent 智能数仓开发平台",
    page_icon="🚀",
    layout="wide",
)

# ---------- Header ----------
st.title("🚀 Data Warehouse Agent 智能数仓开发平台")
st.caption("Dual-Agent Architecture — Dev Agent + QA Architect — Self-Correction Loop")
st.divider()

# ============================================================
# Sidebar — Live warehouse schema
# ============================================================
with st.sidebar:
    st.markdown("## 📊 当前数仓 Schema")

    try:
        schema = get_warehouse_schema()
        if schema:
            for table, cols in schema.items():
                with st.expander(f"📁 {table}  ({len(cols)} cols)", expanded=False):
                    rows = [[c["name"], c["type"]] for c in cols]
                    st.dataframe(
                        rows,
                        column_config={0: "Column", 1: "Type"},
                        hide_index=True,
                        width="stretch",
                    )
        else:
            st.warning("数仓中暂无表，请先运行 init_mock_db.py。")
    except Exception as e:
        st.error(f"连接数仓失败: {e}")

    st.divider()
    if st.button("🔄 刷新 Schema", width="stretch"):
        st.rerun()

# ============================================================
# Main area — Requirement input + Run
# ============================================================
DEFAULT_REQUIREMENT = (
    "把订单表和用户表的所有数据全部拼在一起查出来，帮我建个宽表。"
)

col_input, col_btn = st.columns([5, 1])
with col_input:
    requirement = st.text_area(
        "📝 输入数仓开发需求",
        value=DEFAULT_REQUIREMENT,
        height=80,
        placeholder="例如：统计每个城市的总销售额，按从高到低排序，建一张汇总表...",
        label_visibility="collapsed",
    )
with col_btn:
    st.write("")  # spacer
    run_btn = st.button("🚀 开始生成", width="stretch", type="primary")

# ============================================================
# Output area — Live trace log
# ============================================================
st.divider()
st.markdown("### 📋 运行日志")

log_container = st.container()

if run_btn:
    if not requirement.strip():
        st.warning("请输入需求描述。")
    else:
        # Clear previous logs via session state
        with log_container:
            progress_bar = st.progress(0, text="初始化中...")

            events = []
            final_sql = ""
            status_placeholder = st.empty()

            # Iterate the generator — each yield is a UI update
            for event in run_dw_agent_stream(requirement.strip()):
                events.append(event)
                etype = event.get("type", "")

                # ---- Render based on event type ----
                if etype == "header":
                    with st.chat_message("assistant", avatar="🤖"):
                        st.caption(f"⏰ {event['message']}")
                        st.caption(f"📝 需求: {event['requirement']}")

                elif etype == "info":
                    with st.chat_message("system", avatar="⚙️"):
                        st.info(event["message"])

                elif etype == "schema":
                    with st.chat_message("system", avatar="📊"):
                        st.code(event["message"], language=None)

                elif etype == "sql":
                    round_label = f" (初版)" if event.get("round") == 0 else f" (Round {event['round']} 修正)"
                    with st.chat_message("assistant", avatar="👨‍💻"):
                        st.caption(f"**Dev Agent{round_label}**")
                        st.code(event["sql"], language="sql")

                elif etype == "verdict":
                    rnd = event["round"]
                    if event["is_pass"]:
                        with st.chat_message("assistant", avatar="🏛️"):
                            st.success(f"**QA Architect (Round {rnd}):** ✅ PASS")
                            st.caption(event["message"])
                        progress_bar.progress(100, text=f"Round {rnd} — PASS ✅")
                    else:
                        with st.chat_message("assistant", avatar="🏛️"):
                            st.error(f"**QA Architect (Round {rnd}):** ❌ REJECT")
                            st.caption(event["message"])
                        progress_bar.progress(
                            min(25 + rnd * 20, 90),
                            text=f"Round {rnd} — REJECTED, 重新生成中...",
                        )

                elif etype == "done":
                    final_sql = event["sql"]
                    with st.chat_message("assistant", avatar="✅"):
                        st.success(
                            f"**最终通过！** 执行完毕 — "
                            f"{event['result_rows']} rows affected "
                            f"({event['rounds']} round(s))"
                        )
                        st.code(event["sql"], language="sql")

                    # Show updated schema
                    with st.expander("📊 更新后的数仓 Schema", expanded=True):
                        updated = event.get("updated_schema", {})
                        for t, cols in updated.items():
                            col_list = ", ".join(
                                f"{c['name']} ({c['type']})" for c in cols
                            )
                            st.caption(f"**{t}** — {col_list}")

                elif etype == "error":
                    with st.chat_message("assistant", avatar="❌"):
                        st.error(event["message"])
                        if "sql" in event:
                            st.code(event["sql"], language="sql")

            # Show summary section
            if final_sql:
                st.divider()
                st.markdown("### 🎯 最终可执行 SQL")
                st.code(final_sql, language="sql")
                st.caption("此 SQL 已通过 QA 架构师审查，可直接复制到数仓中执行。")
