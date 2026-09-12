# SQLite 状态库 Schema

状态库位置：`~/.davylinks/state.db`

## 表结构

### processed_articles — 已处理文章

```sql
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
```

| 字段 | 类型 | 说明 |
|------|------|------|
| url | TEXT | 文章 URL（主键，去重依据） |
| title | TEXT | 文章标题 |
| source | TEXT | 来源名称 |
| category | TEXT | 分类 |
| published_at | DATETIME | 发布时间 |
| processed_at | DATETIME | 处理时间（默认当前时间） |
| relevance_score | REAL | 相关性评分 |
| summary | TEXT | AI 摘要 |
| pushed | INTEGER | 是否已推送（0/1） |

**清理策略**: 保留 90 天，超期自动清理。

### run_log — 运行日志

```sql
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

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 自增主键 |
| run_date | DATE | 运行日期（唯一） |
| scanned | INTEGER | 扫描到文章数 |
| filtered | INTEGER | 过滤后文章数 |
| summarized | INTEGER | 摘要完成数 |
| pushed | INTEGER | 推送成功数 |
| errors | INTEGER | 错误数 |
| duration_s | REAL | 耗时（秒） |
| status | TEXT | 运行状态 |

**清理策略**: 永久保留（数据量小，用于统计）。

## 安全说明

- 所有写操作使用参数化查询（防 SQL 注入）
- `mark_processed` 使用 `executemany` 批量插入
- `INSERT OR REPLACE` 支持摘要更新
