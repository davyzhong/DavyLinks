# DavyLinks 知识助理

> 自动化科技资讯聚合系统 — 从多个信息源抓取、AI 摘要、排序，推送每日精华到飞书并沉淀到 Obsidian。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置密钥
cp config/secrets.example.yaml ~/.davylinks/secrets.yaml
# 编辑填入飞书、LLM 等凭证

# 3. 运行管线
python scripts/pipeline.py
```

## 系统架构

```
信息源 (RSS/网站)
    │
    ▼
Phase 1: 扫描抓取 (scan_articles.py)
    │
    ▼
Phase 2: 去重过滤 (SQLite state.db)
    │
    ▼
Phase 3: AI 摘要 + 排序 (summarize.py)
    │
    ▼
Phase 4: 推送飞书 (feishu_bitable.py)
    │
    ▼
Phase 5: 沉淀 Obsidian (save_obsidian.py)
```

## 核心特性

- **多源聚合**: 支持 8+ 个科技资讯源（36 氪、机器之心、Hacker News 等）
- **智能去重**: SQLite 状态库记录已处理文章，支持断点续传
- **话题聚类**: O(n) 倒排索引算法，自动合并同一话题的多源报道
- **AI 摘要**: 多 LLM 并行处理（Qwen/Kimi/Zhipu/MiniMax），失败自动 fallback
- **交叉验证**: 多源报道同一话题 → 评分加成 → 排名靠前
- **日志系统**: 统一 logging 模块，支持分级日志和文件输出

## 项目结构

```
DavyLinks/
├── README.md                   # 本文件
├── ARCHITECTURE.md             # 架构设计文档
├── USAGE.md                    # 详细使用指南
├── OPTIMIZATION_COMPLETE.md    # 优化完成报告
├── requirements.txt            # Python 依赖
├── .gitignore                  # Git 忽略规则
├── config/
│   ├── sources.json            # 信息源 + 关键词配置
│   └── secrets.example.yaml    # 配置模板
├── scripts/
│   ├── logging_config.py       # 统一日志配置
│   ├── state_db.py             # SQLite 状态管理
│   ├── scan_articles.py        # Phase 1-2: 扫描 + 聚类
│   ├── summarize.py            # Phase 3: LLM 摘要
│   ├── feishu_bitable.py       # Phase 4: 飞书推送
│   ├── save_obsidian.py        # Phase 5: Obsidian 沉淀
│   └── pipeline.py             # 主流程编排
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

### 密钥配置 (`~/.davylinks/secrets.yaml`)

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
```

## 运行模式

```bash
# 完整执行
python scripts/pipeline.py

# 预览模式（不推送、不保存）
python scripts/pipeline.py --dry-run

# 跳过推送
python scripts/pipeline.py --skip-push

# 仅清理旧数据
python scripts/pipeline.py --cleanup
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

- **processed_articles**: 已处理文章（90 天自动清理）
- **run_log**: 每日运行统计（扫描数、过滤数、推送数）

```bash
# 查看统计
python scripts/state_db.py
```

## 相关项目

- **Davybase**: 私有笔记管理 → 共享 Obsidian vault 和飞书通知
- **blogwatcher-cli**: RSS 抓取工具
- **Hermes Agent**: 定时任务框架

## License

MIT
