# 快速上手

> 从零开始运行 DavyLinks 管线：安装依赖、执行管线、查看状态、本地校验。

## 安装

### 1. 环境要求

- Python 3.9+
- venv / pip 包管理器

### 2. 安装依赖

```bash
cd /path/to/DavyLinks
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

安装完成后，需先配置密钥才能运行管线，详见 [configuration.md](configuration.md)。

## 运行

### 基本用法

```bash
# 执行完整流程
.venv/bin/python scripts/pipeline.py

# 预览模式（不推送、不保存）
.venv/bin/python scripts/pipeline.py --dry-run

# 跳过飞书推送
.venv/bin/python scripts/pipeline.py --skip-push

# 跳过 Obsidian 保存
.venv/bin/python scripts/pipeline.py --skip-save

# 仅清理 90 天前旧数据
.venv/bin/python scripts/pipeline.py --cleanup
```

### 所有命令行选项

| 选项 | 说明 |
|------|------|
| `--dry-run` | 预览模式：不推送飞书、不保存 Obsidian |
| `--skip-push` | 跳过飞书消息推送 |
| `--skip-save` | 跳过 Obsidian 保存 |
| `--cleanup` | 仅清理 90 天前的旧数据 |

### 独立运行各阶段（调试用）

```bash
# Phase 1-2: 扫描 + 聚类
.venv/bin/python scripts/scan_articles.py > articles.json

# Phase 3: 摘要
cat articles.json | .venv/bin/python scripts/summarize.py > summarized.json

# Phase 3.5: 飞书多维表格
cat summarized.json | .venv/bin/python scripts/feishu_bitable.py

# Phase 4: 飞书消息推送
cat summarized.json | .venv/bin/python scripts/push_feishu.py

# Phase 5: Obsidian 保存
cat summarized.json | .venv/bin/python scripts/save_obsidian.py
```

**注意**: blogwatcher 的正确命令是 `blogwatcher-cli articles`（不是 `blogwatcher scan`）。

## 查看状态

```bash
# 查看运行统计
.venv/bin/python scripts/state_db.py

# 查看日志
LOG_LEVEL=DEBUG .venv/bin/python scripts/pipeline.py
```

## 本地校验

```bash
sh scripts/check.sh
```

该脚本会执行编译检查并运行全部测试，改动代码后建议先跑一次。

## 下一步

- 配置密钥和信息源 → [configuration.md](configuration.md)
- 配置飞书凭证 → [feishu-setup.md](feishu-setup.md)
- 配置 Obsidian 输出 → [obsidian-setup.md](obsidian-setup.md)
