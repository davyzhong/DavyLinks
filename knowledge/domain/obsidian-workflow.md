# Obsidian 知识管理工作流

> 领域知识：DavyLinks 在 Obsidian 中的沉淀策略，以及与 Davybase 的协同边界。更新于 2026-09。

## 共享 Vault 格局

DavyLinks 和 Davybase 共用同一个 Obsidian vault（`/Users/qiming/ObsidianWiki`）：

| 项目 | 写入区域 | 内容性质 |
|------|----------|----------|
| DavyLinks | `知识助理/每日精华/` | 外部公开资讯的每日/每周聚合 |
| Davybase | 其余wiki区域 | 私有笔记管理 |

边界清晰：DavyLinks 只写 `知识助理/` 子树，不碰用户笔记。

## DavyLinks 的沉淀策略

### 仅 TOP 5 入库

每天扫描 50+ 篇，只有最终 TOP 5 写入 Obsidian。理由：

- 避免知识库膨胀（全量入库一年 = 18000 篇，检索价值趋零）
- 完整记录已由飞书多维表格承担，Obsidian 只留精华
- 详见 [ADR-005](../decisions/005-top5-only-obsidian.md)

### 文件组织

```
ObsidianWiki/
└── 知识助理/
    ├── 每日精华/
    │   └── 2026-09-12.md      # 每日一份
    └── 周报/
        └── 2026-W37.md        # 每周一汇总上周
```

### Frontmatter 规范

```yaml
---
type: daily-digest
date: 2026-09-12
sources_count: 42
articles_count: 8
auto_generated: true
tags: [davylinks, daily-digest]
---
```

`auto_generated: true` 标记机器生成内容，与手写笔记区分。`type: daily-digest` 便于 Dataview 类插件检索。

## Vault 路径解析优先级

1. 环境变量 `OBSIDIAN_VAULT_PATH`
2. `config/secrets.yaml` 的 `obsidian.vault_path`
3. 代码默认值（硬编码路径，仅兜底）

配置加载由 `config_loader.get_obsidian_config()` 统一处理。

## 设计取向

- **Append-only**：DavyLinks 只新增每日文件，从不修改历史文件，避免与用户手工整理冲突
- **周报是聚合视图**：每周一生成，汇总上周每日精华，方便周度回顾
- 潜在改进：按话题打 tag 建立双链，让每日精华与 Davybase 私有笔记互联（未实施）
