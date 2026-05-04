# DavyLinks Pipeline Skill

> 自动化科技资讯聚合 — 扫描、摘要、推送每日精华

## 重要提示

**本技能需要在本地终端执行**，无法在 VM 沙箱中运行：

- `blogwatcher-cli` 需要预先安装
- RSS 抓取需要访问外部网络（沙箱受限）

当用户触发时，技能应返回提示让用户在本机执行：

```bash
cd /Users/qiming/workspace/DavyLinks

# 预览模式（不推送）
python3 scripts/pipeline.py --dry-run

# 完整执行
python3 scripts/pipeline.py
```

## 能力说明

本 skill 用于执行 DavyLinks 知识助理的完整管线，包括：

1. **扫描抓取**: 从 8+ 个 RSS 源获取最新科技资讯
2. **去重聚类**: 使用倒排索引合并同一话题的多源报道
3. **AI 摘要**: 多 LLM 并行生成摘要（Qwen/Kimi/Zhipu/MiniMax）
4. **飞书推送**: 将 TOP 5 文章推送到飞书多维表格
5. **Obsidian 沉淀**: 生成每日精华笔记

## 执行流程

```bash
cd /Users/qiming/workspace/DavyLinks

# 方式一：完整管线（推荐）
python scripts/pipeline.py

# 方式二：分阶段执行（调试用）
python scripts/scan_articles.py | python scripts/summarize.py | python scripts/feishu_bitable.py
```

## 配置检查清单

执行前确认以下配置已就绪：

- [ ] `~/.davylinks/secrets.yaml` 包含飞书凭证
- [ ] `config/sources.json` 配置了至少 3 个信息源
- [ ] LLM Provider 配置在 `~/.config/llm-providers.yaml`
- [ ] Obsidian vault 路径存在

## 输出产物

| 产物 | 位置 | 说明 |
|------|------|------|
| 飞书表格 | 配置的 Bitable | 每日文章记录 |
| Obsidian 笔记 | `知识助理/每日精华/` | Markdown 格式 |
| 运行日志 | stderr / `~/.davylinks/` | 调试信息 |
| 状态数据库 | `~/.davylinks/state.db` | 去重记录 |

## 故障排查命令

```bash
# 测试飞书连接
python scripts/feishu_bitable.py --test

# 查看运行统计
python scripts/state_db.py

# 调试模式运行
LOG_LEVEL=DEBUG python scripts/pipeline.py

# 仅扫描不推送（测试用）
python scripts/pipeline.py --dry-run
```

## 性能基准

| 阶段 | 耗时 (典型值) |
|------|---------------|
| 扫描 | 5-10 秒 |
| 聚类 | < 1 秒 |
| 摘要 (5 篇) | 30-60 秒 |
| 推送 | 2-5 秒 |
| 保存 | < 1 秒 |
| **总计** | **~60 秒** |

## 相关技能

- `obsidian` - 文件写入操作
- `terminal` - 执行命令
- `notify` - 飞书通知（复用 Davybase）

## 版本历史

- **v1.0** (2026-05-04): 初始版本
  - 倒排索引聚类 O(n)
  - 多 LLM 并行摘要
  - 统一日志系统
