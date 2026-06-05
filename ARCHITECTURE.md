# DavyLinks 架构设计

> 本文档描述 DavyLinks 知识助理的系统架构、数据流和核心设计决策。

## 1. 系统概述

DavyLinks 是一个自动化科技资讯聚合系统，从多个公开信息源定时抓取内容，经过 AI 筛选、摘要、排序后，将每日精华推送到飞书并沉淀到 Obsidian 知识库。

## 2. 六阶段工作流

### Phase 1-2: 扫描 + 聚类

**文件**: `scripts/scan_articles.py`

**职责**:
- 从 RSS 源和微信公众号获取文章列表
- 提取标题、链接、来源、发布时间
- URL 去重（基于 64 位 hash）
- 关键词过滤 + 相关性评分
- 话题聚类（倒排索引 + Union-Find）

**数据来源**:
- 6 个活跃 RSS 源（36氪、少数派、量子位、IT之家、Hacker News 等）
- 微信公众号 via wewe-rss Atom feed (`http://localhost:4000/feeds/all.atom`)
- 支持通过 `config/sources.json` 动态扩展

**关键词过滤评分算法**:
```
score = source_weight × 2
      + title_matches × 3
      + content_matches × 1
      + recency_bonus (24h:+5, 48h:+3, 72h:+1)
```
阈值：score >= 8

**话题聚类算法**:
- **Phase 1**: 预计算每篇文章的实体名（英文词汇）和中文二元组
- **Phase 2**: 构建两个倒排索引（实体索引 + 二元组索引）
- **Phase 3**: 从索引生成候选对（跳过过大的泛化桶，`max_bucket_size=50`）
- **Phase 4**: Union-Find 聚类，只比较有候选对的文章
- **Phase 5**: 按根节点分组
- **Phase 6**: 构建话题对象，评分加成 `cross_bonus = min(source_count, 5) × 15`

**复杂度**: O(n) 建索引 → O(k²) 组内比较 (k<<n)，比较次数减少 80-95%

**输出格式**:
```json
{
  "scanned": 87,
  "filtered": 23,
  "articles": [...],
  "total": 15,
  "multi_source": 3
}
```

### Phase 3: AI 摘要 + 排序

**文件**: `scripts/summarize.py`

**LLM 配置**:
- Qwen (OpenAI 格式)
- Kimi (Anthropic 格式)
- Zhipu (Anthropic 格式)
- MiniMax (OpenAI 格式)
- 配置来源：`config_loader.get_llm_provider_configs()` → 环境变量 > `config/secrets.yaml` > `~/.davylinks/secrets.yaml`；保留 `~/.config/llm-providers.yaml` 作为兼容 fallback

**分配策略**:
- Round-robin 分配 TOP 5 文章
- 失败自动 fallback 到下一个 LLM
- 并行执行（ThreadPoolExecutor），理论耗时 ~50s (vs 串行 250s)

**不可变数据流**:
- `summarize_one()` 返回新 dict，不修改输入 article
- `final_sort()` 返回新列表，不修改输入
- 所有错误路径（LLM 失败、超时）也返回新 dict

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

### Phase 3.5: 飞书多维表格

**文件**: `scripts/feishu_bitable.py`

**职责**: 将文章写入飞书多维表格（Bitable）

**配置加载**:
- 延迟加载：首次调用 `_get_config()` 时初始化，不在 import 时读取 secrets
- 通过 `config_loader.get_feishu_config()` 统一加载
- 环境变量优先 (`FEISHU_APP_ID` 等)
- Fallback 到 `config/secrets.yaml` → `~/.davylinks/secrets.yaml`

**批量写入**:
- 每批最多 500 条
- 失败时降级为逐条写入
- 输出 `{"bitable_ok": N, "bitable_fail": M}` 供 pipeline 统计

**数据表结构**:
| 字段 | 类型 | 说明 |
|------|------|------|
| 日期 | Date | 发布日期（毫秒时间戳） |
| 标题 | Text | 文章标题 |
| 来源 | Text | 来源名称 |
| 来源列表 | Text | 多源列表（顿号分隔） |
| 来源数量 | Number | 来源计数 |
| 分类 | Text | 分类 |
| 摘要 | Text | AI 摘要 |
| 热度评分 | Number | final_score |
| 是否多源交叉 | Checkbox | 聚类标记 |
| 链接 | URL | 原文链接（超链接格式） |

### Phase 4: 飞书消息推送

**文件**: `scripts/push_feishu.py`

**职责**: 生成每日精华内容并发送到飞书群消息

**推送方式**:
1. **Davybase notify.py**（优先）: 复用 Davybase 的通知脚本
2. **直接 Webhook**（fallback）: 直接调用飞书 Webhook API

**配置加载**:
- 延迟加载：首次调用 `_get_davybase_config()` / `_get_feishu_webhook()` 时初始化
- 通过 `config_loader` 统一加载

**推送内容**:
- TOP 5 文章：标题 + AI 摘要 + 来源 + 链接
- 值得关注列表：5-10 篇
- 统计信息

**飞书 Card 格式**:
- Header: 绿色主题 + 日期
- Body: Markdown 格式
- Footer: 统计信息

### Phase 5: Obsidian 沉淀

**文件**: `scripts/save_obsidian.py`

**路径**: `ObsidianWiki/知识助理/每日精华/YYYY-MM-DD.md`

Vault 路径优先读取 `OBSIDIAN_VAULT_PATH`，其次读取 `obsidian.vault_path`。

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
┌─────────────────┐  ┌─────────────────┐
│  blogwatcher-cli │  │  wewe-rss Atom  │
│  (RSS sources)   │  │  (微信公众号)    │
└───────┬─────────┘  └───────┬─────────┘
        │                     │
        └──────────┬──────────┘
                   │
                   ▼
┌─────────────────────────┐
│ scan_articles.py        │
│ - 解析文章              │
│ - 去重 (64-bit hash)    │
│ - 关键词过滤 + 评分     │
│ - 话题聚类 (倒排索引)    │
│ 输出: scanned/filtered  │
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
│ push_feishu.py          │
│ - 生成推送内容          │
│ - 发送飞书群消息        │
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
2. 提取中文二元组
3. 构建两个倒排索引：`entity → [文章 ID]` 和 `bigram → [文章 ID]`
4. 只比较有共享实体或二元组的文章对（跳过过大的泛化桶）

**收益**: 比较次数减少 80-95%，聚类质量保持不变

### 4.2 为什么用 64 位 hash_url？

**问题**: 早期版本用 32 位 hash，生日悖论下约 7 万篇文章即达 50% 碰撞概率

**方案**: 扩展到 64 位（16 hex chars），碰撞概率极低

**权衡**: hash 值更大，但对于当前规模（<1000 篇/天）完全可接受

### 4.3 为什么用不可变数据流？

**问题**: 早期版本函数直接修改传入的 article dict，导致：
- 调试时难以追踪数据流
- 测试时需要 deep copy 输入数据
- 副作用难以预测

**方案**: 所有函数返回新 dict（使用 `{**article, ...}` 模式），不修改输入

**收益**:
- 测试简单：直接比较输入输出
- 调试容易：数据流清晰
- 无副作用：函数可安全重试

### 4.4 为什么用延迟配置加载？

**问题**: 早期版本在模块顶层加载配置（`FEISHU_APP_ID = _feishu_config["app_id"]`），导致：
- import 时读取 secrets.yaml，可能泄露凭证
- 配置缺失时 import 就崩
- 测试时需要 mock 模块级变量

**方案**: 延迟加载（`_get_config()` 首次调用时初始化）

**收益**:
- import 时不读取 secrets
- 配置缺失只在运行时报错
- 测试简单：mock 函数而非模块变量

### 4.5 为什么用 SQL 参数化查询？

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

### 4.6 为什么用 executemany？

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

### 4.7 为什么用 INSERT OR REPLACE？

**问题**: 早期版本用 `INSERT OR IGNORE`，导致文章摘要无法更新

**方案**: 改用 `INSERT OR REPLACE`，支持摘要更新

**权衡**: 同一天多次运行会覆盖记录（设计接受）

### 4.8 为什么 LLM 用 Anthropic + OpenAI 双格式？

**原因**: 不同厂商 API 格式不统一
- Kimi、Zhipu → Anthropic 格式 (`/v1/messages`)
- Qwen、MiniMax → OpenAI 格式 (`/chat/completions`)

**解决**: `ANTHROPIC_PROVIDERS = {"kimi", "zhipu"}` 白名单判断

### 4.9 为什么仅 TOP 5 写入 Obsidian？

**考虑**:
- 避免知识库膨胀（每天 50+ 篇 → 一年 18000 篇）
- 聚焦真正有价值的信息
- 飞书表格保留完整记录可供回溯

### 4.10 为什么用统一配置加载器？

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

- `processed_articles`: 保留 90 天（使用参数化查询防止 SQL 注入）
- 成功进入摘要输出的 `articles` 会整体标记为已处理（使用 `executemany` 批量插入），避免 top15 之外的话题在后续运行中反复出现
- `run_log`: 永久保留（数据量小，用于统计）

## 6. 配置系统

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

### 日志配置

```python
from logging_config import setup_logging
logger = setup_logging(__name__)

# 通过 LOG_LEVEL 环境变量控制级别
# 输出到 stderr + 可选文件
```

## 7. 测试

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

## 8. 性能优化

| 优化点 | 方案 | 效果 |
|--------|------|------|
| 话题聚类 | 倒排索引（实体 + 二元组） | O(n²)→O(n), 80-95% 减少 |
| LLM 摘要 | 4 路并行 + fallback | 250s→50s |
| 去重检查 | SQLite 索引 | O(1) 查询 |
| 批量写入 | executemany | 减少数据库往返 |
| 日志系统 | 标准 logging | 阻塞最小化 |

## 9. 扩展性

### 新增信息源

1. 编辑 `config/sources.json`
2. 添加 source 配置（name, url, weight, keywords）
3. 无需修改代码

### 新增 LLM Provider

1. 编辑 `config/secrets.yaml` 的 `llm_providers`
2. 如果是 Anthropic 格式，添加到 `ANTHROPIC_PROVIDERS`
3. 无需修改代码

### 新增输出目标

1. 创建 `scripts/push_XXX.py`
2. 实现 `push_articles(articles)` 函数
3. 在 `pipeline.py` 中调用

## 10. 监控与调试

### 查看运行日志

```bash
# 查看最新运行统计
.venv/bin/python scripts/state_db.py

# 查看详细日志
tail -f ~/.davylinks/daily.log  # 如果配置了文件输出

# 调试模式
LOG_LEVEL=DEBUG .venv/bin/python scripts/pipeline.py
```

### 常见问题

| 问题 | 排查步骤 |
|------|----------|
| 飞书推送失败 | 检查 `FEISHU_*` 环境变量 |
| LLM 摘要超时 | 检查网络 + API key 配额 |
| 聚类似乎不准 | 调低 `chinese_overlap` 阈值 (默认 0.35) |
| 文章量太少 | 检查 `global_keywords` 是否太严格 |
