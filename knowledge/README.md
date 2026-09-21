# DavyLinks 知识库

项目沉淀的领域知识、设计决策和演进记录。与项目文档（docs/）的区别：

- **docs/** 回答"怎么用"——面向使用者和开发者
- **knowledge/** 回答"为什么这么做"和"这个领域是什么样"——面向决策者

## 结构

```
knowledge/
├── domain/                # 领域知识（行业认知）
│   ├── rss-ecosystem.md         # RSS 生态现状
│   ├── llm-landscape.md         # LLM 选型对比
│   ├── feishu-platform.md       # 飞书平台能力
│   ├── obsidian-workflow.md     # Obsidian 知识管理
│   └── tech-news-landscape.md   # 科技资讯源分析
│
├── decisions/             # 架构决策记录（ADR）
│   ├── README.md                # ADR 索引
│   ├── 001-inverted-index-clustering.md
│   ├── 002-immutable-data-flow.md
│   ├── 003-lazy-config-loading.md
│   ├── 004-multi-llm-fallback.md
│   ├── 005-top5-only-obsidian.md
│   ├── 006-sqlite-state-management.md
│   ├── 007-64bit-hash-dedup.md
│   └── 008-dual-llm-api-format.md
│
├── evolution/             # 项目演进记录
│   ├── v1.0-mvp.md              # MVP 阶段
│   ├── v2.0-code-review.md      # 代码审查阶段
│   └── direction-changes.md     # 方向调整记录
│
└── reference/             # 速查手册
    ├── sources-analysis.md      # 信息源详细分析
    ├── llm-api-cheatsheet.md    # LLM API 格式速查
    └── feishu-api-cheatsheet.md # 飞书 API 速查
```

## 使用场景

| 场景 | 看哪里 |
|------|--------|
| 选型 LLM 供应商 | [domain/llm-landscape.md](domain/llm-landscape.md) |
| 新增信息源 | [domain/tech-news-landscape.md](domain/tech-news-landscape.md) + [reference/sources-analysis.md](reference/sources-analysis.md) |
| 理解某个设计决策 | [decisions/](decisions/) |
| 查 LLM API 格式 | [reference/llm-api-cheatsheet.md](reference/llm-api-cheatsheet.md) |
| 了解项目历史 | [evolution/](evolution/) |
