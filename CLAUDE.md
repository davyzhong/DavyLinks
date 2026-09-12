# DavyLinks

**Python 3.9+** | 科技资讯聚合管线 | 飞书 + Obsidian 输出

> 本文件是 AI 助手的唯一指令来源。AGENTS.md 仅为其存根，指向本文件。

## 快速命令

```bash
# 安装依赖
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt

# 配置密钥 (首次运行)
cp config/secrets.example.yaml config/secrets.yaml
# 编辑 config/secrets.yaml 填入飞书凭证和 LLM API Key

# 运行完整管线
.venv/bin/python scripts/pipeline.py

# 预览模式 (不摘要、不推送、不保存)
.venv/bin/python scripts/pipeline.py --dry-run

# 跳过飞书推送 / 跳过 Obsidian 保存
.venv/bin/python scripts/pipeline.py --skip-push
.venv/bin/python scripts/pipeline.py --skip-save

# 清理 90 天前的旧记录
.venv/bin/python scripts/pipeline.py --cleanup

# 查看运行统计
.venv/bin/python scripts/state_db.py

# 运行测试
.venv/bin/python -m pytest tests/ -v

# 本地校验 (编译 + 测试)
sh scripts/check.sh
```

## 配置加载优先级

1. **环境变量** (最高) → `FEISHU_APP_ID`, `LOG_LEVEL` 等
2. **config/secrets.yaml** (推荐)
3. **~/.davylinks/secrets.yaml** (备用)

所有配置通过 `scripts/config_loader.py` 统一加载，各模块延迟读取（首次调用时初始化，不在 import 时读取 secrets）。

## 项目结构

```
DavyLinks/
├── CLAUDE.md                  # AI 助手指令 (本文件)
├── CHANGELOG.md               # 版本变更记录
├── docs/                      # 项目文档 (怎么用)
│   ├── architecture/          # 架构设计 (pipeline/clustering/summarization/data-flow)
│   ├── guides/                # 使用指南 (quickstart/configuration/setup/troubleshooting)
│   ├── api/                   # 接口文档 (CLI/配置格式/数据库Schema)
│   └── design/                # 设计文档 (当前设计 + 历史需求)
├── knowledge/                 # 知识库 (为什么这么做)
│   ├── domain/                # 领域知识 (RSS/LLM/飞书/Obsidian)
│   ├── decisions/             # 架构决策记录 ADR
│   ├── evolution/             # 项目演进记录
│   └── reference/             # 速查手册
├── scripts/
│   ├── config_loader.py       # 统一配置加载 (secrets.yaml + 环境变量)
│   ├── pipeline.py            # 主入口 (六阶段编排)
│   ├── scan_articles.py       # Phase 1-2: 扫描 + 聚类 (O(n) 倒排索引)
│   ├── summarize.py           # Phase 3: LLM 并行摘要 (4 路 fallback)
│   ├── feishu_bitable.py      # Phase 3.5: 飞书多维表格写入
│   ├── push_feishu.py         # Phase 4: 飞书消息推送
│   ├── save_obsidian.py       # Phase 5: Obsidian 沉淀
│   ├── state_db.py            # SQLite 状态管理
│   ├── logging_config.py      # 统一日志配置
│   └── check.sh               # 本地校验脚本
├── config/
│   ├── sources.json           # 信息源 + 关键词配置
│   └── secrets.yaml           # 密钥 (不提交 git)
├── tests/
│   ├── conftest.py            # pytest 配置
│   ├── test_config_loader.py  # 配置加载测试
│   ├── test_config_integration.py  # 模块集成测试
│   ├── test_pipeline.py       # 管线编排测试
│   ├── test_push_feishu.py    # 飞书推送测试
│   ├── test_scan_articles.py  # 聚类算法测试
│   ├── test_state_db.py       # 数据库测试
│   └── test_immutability.py   # 不可变性测试
└── skills/
    └── davylinks-pipeline.md  # Hermes skill
```

## 核心管线

```
RSS/Atom → 扫描去重 → 话题聚类 → AI 摘要 → 飞书表格 → 飞书推送 → Obsidian
           (Phase 1-2)  (Phase 1-2)  (Phase 3)  (Phase 3.5) (Phase 4)  (Phase 5)
```

## 关键注意事项

- **blogwatcher-cli 命令**: 用 `blogwatcher-cli articles` (不是 `blogwatcher scan`)
- **LLM API 格式**: Kimi/Zhipu 用 Anthropic 格式，Qwen/MiniMax 用 OpenAI 格式
- **聚类阈值**: `chinese_overlap >= 0.35`，调低可增加敏感度
- **相关性门槛**: `relevance_score >= 8` 才进入后续流程（来源权重×2 + 关键词命中）
- **分类来源**: 每个 RSS 源的 `category` 字段在 `config/sources.json` 中配置，由 `scan_articles.py` 自动注入
- **飞书权限**: 应用需添加为多维表格协作者 (编辑权限)
- **状态库位置**: `~/.davylinks/state.db` (90 天自动清理)
- **不可变数据流**: 各阶段函数返回新 dict，不修改输入数据
- **SQL 安全**: `cleanup_old` 使用参数化查询，`mark_processed` 使用 `executemany`
- **延迟配置加载**: `feishu_bitable.py`、`push_feishu.py`、`save_obsidian.py` 在首次调用时加载配置
- **Obsidian 周报**: `save_obsidian.py --weekly` 汇总本周每日精华生成周报

## 文档体系

| 文档 | 位置 | 何时看 |
|------|------|--------|
| 文档导航 | [docs/README.md](docs/README.md) | 找不到文档时 |
| 知识库导航 | [knowledge/README.md](knowledge/README.md) | 了解设计背景时 |
| **设计报告** | [docs/design/design-report.md](docs/design/design-report.md) | 全面理解项目时 |
| 当前设计 | [docs/design/current-design.md](docs/design/current-design.md) | 理解设计原则与参数 |
| 架构详解 | [docs/architecture/](docs/architecture/) | 改代码前 |
| 故障排查 | [docs/guides/troubleshooting.md](docs/guides/troubleshooting.md) | 出问题时 |
| 设计决策 | [knowledge/decisions/](knowledge/decisions/) | 理解"为什么"时 |

## 文档维护规范

- 改动管线行为 → 同步更新 `docs/architecture/pipeline.md` + `docs/design/current-design.md`
- 新增重要设计决策 → 在 `knowledge/decisions/` 新增 ADR（三位序号递增）
- 修改配置格式 → 同步更新 `docs/api/config-format.md`
- 版本级变更 → 记录到 `CHANGELOG.md`
- 根目录只保留：`README.md`、`CLAUDE.md`、`CHANGELOG.md`、`CONTRIBUTING.md`

## 故障排查

```bash
# 测试飞书连接
.venv/bin/python scripts/feishu_bitable.py --test

# 查看状态库统计
.venv/bin/python scripts/state_db.py

# 调试模式
LOG_LEVEL=DEBUG .venv/bin/python scripts/pipeline.py

# 分阶段执行 (调试用)
.venv/bin/python scripts/scan_articles.py > articles.json
cat articles.json | .venv/bin/python scripts/summarize.py > summarized.json
```

## 验证命令

```bash
.venv/bin/python -m pytest tests/ -v          # 运行全部测试
.venv/bin/python scripts/pipeline.py --help   # 查看命令行选项
.venv/bin/python -c "import yaml; print('OK')" # 验证 YAML 依赖
sh scripts/check.sh                           # 编译 + 测试
```
