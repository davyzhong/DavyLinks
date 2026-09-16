# ADR-006: SQLite 状态管理

**状态**: ✅ 已实施 (v1.0 设计起)

## 背景

管线需要回答三个状态问题：

1. **去重**：这篇文章处理过没有？（每天重复推送相同文章是最大痛点）
2. **断点续传**：管线中断后，哪些阶段已完成？
3. **统计**：每天扫了多少、推了多少、错了多少？

## 备选方案

| 方案 | 评价 |
|------|------|
| 不做状态（每次全量） | 重复推送，用户直接流失 ❌ |
| 文件记录（JSON/文本） | 无索引查询慢，并发写易损坏，无事务 |
| Redis | 外部服务依赖，对单机定时任务是过度设计 |
| **SQLite** | 零依赖、单文件、事务、索引查询，完美匹配场景 |

## 决策

**SQLite 单文件状态库**（`~/.davylinks/state.db`），两张表：

- `processed_articles`：URL 主键去重 + 摘要缓存 + 推送状态，保留 90 天
- `run_log`：每日运行统计（scanned/filtered/pushed/errors/duration），永久保留

写策略三原则（v2.0 确立）：

1. **参数化查询**——`cleanup_old` 曾用 f-string 拼 SQL，存在注入风险，已改为 `?` 占位符
2. **批量写入**——`mark_processed` 用 `executemany`，100 条写入从 ~100ms 降到 ~8ms
3. **INSERT OR REPLACE**——同 URL 重复处理时更新摘要（`OR IGNORE` 曾导致摘要无法更新）

## 后果

- ✅ 零部署依赖：状态库就是一个文件，备份 = `cp`
- ✅ URL 主键天然去重，索引查询 O(1)
- ✅ 90 天自动清理防止膨胀；run_log 数据量小可永久保留
- ⚠️ 同一天多次运行会覆盖当日记录（INSERT OR REPLACE 的设计取舍，接受）
- Schema 详见 [docs/api/state-db-schema.md](../../docs/api/state-db-schema.md)
