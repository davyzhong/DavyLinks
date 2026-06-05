# DavyLinks 知识助理

> 自动化科技资讯聚合系统 — 从多个信息源抓取、AI 摘要、排序，推送每日精华到飞书并沉淀到 Obsidian。

## 快速开始

```bash
# 1. 安装依赖（Python 3.9+）
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# 2. 配置密钥
cp config/secrets.example.yaml config/secrets.yaml
# 或: cp config/secrets.example.yaml ~/.davylinks/secrets.yaml
# 编辑填入飞书、LLM 等凭证

# 3. 运行管线
.venv/bin/python scripts/pipeline.py

# 4. 运行测试
.venv/bin/python -m pytest tests/ -v
```

## 系统架构

```
信息源 (RSS/网站)
    │
    ▼
Phase 1-2: 扫描 + 聚类 (scan_articles.py)
    │
    ▼
Phase 3: AI 摘要 + 排序 (summarize.py)
    │
    ▼
Phase 3.5: 飞书多维表格 (feishu_bitable.py)
    │
    ▼
Phase 4: 飞书消息推送 (push_feishu.py)
    │
    ▼
Phase 5: 沉淀 Obsidian (save_obsidian.py)
```

## 核心特性

- **多源聚合**: 支持 6+ 个科技资讯源（36氪、少数派、量子位、IT之家、Hacker News + 微信公众号 via wewe-rss）
- **智能去重**: SQLite 状态库记录已处理文章，支持断点续传
- **话题聚类**: O(n) 倒排索引算法（实体索引 + 中文二元组索引），自动合并同一话题的多源报道
- **AI 摘要**: 多 LLM 并行处理（Qwen/Kimi/Zhipu/MiniMax），失败自动 fallback
- **交叉验证**: 多源报道同一话题 → 评分加成 → 排名靠前
- **不可变数据流**: 各阶段函数返回新对象，不修改输入数据，便于调试和测试
- **安全**: SQL 参数化查询防止注入，配置延迟加载避免 import 时泄露
- **统一配置**: `config_loader.py` 集中管理所有配置，支持环境变量 > config/secrets.yaml > ~/.davylinks/secrets.yaml
- **完整测试**: 19 个测试用例覆盖配置加载、管线编排、聚类算法、不可变性保证

## 项目结构

```
DavyLinks/
├── README.md                   # 本文件
├── CLAUDE.md                   # Claude Code 快速参考
├── ARCHITECTURE.md             # 架构设计文档
├── USAGE.md                    # 详细使用指南
├── OPTIMIZATION_COMPLETE.md    # 优化历史报告
├── requirement.md              # 原始设计文档 (历史参考)
├── requirements.txt            # Python 依赖
├── .gitignore                  # Git 忽略规则
├── config/
│   ├── sources.json            # 信息源 + 关键词配置
│   └── secrets.example.yaml    # 配置模板
├── scripts/
│   ├── config_loader.py        # 统一配置加载模块
│   ├── logging_config.py       # 统一日志配置
│   ├── state_db.py             # SQLite 状态管理
│   ├── scan_articles.py        # Phase 1-2: 扫描 + 聚类
│   ├── summarize.py            # Phase 3: LLM 摘要
│   ├── feishu_bitable.py       # Phase 3.5: 飞书表格写入
│   ├── push_feishu.py          # Phase 4: 飞书消息推送
│   ├── save_obsidian.py        # Phase 5: Obsidian 沉淀
│   ├── pipeline.py             # 主流程编排
│   └── check.sh                # 本地校验脚本
├── tests/
│   ├── conftest.py             # pytest 配置
│   ├── test_config_loader.py   # 配置加载测试
│   ├── test_config_integration.py  # 模块集成测试
│   ├── test_pipeline.py        # 管线编排测试
│   ├── test_push_feishu.py     # 飞书推送测试
│   ├── test_scan_articles.py   # 聚类算法测试
│   ├── test_state_db.py        # 数据库测试
│   └── test_immutability.py    # 不可变性测试
└── skills/
    └── davylinks-pipeline.md   # Hermes skill 定义
```

## 配置说明

### 信息源配置 (`config/sources.json`)

```json
{
  "sources": [
    {
      "name": "36 氪",
      "url": "https://36kr.com/feed",
      "weight": 5,
      "keywords": ["AI", "大模型", "创业"]
    }
  ],
  "global_keywords": ["AI", "LLM", "开源"]
}
```

### 密钥配置 (`config/secrets.yaml` 或 `~/.davylinks/secrets.yaml`)

配置加载优先级：环境变量 > `config/secrets.yaml` > `~/.davylinks/secrets.yaml`。

所有配置通过 `scripts/config_loader.py` 统一加载，各模块延迟读取（首次调用时初始化）。

```yaml
feishu:
  app_id: "cli_xxx"
  app_secret: "xxx"
  webhook_url: "https://open.feishu.cn/..."
  bitable:
    app_token: "xxx"
    table_id: "tblxxx"

llm_providers:
  qwen:
    api_key: "sk-xxx"
    base_url: "https://dashscope.aliyuncs.com/..."

obsidian:
  vault_path: "/path/to/ObsidianWiki"

davybase:
  notify_path: ""    # 可选：/path/to/davybase/scripts/notify.py
  secrets_path: ""   # 可选：/path/to/davybase/secrets.yaml
```

## 运行模式

```bash
# 完整执行
.venv/bin/python scripts/pipeline.py

# 预览模式（不推送、不保存）
.venv/bin/python scripts/pipeline.py --dry-run

# 跳过推送
.venv/bin/python scripts/pipeline.py --skip-push

# 仅清理旧数据
.venv/bin/python scripts/pipeline.py --cleanup

# 本地校验（编译 + 测试）
sh scripts/check.sh
```

## 性能指标

| 指标 | 数值 |
|------|------|
| 扫描速度 | ~50 篇/秒 |
| 聚类耗时 (100 篇) | < 1ms |
| 摘要耗时 (5 篇) | ~30 秒 (并行) |
| 内存占用 | < 50MB |

## 状态追踪

SQLite 状态库 (`~/.davylinks/state.db`) 记录：

- **processed_articles**: 已处理文章（90 天自动清理，使用参数化查询防止 SQL 注入）
- **run_log**: 每日运行统计（扫描数、过滤数、推送数）

```bash
# 查看统计
.venv/bin/python scripts/state_db.py
```

## 测试

项目包含 19 个测试用例，覆盖：

- 配置加载优先级和覆盖逻辑
- 管线编排和错误计数
- 话题聚类算法正确性
- 数据库操作（批量插入、参数化查询）
- **不可变性保证**：验证 `filter_by_keywords`、`summarize_one`、`final_sort` 不修改输入数据

```bash
# 运行全部测试
.venv/bin/python -m pytest tests/ -v

# 运行特定模块测试
.venv/bin/python -m pytest tests/test_immutability.py -v
```

## 相关项目

- **Davybase**: 私有笔记管理 → 共享 Obsidian vault 和飞书通知
- **blogwatcher-cli**: RSS 抓取工具
- **Hermes Agent**: 定时任务框架

## License

MIT
