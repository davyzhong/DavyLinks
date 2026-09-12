# 状态管理、配置系统、测试与性能

> 本文档描述 DavyLinks 的持久化状态（SQLite）、三层配置体系与统一配置加载器、测试覆盖与运行方式、性能优化点，以及与之相关的核心设计决策。
> 管线各阶段见 [pipeline.md](pipeline.md)；聚类算法见 [clustering.md](clustering.md)；AI 摘要见 [summarization.md](summarization.md)。

## 状态管理

状态库位置：`~/.davylinks/state.db`（90 天自动清理）。

### SQLite Schema

```sql
-- 已处理文章
CREATE TABLE processed_articles (
    url         TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    source      TEXT NOT NULL,
    category    TEXT DEFAULT '',
    published_at DATETIME,
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    relevance_score REAL DEFAULT 0,
    summary     TEXT DEFAULT '',
    pushed      INTEGER DEFAULT 0
);

-- 运行日志
CREATE TABLE run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    DATE NOT NULL UNIQUE,
    scanned     INTEGER DEFAULT 0,
    filtered    INTEGER DEFAULT 0,
    summarized  INTEGER DEFAULT 0,
    pushed      INTEGER DEFAULT 0,
    errors      INTEGER DEFAULT 0,
    duration_s  REAL DEFAULT 0,
    status      TEXT DEFAULT 'success'
);
```

### 清理策略

- `processed_articles`: 保留 90 天（使用参数化查询防止 SQL 注入）
- 成功进入摘要输出的 `articles` 会整体标记为已处理（使用 `executemany` 批量插入），避免 top15 之外的话题在后续运行中反复出现
- `run_log`: 永久保留（数据量小，用于统计）

### 设计决策：为什么用 SQL 参数化查询？

**问题**: 早期版本 `cleanup_old` 用 f-string 拼接 SQL：
```python
conn.execute(f"DELETE ... datetime('now', '-{days} days')")
```
虽然 `days` 参数当前来自代码，但函数签名是 public API，存在 SQL 注入风险

**方案**: 参数化查询：
```python
conn.execute("DELETE ... datetime('now', ?)", (f"-{int(days)} days",))
```

**收益**: 防止 SQL 注入，代码更安全

### 设计决策：为什么用 executemany？

**问题**: 早期版本 `mark_processed` 逐条 INSERT：
```python
for a in articles:
    conn.execute("INSERT ...", (...))
```

**方案**: 批量插入：
```python
conn.executemany("INSERT ...", rows)
```

**收益**: 减少数据库往返，性能更好

### 设计决策：为什么用 INSERT OR REPLACE？

**问题**: 早期版本用 `INSERT OR IGNORE`，导致文章摘要无法更新

**方案**: 改用 `INSERT OR REPLACE`，支持摘要更新

**权衡**: 同一天多次运行会覆盖记录（设计接受）

## 配置系统

### 三层配置优先级

1. **环境变量** (最高优先级)
   - `FEISHU_APP_ID`, `FEISHU_APP_SECRET`
   - `LOG_LEVEL=DEBUG`

2. **config/secrets.yaml** (推荐主位置)
   - 飞书凭证
   - LLM API Key
   - Obsidian vault 路径
   - 可选 Davybase notify 路径

3. **~/.davylinks/secrets.yaml** (备用位置)
   - 向后兼容的配置路径

4. **config/*.json**
   - 信息源配置
   - 关键词配置

### 统一配置加载器

**文件**: `scripts/config_loader.py`

**职责**:
- 读取 YAML 配置（支持 PyYAML 或内置简易解析器）
- 合并多层配置（deep merge）
- 提供统一的配置访问接口

**关键函数**:
```python
load_secrets()                    # 加载并合并所有 secrets
get_feishu_config()               # 飞书配置
get_llm_provider_configs()        # LLM Provider 配置
get_obsidian_config()             # Obsidian 配置
get_davybase_config()             # Davybase 配置
```

**延迟加载**: 各模块在首次调用时加载配置，不在 import 时读取

### 设计决策：为什么用统一配置加载器？

**问题**: 早期版本每个脚本都有自己的配置加载逻辑（`_parse_yaml_simple` 重复定义 3 次）

**方案**: `scripts/config_loader.py` 集中管理所有配置加载：
- `get_feishu_config()`
- `get_llm_provider_configs()`
- `get_obsidian_config()`
- `get_davybase_config()`

**收益**:
- 单一配置加载逻辑
- 配置优先级统一（环境变量 > config/secrets.yaml > ~/.davylinks/secrets.yaml）
- 各模块不再重复实现 YAML 解析

### 设计决策：为什么用延迟配置加载？

**问题**: 早期版本在模块顶层加载配置（`FEISHU_APP_ID = _feishu_config["app_id"]`），导致：
- import 时读取 secrets.yaml，可能泄露凭证
- 配置缺失时 import 就崩
- 测试时需要 mock 模块级变量

**方案**: 延迟加载（`_get_config()` 首次调用时初始化）

**收益**:
- import 时不读取 secrets
- 配置缺失只在运行时报错
- 测试简单：mock 函数而非模块变量

### 日志配置

```python
from logging_config import setup_logging
logger = setup_logging(__name__)

# 通过 LOG_LEVEL 环境变量控制级别
# 输出到 stderr + 可选文件
```

## 测试

### 测试覆盖

项目包含 19 个测试用例（`tests/` 目录）：

| 测试文件 | 覆盖内容 |
|---------|---------|
| `test_config_loader.py` | 配置加载优先级、环境变量覆盖 |
| `test_config_integration.py` | 模块集成（summarize、save_obsidian 使用 config_loader） |
| `test_pipeline.py` | 管线编排、错误计数、状态记录 |
| `test_push_feishu.py` | 飞书推送、webhook 配置 |
| `test_scan_articles.py` | 话题聚类算法正确性 |
| `test_state_db.py` | 数据库操作（批量插入、参数化查询、update 语义） |
| `test_immutability.py` | 不可变性保证（filter_by_keywords、summarize_one、final_sort 不修改输入） |

### 运行测试

```bash
# 全部测试
.venv/bin/python -m pytest tests/ -v

# 带覆盖率
.venv/bin/python -m pytest tests/ --cov=scripts --cov-report=term-missing

# 特定模块
.venv/bin/python -m pytest tests/test_immutability.py -v
```

## 性能优化

| 优化点 | 方案 | 效果 |
|--------|------|------|
| 话题聚类 | 倒排索引（实体 + 二元组，见 [clustering.md](clustering.md)） | O(n²)→O(n), 80-95% 减少 |
| LLM 摘要 | 4 路并行 + fallback（见 [summarization.md](summarization.md)） | 250s→50s |
| 去重检查 | SQLite 索引 | O(1) 查询 |
| 批量写入 | executemany | 减少数据库往返 |
| 日志系统 | 标准 logging | 阻塞最小化 |
