# DavyLinks Pipeline Skill

> 自动化科技资讯聚合 — 扫描、聚类、摘要、推送每日精华

## 重要提示

**本技能需要在本地终端执行**，无法在 VM 沙箱中运行：

- `blogwatcher-cli` 需要预先安装
- RSS 抓取需要访问外部网络（沙箱受限）

当用户触发时，技能应返回提示让用户在本机执行：

```bash
cd /Users/qiming/workspace/DavyLinks

# 本地校验（编译 + 测试）
sh scripts/check.sh

# 预览模式（不推送）
python3 scripts/pipeline.py --dry-run

# 完整执行
python3 scripts/pipeline.py

# 运行测试
python3 -m pytest tests/ -v
```

## 能力说明

本 skill 用于执行 DavyLinks 知识助理的完整管线，包括：

1. **扫描抓取**: 从 6+ 个 RSS 源获取最新科技资讯（36氪、少数派、量子位、IT之家、Hacker News + 微信公众号 via wewe-rss）
2. **去重聚类**: 使用倒排索引（实体索引 + 中文二元组索引）合并同一话题的多源报道
3. **AI 摘要**: 多 LLM 并行生成摘要（Qwen/Kimi/Zhipu/MiniMax），失败自动 fallback
4. **飞书表格**: 将文章写入飞书多维表格（Bitable）
5. **飞书推送**: 生成每日精华内容并发送到飞书群消息
6. **Obsidian 沉淀**: 生成每日精华笔记

## 执行流程

```bash
cd /Users/qiming/workspace/DavyLinks

# 方式一：完整管线（推荐）
python scripts/pipeline.py

# 方式二：分阶段执行（调试用）
# Phase 1-2: 扫描 + 去重 + 聚类
python scripts/scan_articles.py > articles.json

# Phase 3: LLM 摘要 + 排序
cat articles.json | python scripts/summarize.py > summarized.json

# Phase 3.5: 飞书多维表格写入
cat summarized.json | python scripts/feishu_bitable.py

# Phase 4: 飞书消息推送
cat summarized.json | python scripts/push_feishu.py

# Phase 5: Obsidian 沉淀
cat summarized.json | python scripts/save_obsidian.py
```

**注意**: RSS 扫描使用 `blogwatcher-cli articles` 命令（不是 `blogwatcher scan`）。

## 配置检查清单

执行前确认以下配置已就绪：

- [ ] `config/secrets.yaml`（或 `~/.davylinks/secrets.yaml`）包含飞书凭证
- [ ] `config/sources.json` 配置了至少 3 个信息源
- [ ] LLM Provider 配置在 `config/secrets.yaml` 的 `llm_providers` 部分（或 `~/.config/llm-providers.yaml` 作为兼容 fallback）
- [ ] Obsidian vault 路径存在

所有配置通过 `scripts/config_loader.py` 统一加载，支持：
- 环境变量（最高优先级）
- `config/secrets.yaml`（推荐）
- `~/.davylinks/secrets.yaml`（备用）

## 输出产物

| 产物 | 位置 | 说明 |
|------|------|------|
| 飞书多维表格 | 配置的 Bitable | 每日文章记录（批量写入） |
| 飞书群消息 | 配置的 Webhook | 每日精华推送（Markdown 格式） |
| Obsidian 笔记 | `知识助理/每日精华/` | Markdown 格式（Frontmatter + TOP 5） |
| 运行日志 | stderr / `~/.davylinks/` | 调试信息 |
| 状态数据库 | `~/.davylinks/state.db` | 去重记录（90 天自动清理） |

## 测试与校验

项目包含 19 个测试用例，覆盖配置加载、管线编排、聚类算法、数据库操作、不可变性保证：

```bash
# 本地校验（编译 + 测试）
sh scripts/check.sh

# 运行全部测试
python -m pytest tests/ -v

# 运行特定模块
python -m pytest tests/test_immutability.py -v

# 带覆盖率
python -m pytest tests/ --cov=scripts --cov-report=term-missing
```

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
| 飞书表格 | 2-5 秒 |
| 飞书推送 | 2-5 秒 |
| Obsidian 保存 | < 1 秒 |
| **总计** | **~60 秒** |

## 架构特点

- **六阶段管线**: Phase 1-2 (扫描+聚类) → Phase 3 (摘要) → Phase 3.5 (飞书表格) → Phase 4 (飞书推送) → Phase 5 (Obsidian)
- **不可变数据流**: 各阶段函数返回新 dict，不修改输入数据
- **延迟配置加载**: 各模块在首次调用时加载配置，不在 import 时读取 secrets
- **SQL 安全**: 参数化查询防止注入，executemany 批量插入
- **64 位 hash**: URL 去重使用 64 位 hash，碰撞概率极低
- **完整测试**: 19 个测试用例覆盖核心模块

## 相关技能

- `obsidian` - 文件写入操作
- `terminal` - 执行命令
- `notify` - 飞书通知（复用 Davybase）

## 版本历史

- **v2.0** (2026-06-05): 代码质量优化
  - 修复 SQL 注入漏洞（参数化查询）
  - 实现不可变数据流（返回新 dict）
  - 延迟配置加载（lazy init）
  - 修复时区计算错误（timezone.utc）
  - executemany 替代逐条 INSERT
  - hash_url 扩展到 64 bit
  - 添加 19 个测试用例
  - 统一配置加载到 `config_loader.py`
  - 更新全部项目文档

- **v1.0** (2026-05-04): 初始版本
  - 倒排索引聚类 O(n)
  - 多 LLM 并行摘要
  - 统一日志系统
  - SQLite 状态管理
  - 飞书多维表格写入
