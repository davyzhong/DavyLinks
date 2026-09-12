# Obsidian 配置指南

> 配置 Obsidian 输出路径，了解沉淀文件的结构与 frontmatter 格式。

## Obsidian 配置

在 `config/secrets.yaml` 中设置 Obsidian 仓库路径：

```yaml
obsidian:
  vault_path: "/Users/qiming/ObsidianWiki"
```

也可以通过环境变量覆盖：

```bash
export OBSIDIAN_VAULT_PATH=/path/to/vault
```

## Obsidian 输出说明

管线 Phase 5（`scripts/save_obsidian.py`）会将摘要结果写入 `vault_path` 指定的 Obsidian 仓库中。

### 输出路径

文章按日期组织，保存在仓库的对应目录下，便于按天回顾当天聚合的科技资讯。

### Frontmatter

每篇输出的 Markdown 文件包含 YAML frontmatter，记录来源、日期、热度评分等元数据，便于在 Obsidian 中通过 Dataview 等插件检索和筛选。

## 周报功能

基于已沉淀的每日文章，可以在 Obsidian 侧定期汇总生成周报，回顾一周内的高热度话题。

## 跳过 Obsidian 保存

如果只想推送到飞书、不写入 Obsidian，可以跳过该阶段：

```bash
.venv/bin/python scripts/pipeline.py --skip-save
```

## 相关配置

- 密钥与环境变量的完整说明 → [configuration.md](configuration.md)
- 保存阶段的独立运行调试 → [quickstart.md](quickstart.md)
