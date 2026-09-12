# DavyLinks 文档导航

## 文档结构

```
docs/
├── architecture/          # 架构设计文档
│   ├── overview.md        # 系统架构总览
│   ├── pipeline.md        # 六阶段管线详解
│   ├── clustering.md      # 聚类算法设计
│   ├── summarization.md   # LLM 摘要与评分机制
│   └── data-flow.md       # 数据流与状态管理
│
├── guides/                # 使用指南
│   ├── quickstart.md      # 快速上手
│   ├── configuration.md   # 配置详解
│   ├── feishu-setup.md    # 飞书配置指南
│   ├── obsidian-setup.md  # Obsidian 配置指南
│   └── troubleshooting.md # 故障排查手册
│
├── api/                   # 接口文档
│   ├── pipeline-cli.md    # 命令行接口
│   ├── config-format.md   # 配置文件格式规范
│   └── state-db-schema.md # SQLite 状态库 Schema
│
└── design/                # 设计文档
    ├── original-requirement.md  # 原始需求文档（历史）
    └── current-design.md        # 当前设计文档
```

## 快速查找

| 我想... | 看这里 |
|---------|--------|
| 快速开始 | [guides/quickstart.md](guides/quickstart.md) |
| 配置飞书 | [guides/feishu-setup.md](guides/feishu-setup.md) |
| 配置 Obsidian | [guides/obsidian-setup.md](guides/obsidian-setup.md) |
| 理解系统架构 | [architecture/overview.md](architecture/overview.md) |
| 理解聚类算法 | [architecture/clustering.md](architecture/clustering.md) |
| 排查问题 | [guides/troubleshooting.md](guides/troubleshooting.md) |
| 查看配置格式 | [api/config-format.md](api/config-format.md) |
| 了解设计决策 | [knowledge/decisions/](../knowledge/decisions/) |
