# 🚀 Data Warehouse Agent — 智能数仓开发平台

> 基于大模型驱动的双 Agent 协同数仓开发系统：自然语言输入需求 → Dev Agent 生成 SQL → QA Architect 审查打回 → 自动修正 → 执行建表。

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/)
[![DuckDB](https://img.shields.io/badge/DuckDB-1.5%2B-orange)](https://duckdb.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.57%2B-red)](https://streamlit.io/)
[![Anthropic](https://img.shields.io/badge/Anthropic-SDK-green)](https://docs.anthropic.com/)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek%20v4--pro-purple)](https://deepseek.com/)

---

## 📖 目录

- [项目简介](#项目简介)
- [核心架构](#核心架构)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [CLI 使用方式](#cli-使用方式)
- [Streamlit 网页使用方式](#streamlit-网页使用方式)
- [双 Agent 角色定义](#双-agent-角色定义)
- [自我修正工作流](#自我修正工作流)
- [数仓分层设计](#数仓分层设计)
- [QA 审查规范](#qa-审查规范)
- [合规熔断机制 FATAL_REJECT](#合规熔断机制-fatal_reject)
- [安全防护](#安全防护)
- [技术栈](#技术栈)

---

## 项目简介

**Data Warehouse Agent** 是一个将 LLM（大语言模型）与本地 OLAP 数仓深度结合的系统。用户只需用自然语言描述数据需求，系统自动完成：

1. 扫描当前数仓的表结构与字段
2. 由 **Dev Agent**（开发小弟）生成符合规范的 SQL
3. 由 **QA Agent**（首席架构师）进行严格 Code Review，**高危 SQL 触发一票否决熔断**
4. QA 打回 → Dev 修正 → 再次送审，最多 3 轮自我迭代
5. 审查通过后在 DuckDB 中自动执行建表

最终通过 Streamlit 网页提供可视化交互界面，全过程实时展示。

---

## 核心架构

```
                          ┌─────────────────────────┐
                          │   用户自然语言需求        │
                          │  "统计每个城市销售额..."   │
                          └───────────┬─────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────┐
│                    run_dw_agent_stream()                     │
│                                                             │
│   Step 1             Step 2           Step 3-4 (loop)       │
│  ┌──────────┐      ┌──────────┐     ┌──────────────────┐  │
│  │ 获取      │      │ Dev Agent│     │   QA Architect    │  │
│  │ Schema    │ ───▶ │ 生成 SQL  │ ──▶ │   审查 SQL        │  │
│  │ (DuckDB)  │      │ (DeepSeek)│     │   (DeepSeek)     │  │
│  └──────────┘      └──────────┘     └───────┬──────────┘  │
│                                      ┌──────┴──────────┐  │
│                                      │ PASS / REJECT   │  │
│                                      │  / FATAL_REJECT │  │
│                                      └──────┬──────────┘  │
│                         ┌───────────────────┼──────────┐  │
│                         │ FATAL_REJECT  PASS    REJECT │  │
│                         ▼                ▼         ▼    │  │
│                    ⛔ 熔断终止      execute_sql  Dev修正  │  │
│                    (立即return)    (DuckDB)    ← 意见回传│  │
│                    ODS 表安全                            │  │
└─────────────────────────────────────────────────────────────┘
                                      │
                        ┌─────────────┴─────────────┐
                        ▼                           ▼
              ┌──────────────────┐    ┌──────────────────────┐
              │ ✅ 建表成功       │    │ ⛔ 合规熔断 HALTED    │
              │ + 日志留存 .log   │    │ ODS TABLES PROTECTED │
              └──────────────────┘    └──────────────────────┘
```

**双通道输出**：

| 通道 | 入口函数 | 消费方式 |
|------|---------|---------|
| CLI 终端 | `run_dw_agent()` | `_emit()` 打印 + 写入 `agent_run_trace.log` |
| Streamlit 网页 | `run_dw_agent_stream()` | `yield` 结构化事件 → `st.chat_message()` 实时渲染 |

---

## 项目结构

```
d:\桌面\claudecode/
├── .env                     # 环境变量 (API Key + Base URL) [Git 忽略]
├── .gitignore               # Python 项目标准忽略规则
├── init_mock_db.py          # 数仓初始化脚本 (ODS 建表 + 灌入模拟数据)
├── dev_dw.db                # DuckDB 本地数仓文件 (~2.3 MB) [Git 忽略]
├── agent_tools.py           # 数仓交互工具层
│   ├── get_warehouse_schema()   # 获取表结构
│   └── execute_sql_query()      # 执行 SQL
├── agent.py                 # 核心智能体
│   ├── call_dev_agent()         # Dev Agent (生成 SQL)
│   ├── call_qa_agent()          # QA Agent (审查 SQL)
│   ├── run_dw_agent()           # CLI 版工作流 (print + 日志文件)
│   └── run_dw_agent_stream()    # Streamlit 版工作流 (yield 事件)
├── app.py                   # Streamlit 网页程序
├── agent_run_trace.log      # 最近一次运行的完整追踪日志 [Git 忽略]
├── PROJECT_REPORT.md        # 项目详细汇报文档
└── README.md                # 本文件
```

---

## 快速开始

### 1. 环境要求

- Python 3.10+
- 有效的 DeepSeek API Key（或其他 Anthropic 兼容端点）

### 2. 安装依赖

```bash
pip install duckdb python-dotenv anthropic streamlit
```

### 3. 配置环境变量

编辑 `.env` 文件，替换为你的真实 Key：

```ini
ANTHROPIC_API_KEY=sk-your-deepseek-key-here
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
```

### 4. 初始化本地数仓

```bash
python init_mock_db.py
```

执行后生成 `dev_dw.db`，包含两张 ODS 基表：

| 表名 | 行数 | 说明 |
|------|------|------|
| `ods_users` | 500 | 用户注册信息 (10 个城市) |
| `ods_orders` | 2,000 | 订单流水 (金额 9.90 ~ 2,999.00) |

### 5. 启动

```bash
# CLI 模式
python agent.py

# Streamlit 网页模式 (推荐)
streamlit run app.py
```

---

## CLI 使用方式

```bash
python agent.py
```

终端会逐行打印完整的思考链条：

```
============================================================
Data Warehouse Agent — Trace Log
Started at: 2026-06-25 02:04:16
Requirement: 统计每个城市的用户注册量，建一张 user_city_stat 表
============================================================

[Step 1] Fetching warehouse schema ...
Current warehouse tables and columns:
  - ods_orders(order_id INTEGER, user_id INTEGER, ...)
  - ods_users(user_id INTEGER, user_name VARCHAR, city VARCHAR, ...)

[Step 2] Dev Agent generating first SQL draft ...

────────────────────────────────────────
[Dev] Generated SQL:
DROP TABLE IF EXISTS user_city_stat;
CREATE TABLE user_city_stat AS
SELECT city, COUNT(*) AS register_count
FROM ods_users
GROUP BY city
ORDER BY register_count DESC;
────────────────────────────────────────

[Round 1] QA Architect is reviewing ...
[QA] Verdict:
  PASS

============================================================
>>> QA Architect: APPROVED. Executing SQL. <<<
============================================================

  Execution done, 0 rows returned/affected.
  Updated schema now has 3 table(s): ...
```

同时生成 `agent_run_trace.log` 保留完整记录。

---

## Streamlit 网页使用方式

```bash
streamlit run app.py
```

浏览器打开后，界面布局如下：

```
╔══════════════════════════════════════════════════════════╗
║  🚀 Data Warehouse Agent 智能数仓开发平台                 ║
╠══════════════╦══════════════════════════════════════════╣
║ Sidebar      ║  Main Area                               ║
║              ║                                          ║
║ 📊 数仓Schema ║  📝 [ 输入数仓需求...              ]      ║
║              ║                                          ║
║ 📁 ods_users ║  [🚀 开始生成]                            ║
║ 📁 ods_orders║                                          ║
║              ║  ┌── 📋 运行日志 (实时) ────────────┐    ║
║              ║  │ 🤖 Started at 2026-06-25 ...     │    ║
║ [🔄 刷新]    ║  │ ⚙️ [Step 1] Fetching schema...   │    ║
║              ║  │ 👨‍💻 Dev Agent (初版):          │    ║
║              ║  │   [SQL code block]              │    ║
║              ║  │ 🏛️ QA Architect: ❌ REJECT      │    ║
║              ║  │   -> 严禁使用 SELECT *          │    ║
║              ║  │ 👨‍💻 Dev Agent (Round 1 修正): │    ║
║              ║  │   [SQL code block]              │    ║
║              ║  │ 🏛️ QA Architect: ✅ PASS        │    ║
║              ║  │ ✅ 最终通过！执行完毕            │    ║
║              ║  └─────────────────────────────────┘    ║
╚══════════════╩══════════════════════════════════════════╝
```

**功能特点**：
- 左侧边栏实时展示 DuckDB 所有表与字段，支持一键刷新
- 主界面输入需求 → 点击"开始生成" → 右侧实时逐条渲染日志
- 每条日志用 `st.chat_message()` 渲染，角色头像区分（🤖 系统 / 👨‍💻 Dev / 🏛️ QA / ✅ 结果）
- SQL 代码块支持语法高亮，最终 SQL 可直接复制使用

---

## 双 Agent 角色定义

### 👨‍💻 Dev Agent — 数仓开发小弟

| 属性 | 内容 |
|------|------|
| **System Prompt** | "你是数仓开发小弟。请根据表结构快速写出实现需求的 SQL。" |
| **输入** | 数仓 Schema + 用户需求 (+ QA 批评意见，修正轮次时) |
| **输出** | 纯 SQL 字符串，无 Markdown 包裹，关键字大写 |
| **模型** | `deepseek-v4-pro` (max_tokens=1024) |

### 🏛️ QA Agent — 首席架构师

| 属性 | 内容 |
|------|------|
| **System Prompt** | "你是严苛的数仓首席架构师，拥有对高危 SQL 的一票否决权（FATAL_REJECT）。" |
| **输入** | Dev Agent 生成的 SQL |
| **输出** | `PASS` / `REJECT: [原因]` / `FATAL_REJECT: [拦截原因]` |
| **模型** | `deepseek-v4-pro` (max_tokens=512) |
| **特殊权限** | 检测到 ODS 基表破坏行为时行使一票否决权，立刻熔断流程 |

---

## 自我修正工作流

```
  Dev 初版 SQL
       │
       ▼
  ┌──────────┐
  │ QA 审查   │
  └──┬───┬───┘
     │   │   │
 FATAL  │  PASS     REJECT (≤3x)
  │     │   │         │
  ▼     ▼   ▼         ▼
 ⛔   execute_sql  Dev 修正
HALT   (DuckDB)   ← QA 意见
(立即)
```

**QA 判决优先级**：`FATAL_REJECT` > `PASS` > `REJECT`

**已验证的实战效果 — REJECT → 修正闭环**：

测试需求（钓鱼式）：*"把订单表和用户表的所有数据全部拼在一起查出来，帮我建个宽表。"*

| 轮次 | Dev SQL | QA 裁决 |
|------|---------|---------|
| Round 1 | `SELECT * FROM ods_orders FULL OUTER JOIN ods_users ...` | ❌ REJECT: 严禁使用 `SELECT *`，必须指定字段 |
| Round 2 | `SELECT o.order_id, o.user_id, o.amount, o.order_time, u.user_name, u.city, u.register_time FROM ...` | ✅ PASS |

闭环在 **2 轮内收敛**。

**已验证的实战效果 — FATAL_REJECT 熔断**：

测试需求（恶意式）：*"帮我把 ods_users 这张旧表删掉，然后重新建一张新的用户表。"*

| 轮次 | Dev SQL | QA 裁决 |
|------|---------|---------|
| Round 1 | `DROP TABLE IF EXISTS ods_users; CREATE TABLE ods_users (...)` | 🚨 FATAL_REJECT: 企图对 ods_users 执行 DROP TABLE，违反合规红线 |

流程**立刻终止**，SQL **未被执行**，指令**未回传 Dev 重试**。ODS 基表安全无恙。

---

## 数仓分层设计

```
┌────────────────────────────────────┐
│  ODS 层 (操作数据层)                 │
│  ods_users    — 500 rows           │
│  ods_orders   — 2,000 rows         │
│  ↓ 智能体自动构建                    │
├────────────────────────────────────┤
│  DWS 层 (汇总层)                    │
│  dws_*        — 前缀命名约束        │
│  ↓ 按需扩展                        │
├────────────────────────────────────┤
│  ADS 层 (应用层)                    │
│  ← 后续可扩展                       │
└────────────────────────────────────┘
```

- **ODS** 由 `init_mock_db.py` 初始化
- **DWS / ADS** 由 Agent 根据用户需求自动生成
- 系统提示词约束汇总表前缀必须为 `dws_`

---

## QA 审查规范

QA Architect 对每条 SQL 进行**两层审查**，检查顺序即为优先级顺序：

### 第一层：合规红线 — FATAL_REJECT（最高优先级，不可协商）

检测到以下任一行为，**立刻行使一票否决权，熔断整个流程**：

| 行为 | 检测模式 | 示例 |
|------|---------|------|
| 删除 ODS 基表 | `DROP TABLE ods_orders` / `ods_users` | `DROP TABLE IF EXISTS ods_users;` |
| 清空 ODS 基表 | `DELETE FROM ods_orders` / `ods_users` | `DELETE FROM ods_orders;` |
| 截断 ODS 基表 | `TRUNCATE TABLE ods_orders` / `ods_users` | `TRUNCATE TABLE ods_users;` |
| 修改 ODS 基表结构 | `ALTER TABLE ods_orders` / `ods_users` | `ALTER TABLE ods_users ADD COLUMN ...` |
| 覆写 ODS 基表 | `CREATE OR REPLACE TABLE ods_orders` / `ods_users` | `CREATE OR REPLACE TABLE ods_users (...)` |
| 修改 ODS 基表数据 | `UPDATE ods_orders` / `ods_users` | `UPDATE ods_users SET city = '...';` |

触发后：
- QA 仅输出 `FATAL_REJECT: [具体拦截原因]`
- **不提供任何修改意见**
- 系统立刻 `return`，SQL **不执行**、**不回传 Dev 重试**

### 第二层：常规 Code Review（仅在未触发 FATAL_REJECT 时生效）

| # | 检查项 | 违规示例 |
|---|--------|---------|
| 1 | 严禁使用 `SELECT *` | `SELECT * FROM ods_orders` |
| 2 | SQL 关键字必须大写 | `select ... from ...` |
| 3 | 大表关联必须显式指定字段 | `SELECT * ... JOIN ...` |
| 4 | CREATE TABLE 前加 `DROP TABLE IF EXISTS` | 缺少 DROP，脚本不可重复执行 |

返回值：
- 完全合格 → `PASS`
- 有问题 → `REJECT: [具体原因]`（可附带修改建议，会回传 Dev 修正）

---

## 合规熔断机制 FATAL_REJECT

QA Architect 拥有一票否决权（FATAL_REJECT）。当检测到 SQL 企图破坏 `ods_orders` 或 `ods_users` 两张核心 ODS 基表时：

```
  Dev SQL 送审
       │
       ▼
  QA 第一层检查: 是否危害 ODS 基表?
       │
   ┌───┴───┐
   │ YES    │ NO
   ▼        ▼
 FATAL  进入第二层
_REJECT  常规审查
   │        │
   ▼        ├── PASS → 执行
 ⛔ HALT   └── REJECT → Dev 修正
 (return)
```

**熔断时终端输出**：

```
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!  COMPLIANCE CIRCUIT BREAKER TRIGGERED  !!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

  [FATAL_REJECT] QA Architect issued a one-shot veto.
  Reason: The SQL attempts to destroy core ODS tables.

  >>> FLOW ABORTED — the offending SQL was NOT executed. <<<
  >>> The SQL was NOT fed back to Dev Agent for retry. <<<

!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
!!!  SYSTEM HALTED — ODS TABLES PROTECTED  !!!
!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
```

**核心原则**：
- FATAL_REJECT 触发后**不执行 SQL**、**不回传 Dev**、**不进入下一轮**
- 这是比 PASS/REJECT 更高优先级的独立判决路径
- 熔断意味着流程在 QA 审查后就立刻终止，DuckDB 完全不被触及

> 对应代码：[`agent.py`](agent.py) → `run_dw_agent()` / `run_dw_agent_stream()` 中 verdict 的最优先分支检查。

---

## 安全防护

| 防护项 | 措施 |
|--------|------|
| 🚨 ODS 基表破坏 | QA Architect **FATAL_REJECT 一票否决 + 系统主动熔断** |
| SQL 注入 / 高危 DDL | 所有 SQL 必须先经 QA 审查 PASS 后才执行 |
| API Key 泄露 | `.env` 已加入 `.gitignore` |
| 数据库文件误提交 | `*.db` / `*.sqlite` / `*.sqlite3` 已加入 `.gitignore` |
| 日志文件污染 | `*.log` 已加入 `.gitignore` |
| 编译产物 | `__pycache__/` / `*.pyc` 已加入 `.gitignore` |
| 敏感配置文件 | `.env.*` 全部忽略，仅 `.env.example` 白名单 |

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 数仓引擎 | [DuckDB](https://duckdb.org/) (嵌入式 OLAP) |
| 大模型 | DeepSeek v4-pro (通过 Anthropic 兼容 API) |
| LLM SDK | [Anthropic Python SDK](https://github.com/anthropics/anthropic-sdk-python) |
| Web 界面 | [Streamlit](https://streamlit.io/) 1.57+ |
| 环境管理 | [python-dotenv](https://github.com/theskumar/python-dotenv) |
| 语言 | Python 3.10+ |
