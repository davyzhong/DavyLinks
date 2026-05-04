# DavyLinks 架构设计

> 本文档描述 DavyLinks 知识助理的系统架构、数据流和核心设计决策。

## 1. 系统概述

DavyLinks 是一个自动化科技资讯聚合系统，从多个公开信息源定时抓取内容，经过 AI 筛选、摘要、排序后，将每日精华推送到飞书并沉淀到 Obsidian 知识库。

## 2. 五阶段工作流

### Phase 1: 扫描抓取

**文件**: `scripts/scan_articles.py`

**职责**:
- 从 RSS 源获取文章列表
- 提取标题、链接、来源、发布时间
- 初步去重（基于 URL hash）

**数据来源**:
- 8 个配置的 RSS 源（36 氪、少数派、机器之心等）
- 支持通过 `config/sources.json` 动态扩展

**输出格式**:
```json
[
  {
    "title": "文章标题",
    "url": "https://...",
    "source": "36 氪",
    "published_at": "2026-05-04T10:00:00Z",
    "id": 12345678
  }
]
```

### Phase 2: 去重过滤 + 话题聚类

**文件**: `scripts/scan_articles.py` (续)

**去重**:
- 查询 `state_db.processed_articles` 排除已处理 URL
- 支持 90 天自动清理

**关键词过滤**:
- 源级 `keywords` ∪ `global_keywords`
- 评分算法：
  ```
  score = source_weight × 2
        + title_matches × 3
        + content_matches × 1
        + recency_bonus (24h:+5, 48h:+3, 72h:+1)
  ```
- 阈值：score >= 8

**话题聚类 (优化版)**:
- 算法：倒排索引 + Union-Find
- 复杂度：O(n) 建索引 → O(k²) 组内比较 (k<<n)
- 判断逻辑：
  1. 共享英文实体名 → 聚类
  2. 中文二元组重叠度 >= 0.35 → 聚类
- 评分加成：`cross_bonus = min(source_count, 5) × 15`

### Phase 3: AI 摘要 + 排序

**文件**: `scripts/summarize.py`

**LLM 配置**:
- Qwen (OpenAI 格式)
- Kimi (Anthropic 格式)
- Zhipu (Anthropic 格式)
- MiniMax (OpenAI 格式)

**分配策略**:
- Round-robin 分配 TOP 5 文章
- 失败自动 fallback 到下一个 LLM
- 并行执行，理论耗时 ~50s (vs 串行 250s)

**摘要 Prompt**:
```
请用一句话（50 字以内）总结这篇文章的要点。

标题：{title}
来源：{source}
内容：{content (前 2000 字)}
```

**最终排序**:
```
final_score = relevance_score + quality_rating × 2 + cross_bonus
```

### Phase 4: 飞书推送

**文件**: `scripts/feishu_bitable.py`

**配置加载**:
1. 环境变量优先 (`FEISHU_APP_ID` 等)
2. Fallback 到 `~/.davylinks/secrets.yaml`

**推送内容**:
- TOP 5 文章：标题 + AI 摘要 + 来源 + 链接
- 值得关注列表：5-10 篇
- 统计信息

**数据表结构**:
| 字段 | 类型 | 说明 |
|------|------|------|
| 日期 | Date | 发布日期 |
| 标题 | Text | 文章标题 |
| 来源 | Text | 来源名称 |
| 来源列表 | Text | 多源列表 |
| 来源数量 | Number | 来源计数 |
| 分类 | Text | 分类 |
| 摘要 | Text | AI 摘要 |
| 热度评分 | Number | final_score |
| 是否多源交叉 | Checkbox | 聚类标记 |
| 链接 | URL | 原文链接 |

### Phase 5: Obsidian 沉淀

**文件**: `scripts/save_obsidian.py`

**路径**: `ObsidianWiki/知识助理/每日精华/YYYY-MM-DD.md`

**Frontmatter**:
```yaml
---
type: daily-digest
date: 2026-05-04
sources_count: 42
articles_count: 8
auto_generated: true
tags: [davylinks, daily-digest]
---
```

**内容结构**:
- TOP 5 详细卡片（摘要 + 评分表 + 标签）
- 值得关注列表
- 生成来源统计

**周报功能**:
- 每周一生成 `YYYY-Wxx.md`
- 汇总上周所有每日精华

## 3. 数据流

```
┌─────────────┐
│   RSS 源     │
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ scan_articles.py        │
│ - 获取文章              │
│ - 去重 (SQLite)          │
│ - 话题聚类 (倒排索引)    │
└──────┬──────────────────┘
       │ [articles]
       ▼
┌─────────────────────────┐
│ summarize.py            │
│ - LLM 并行摘要           │
│ - 质量评分              │
│ - 最终排序              │
└──────┬──────────────────┘
       │ [top5 + other]
       ▼
┌─────────────────────────┐
│ feishu_bitable.py       │
│ - 写入飞书多维表格       │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ save_obsidian.py        │
│ - 生成每日笔记          │
│ - (可选) 生成周报        │
└─────────────────────────┘
```

## 4. 核心设计决策

### 4.1 为什么用倒排索引聚类？

**问题**: O(n²) 两两比较在文章数>100 时成为瓶颈

**方案**:
1. 提取标题中的英文实体名（DeepSeek、LLaMA 等）
2. 构建 `entity → [文章 ID]` 倒排索引
3. 只比较有共享实体的文章对

**收益**: 比较次数减少 80-95%，聚类质量保持不变

### 4.2 为什么用 INSERT OR REPLACE？

**问题**: 早期版本用 `INSERT OR IGNORE`，导致文章摘要无法更新

**方案**: 改用 `INSERT OR REPLACE`，支持摘要更新

**权衡**: 同一天多次运行会覆盖记录（设计接受）

### 4.3 为什么 LLM 用 Anthropic + OpenAI 双格式？

**原因**: 不同厂商 API 格式不统一
- Kimi、Zhipu → Anthropic 格式 (`/v1/messages`)
- Qwen、MiniMax → OpenAI 格式 (`/chat/completions`)

**解决**: `ANTHROPIC_PROVIDERS = {"kimi", "zhipu"}` 白名单判断

### 4.4 为什么仅 TOP 5 写入 Obsidian？

**考虑**:
- 避免知识库膨胀（每天 50+ 篇 → 一年 18000 篇）
- 聚焦真正有价值的信息
- 飞书表格保留完整记录可供回溯

## 5. 状态管理

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

- `processed_articles`: 保留 90 天
- `run_log`: 永久保留（数据量小，用于统计）

## 6. 配置系统

### 三层配置优先级

1. **环境变量** (最高优先级)
   - `FEISHU_APP_ID`, `FEISHU_APP_SECRET`
   - `LOG_LEVEL=DEBUG`

2. **~/.davylinks/secrets.yaml**
   - 飞书凭证
   - LLM API Key

3. **config/*.json**
   - 信息源配置
   - 关键词配置

### 日志配置

```python
from logging_config import setup_logging
logger = setup_logging(__name__)

# 通过 LOG_LEVEL 环境变量控制级别
# 输出到 stderr + 可选文件
```

## 7. 性能优化

| 优化点 | 方案 | 效果 |
|--------|------|------|
| 话题聚类 | 倒排索引 | O(n²)→O(n), 80-95% 减少 |
| LLM 摘要 | 4 路并行 + fallback | 250s→50s |
| 去重检查 | SQLite 索引 | O(1) 查询 |
| 日志系统 | 异步 handler | 阻塞最小化 |

## 8. 扩展性

### 新增信息源

1. 编辑 `config/sources.json`
2. 添加 source 配置（name, url, weight, keywords）
3. 无需修改代码

### 新增 LLM Provider

1. 编辑 `~/.config/llm-providers.yaml`
2. 如果是 Anthropic 格式，添加到 `ANTHROPIC_PROVIDERS`
3. 无需修改代码

### 新增输出目标

1. 创建 `scripts/push_XXX.py`
2. 实现 `push_articles(articles)` 函数
3. 在 `pipeline.py` 中调用

## 9. 监控与调试

### 查看运行日志

```bash
# 查看最新运行统计
python scripts/state_db.py

# 查看详细日志
tail -f ~/.davylinks/daily.log  # 如果配置了文件输出

# 调试模式
LOG_LEVEL=DEBUG python scripts/pipeline.py
```

### 常见问题

| 问题 | 排查步骤 |
|------|----------|
| 飞书推送失败 | 检查 `FEISHU_*` 环境变量 |
| LLM 摘要超时 | 检查网络 + API key 配额 |
| 聚类似乎不准 | 调低 `chinese_overlap` 阈值 (默认 0.35) |
| 文章量太少 | 检查 `global_keywords` 是否太严格 |
