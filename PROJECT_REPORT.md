# 数仓开发智能体（Data Warehouse Agent）项目汇报

> 生成日期：2026-06-25  
> Git 仓库：`d:\桌面\claudecode`  
> 分支：`main`

---

## 一、项目概述

本项目构建了一个**基于大模型驱动的数仓开发智能体**，能够根据用户的自然语言需求，自动完成"理解数仓结构 → 生成 SQL → 自我审查修正 → 执行建表"的完整闭环。

**核心技术栈**：

| 层级 | 技术选型 |
|---|---|
| 本地数仓引擎 | DuckDB（嵌入式 OLAP，单文件 `dev_dw.db`） |
| 大模型接入 | Anthropic SDK → DeepSeek v4-pro 兼容端点 |
| 环境管理 | python-dotenv 加载 `.env` 敏感配置 |
| 编程语言 | Python 3.x |

---

## 二、项目文件结构

```
d:\桌面\claudecode/
├── .env                 # 环境变量（API Key + Base URL），Git 已忽略
├── .gitignore           # Python 项目标准忽略规则
├── init_mock_db.py      # 数仓初始化脚本（建 ODS 表 + 灌入模拟数据）
├── dev_dw.db            # DuckDB 本地数仓文件（~2.3 MB），Git 已忽略
├── agent_tools.py       # 数仓交互工具层（Schema 查询 + SQL 执行）
├── agent.py             # 核心智能体（双 Agent 协同 + 自我迭代）
└── PROJECT_REPORT.md    # 本汇报文档
```

---

## 三、各模块详细说明

### 3.1 .gitignore — 安全防线

覆盖 8 大类忽略规则：

- 编译产物（`__pycache__/`、`*.pyc`）
- 分发包（`dist/`、`build/`、`*.whl`）
- 虚拟环境（`venv/`、`.venv/`）
- **数据库文件**（`*.db`、`*.sqlite`、`*.sqlite3`）
- **敏感配置**（`.env`、`.env.*`，保留 `.env.example` 白名单）
- IDE 残留（`.idea/`、`.vscode/`、`.DS_Store`）
- 测试覆盖率（`.pytest_cache/`、`htmlcov/`、`.tox/`）
- 日志 / Notebook 等

### 3.2 .env — 环境变量

```ini
ANTHROPIC_API_KEY=sk-***
ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
```

通过 `python-dotenv` 加载，客户端代码中无需硬编码任何凭证。

### 3.3 init_mock_db.py — 数仓初始化

**功能**：一键创建 DuckDB 数仓，生成 ODS 层模拟数据。

**ODS 层两张基表**：

| 表名 | 字段 | 数据量 | 说明 |
|---|---|---|---|
| `ods_users` | `user_id`, `user_name`, `city`, `register_time` | 500 行 | 用户注册信息，覆盖 10 个城市 |
| `ods_orders` | `order_id`, `user_id`, `amount`, `order_time` | 2000 行 | 订单流水，金额 9.90 ~ 2999.00 |

**数据特征**：

- 用户注册时间：过去 2 年随机分布
- 订单时间：过去 6 个月随机分布
- 订单 `user_id` 随机关联到用户表
- 城市池：Beijing, Shanghai, Guangzhou, Shenzhen, Hangzhou, Chengdu, Wuhan, Nanjing, Xian, Chongqing

### 3.4 agent_tools.py — 数仓交互工具层

提供两个独立函数，解耦数据库操作与大模型调用：

#### `get_warehouse_schema(db_path?) → dict`

- 以**只读模式**连接 DuckDB
- 执行 `SHOW TABLES` 枚举所有表
- 对每张表执行 `DESCRIBE` 获取字段名与类型
- 返回结构化字典：

```python
{
  "ods_users":  [{"name": "user_id", "type": "INTEGER"}, ...],
  "ods_orders": [{"name": "order_id", "type": "INTEGER"}, ...],
}
```

#### `execute_sql_query(sql, db_path?) → list[tuple]`

- 自动识别 SQL 类型：
  - **DDL**（`CREATE / ALTER / DROP / TRUNCATE`）→ 直接执行，返回 `[]`
  - **DML**（`INSERT / UPDATE / DELETE`）→ 直接执行，返回 `[]`
  - **查询**（`SELECT / DESCRIBE / SHOW` 等）→ 执行并返回全部行

### 3.5 agent.py — 核心智能体（双 Agent 协同 + 自我迭代）

#### 架构设计

```
用户需求（自然语言）
        │
        ▼
┌─────────────────┐
│  Step 1: 获取   │  get_warehouse_schema()
│  数仓 Schema    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Step 2: Dev    │  开发小弟 — 根据需求 + Schema 写 SQL
│  Agent 初版 SQL │  System: "关键字大写，只输出纯 SQL"
└────────┬────────┘
         │
         ▼
   ┌─────────────────────────────┐
   │  Step 3-4: QA ↔ Dev 循环   │  最多 3 轮
   │                             │
   │  ┌──────────┐   REJECT     │
   │  │ QA Agent │──────────────▶│  架构师审查 SQL
   │  │ (架构师)  │  反馈给 Dev   │  检查: ① 禁 SELECT *
   │  └────┬─────┘               │       ② 关键字大写
   │       │ PASS                │       ③ 必须指定字段
   │       ▼                     │
   │  execute_sql_query()        │  审批通过 → 执行建表
   └─────────────────────────────┘
```

#### 两个 Agent 角色

| 角色 | System Prompt 设定 | 职责 |
|---|---|---|
| **Dev Agent** (`call_dev_agent`) | "你是数仓开发小弟...只输出纯 SQL" | 根据 schema + 需求生成 SQL；收到 REJECT 时按批评意见修正 |
| **QA Agent** (`call_qa_agent`) | "你是严苛的数仓首席架构师...以 REJECT/PASS 开头" | 审查 Dev 的 SQL，检查 SELECT *、关键字大小写、字段指定 |

#### 自我修正循环

```python
MAX_RETRIES = 3

for round in 1..3:
    verdict = call_qa_agent(sql)
    if verdict == "PASS":
        执行 SQL → 打印结果 → 返回
    else:
        将 REJECT 意见回传给 Dev → 生成修正版 SQL → 下一轮
```

#### 已验证的实战效果

测试需求（钓鱼式）：
> "把订单表和用户表的所有数据全部拼在一起查出来，帮我建个宽表。"

**Round 1**：Dev 写出 `SELECT * ... FULL OUTER JOIN ...` → QA 打出 **REJECT**（捕获 SELECT *）  
**Round 2**：Dev 修正为显式列出全部 8 个字段 → QA 打出 **PASS** → 执行成功，返回 2008 行

闭环在 **2 轮内收敛**，证明自我修正机制有效。

---

## 四、当前数仓数据资产

执行 `agent.py` 后，`dev_dw.db` 中包含 3 张表：

| 表名 | 分层 | 行数 | 字段数 | 说明 |
|---|---|---|---|---|
| `ods_users` | ODS 操作数据层 | 500 | 4 | 用户注册原始数据 |
| `ods_orders` | ODS 操作数据层 | 2,000 | 4 | 订单流水原始数据 |
| `dws_city_sales` | DWS 汇总层 | 10 | 2 | 各城市总销售额排行（首轮智能体自动生成） |

---

## 五、Git 提交历史

| Commit | 说明 |
|---|---|
| `f71a5fc` | 项目初始化 |
| `0b69d66` | 跑通数仓智能体"理解需求 → 建表"端到端 MVP 闭环（单 Agent 架构） |
| `2df5502` | 升级双 Agent 架构，实现基于数仓规范的 SQL 自我迭代审查（2 轮收敛） |

---

## 六、安全防护总结

| 防护项 | 措施 |
|---|---|
| API Key 泄露 | `.env` 已加入 `.gitignore`，Git 不追踪 |
| 数据库文件误提交 | `*.db` / `*.sqlite` / `*.sqlite3` 已加入 `.gitignore` |
| 编译产物污染 | `__pycache__/`、`*.pyc` 已加入 `.gitignore` |
| IDE 配置文件 | `.idea/`、`.vscode/` 已加入 `.gitignore` |

---

