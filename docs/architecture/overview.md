# 系统概述

> 本文档介绍 DavyLinks 的整体定位、端到端数据流、扩展方式与监控调试手段。
> 各阶段的实现细节见 [pipeline.md](pipeline.md)（六阶段工作流）、[clustering.md](clustering.md)（聚类算法）、[summarization.md](summarization.md)（AI 摘要）、[data-flow.md](data-flow.md)（状态与配置）。

## 系统定位

DavyLinks 是一个自动化科技资讯聚合系统，从多个公开信息源定时抓取内容，经过 AI 筛选、摘要、排序后，将每日精华推送到飞书并沉淀到 Obsidian 知识库。

整体管线：

```
RSS/Atom → 扫描去重 → 话题聚类 → AI 摘要 → 飞书表格 → 飞书推送 → Obsidian
```

## 数据流

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

## 扩展性

### 新增信息源

1. 编辑 `config/sources.json`
2. 添加 source 配置（name, url, weight, keywords）
3. 无需修改代码

### 新增 LLM Provider

1. 编辑 `config/secrets.yaml` 的 `llm_providers`
2. 如果是 Anthropic 格式，添加到 `ANTHROPIC_PROVIDERS`（双 API 格式的原因见 [summarization.md](summarization.md)）
3. 无需修改代码

### 新增输出目标

1. 创建 `scripts/push_XXX.py`
2. 实现 `push_articles(articles)` 函数
3. 在 `pipeline.py` 中调用

## 监控与调试

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
| 聚类似乎不准 | 调低 `chinese_overlap` 阈值 (默认 0.35，见 [clustering.md](clustering.md)) |
| 文章量太少 | 检查 `global_keywords` 是否太严格 |
