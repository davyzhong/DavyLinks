# 六阶段工作流

> 本文档描述 DavyLinks 管线的六个阶段：扫描聚类 → AI 摘要 → 飞书多维表格 → 飞书推送 → Obsidian 沉淀。
> 整体数据流图见 [overview.md](overview.md)；聚类算法细节见 [clustering.md](clustering.md)；LLM 摘要与排序细节见 [summarization.md](summarization.md)；状态管理与配置见 [data-flow.md](data-flow.md)。

## Phase 1-2: 扫描 + 聚类

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

关键词过滤评分算法与话题聚类算法的完整细节（含复杂度分析）见 [clustering.md](clustering.md)。

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

### 设计决策：为什么用 64 位 hash_url？

**问题**: 早期版本用 32 位 hash，生日悖论下约 7 万篇文章即达 50% 碰撞概率

**方案**: 扩展到 64 位（16 hex chars），碰撞概率极低

**权衡**: hash 值更大，但对于当前规模（<1000 篇/天）完全可接受

## Phase 3: AI 摘要 + 排序

**文件**: `scripts/summarize.py`

- 4 个 LLM Provider（Qwen / Kimi / Zhipu / MiniMax）并行摘要，Round-robin 分配，失败自动 fallback
- 不可变数据流：所有函数返回新 dict，不修改输入
- 最终排序公式：`final_score = relevance_score + quality_rating × 2 + cross_bonus`

LLM 配置、分配策略、摘要 Prompt、排序公式的完整说明见 [summarization.md](summarization.md)。

## Phase 3.5: 飞书多维表格

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

## Phase 4: 飞书消息推送

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

## Phase 5: Obsidian 沉淀

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

### 设计决策：为什么仅 TOP 5 写入 Obsidian？

**考虑**:
- 避免知识库膨胀（每天 50+ 篇 → 一年 18000 篇）
- 聚焦真正有价值的信息
- 飞书表格保留完整记录可供回溯
