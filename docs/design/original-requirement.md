# DavyLinks 知识助理系统设计方案（历史文档）

> **注意**: 这是项目的原始设计文档（存档于 `docs/design/`），记录了系统初始设计思路。当前实现已有较大演进，请参考：
> - `README.md` - 项目概览和快速开始
> - `ARCHITECTURE.md` - 当前架构设计
> - `USAGE.md` - 使用指南
> - `CLAUDE.md` - Claude Code 快速参考
> - `CHANGELOG.md` - 版本变更记录
>
> **文档目录约定**：
> - `docs/` - 项目文档（design 设计文档、architecture 架构、api 接口、guides 指南）
> - `knowledge/` - 项目知识沉淀（evolution 演进记录、decisions 决策、domain 领域、reference 参考）
> - 版本演进详情见 `knowledge/evolution/v1.0-mvp.md` 与 `knowledge/evolution/v2.0-code-review.md`

---

## 原始设计（2026-05-04）

> 基于 Hermes Agent 框架实现，复用 Davybase 管线经验与基础设施。

## 1. 项目概述

### 1.1 目标

构建一个自动化知识助理系统，从多个公开信息源（RSS/网站/播客）定时抓取最新内容，经过 AI 筛选、摘要、排序后，将每日精华推送到飞书，并沉淀到 Obsidian 知识库。

### 1.2 与 Davybase 的关系

| 维度 | Davybase | DavyLinks |
|------|----------|-----------|
| 数据源 | get 笔记 API（私有） | 公开 RSS/网站（开放） |
| 管线结构 | Ingest → Digest → Compile | Scan → Filter → Summarize → Push |
| 运行框架 | Python CLI (click) | Hermes Agent (cronjob + skills) |
| 知识库 | 同一 Obsidian vault | 同一 Obsidian vault |
| 通知 | 复用 Davybase notify.py | 复用 Davybase notify.py |

两者互补：Davybase 管理私有笔记，DavyLinks 聚合外部公开信息。

### 1.3 系统架构总览

```
信息源(RSS/网站/播客)
    │
    ▼
┌─────────────────────────────────────────────────┐
│  Hermes Cronjob (每天 8:00)                      │
│                                                  │
│  Phase 1: 扫描抓取 (blogwatcher + web search)    │
│     │                                            │
│     ▼                                            │
│  Phase 2: 去重过滤 (SQLite 状态库)               │
│     │                                            │
│     ▼                                            │
│  Phase 3: AI 摘要 + 排序 (LLM via delegate_task) │
│     │                                            │
│     ▼                                            │
│  Phase 4: 推送飞书 (Davybase notify.py)          │
│     │                                            │
│     ▼                                            │
│  Phase 5: 沉淀 Obsidian (obsidian skill)         │
└─────────────────────────────────────────────────┘
```

## 2. 详细设计

### 2.1 信息源配置

**支持的信息源类型与接入方式：**

| 信息源 | 接入方式 | 说明 |
|--------|----------|------|
| 微信公众号 | RSSHub (`rsshub.app/wechat/...`) | 需要部署或使用公共 RSSHub 实例 |
| 科技博客/网站 | 原生 RSS/Atom feed | blogwatcher 自动发现 feed |
| 外媒网站 | RSS 或 blogwatcher HTML 抓取 | 无 RSS 时用 CSS 选择器回退 |
| B站UP主 | RSSHub (`rsshub.app/bilibili/user/video/...`) | 视频标题+描述 |
| 小宇宙播客 | 原生 RSS feed | 播客自带 RSS |
| 小红书 | 暂不支持 | 反爬严格，后续评估接入 |
| Twitter/X | xitter/xurl skill | 关键词搜索或列表监控 |

**信息源配置文件** (`config/sources.json`)：

```json
{
  "sources": [
    {
      "name": "少数派",
      "type": "rss",
      "url": "https://sspai.com/feed",
      "category": "效率工具",
      "weight": 3,
      "keywords": ["效率", "工具", "生产力", "自动化"]
    },
    {
      "name": "AI科技评论-微信公众号",
      "type": "rsshub",
      "url": "https://rsshub.app/wechat/mp/:id",
      "category": "AI",
      "weight": 4,
      "keywords": ["AI", "大模型", "GPT", "Claude"]
    },
    {
      "name": "Hacker News",
      "type": "rss",
      "url": "https://hnrss.org/frontpage",
      "category": "技术",
      "weight": 2,
      "keywords": ["AI", "LLM", "open source", "programming"]
    }
  ],
  "global_keywords": [
    "AI", "人工智能", "大模型", "LLM", "AGI",
    "效率", "工具", "生产力",
    "创业", "产品", "设计",
    "编程", "开源"
  ]
}
```

**字段说明：**

- `weight` (1-5): 来源权重，影响排序分数。5=核心必读，1=低优先级
- `category`: 用于知识库分类和推送分组
- `keywords`: 该信息源的专属关键词，与 global_keywords 取并集过滤

### 2.2 状态管理

**为什么需要状态管理？** 原设计遗漏了去重和断点续传，这是实际运行中最大的问题。

**方案：SQLite 状态库** (`~/.davylinks/state.db`)

```sql
-- 已处理文章记录（去重）
CREATE TABLE IF NOT EXISTS processed_articles (
    url         TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    source      TEXT NOT NULL,
    category    TEXT DEFAULT '',
    published_at DATETIME,
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    relevance_score REAL DEFAULT 0,
    summary     TEXT DEFAULT '',
    pushed      INTEGER DEFAULT 0
);

-- 每日运行日志
CREATE TABLE IF NOT EXISTS run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    DATE NOT NULL UNIQUE,
    scanned     INTEGER DEFAULT 0,
    filtered    INTEGER DEFAULT 0,
    summarized  INTEGER DEFAULT 0,
    pushed      INTEGER DEFAULT 0,
    errors      INTEGER DEFAULT 0,
    duration_s  REAL DEFAULT 0,
    status      TEXT DEFAULT 'success'
);
```

**去重逻辑：**
- 每篇文章以 URL 为主键
- 扫描阶段先查 processed_articles，跳过已有记录
- 保留最近 90 天记录，超期自动清理（避免库膨胀）

### 2.3 五阶段工作流

#### Phase 1: 扫描抓取

**工具：** blogwatcher skill + terminal (curl/xq)

```
1. blogwatcher-cli articles → 获取所有订阅源的新文章列表
2. 对每篇新文章，用 terminal + curl 抓取全文
3. HTML → Markdown 转换（使用 readability + pandoc 或 xq）
4. 输出：[{title, url, source, category, content_md, published_at}, ...]
```

**并发控制：**
- blogwatcher 内置 8 workers 并发扫描
- 全文抓取阶段用 Hermes delegate_task 并行处理（最多 3 并发子任务）

**降级策略：**
- 全文抓取超时(15s) → 仅使用 RSS feed 中的摘要文本
- feed 不可达 → 记录错误，跳过该源，不阻塞其他源

#### Phase 2: 去重过滤

```
1. 查 SQLite state.db，排除已处理过的 URL
2. 关键词匹配过滤（源级 keywords ∪ global_keywords）
3. 排除：广告、纯转载、内容过短(<100字)的文章
4. 输出：过滤后的文章列表 + 相关性初评分
```

**相关性初评分算法：**

```
score = source_weight × 2
      + title_keyword_matches × 3
      + content_keyword_matches × 1
      + recency_bonus (24h内 +5, 48h内 +3, 72h内 +1)
```

取 score >= 3 的文章进入下一阶段（阈值可配置）。

#### Phase 3: AI 摘要 + 排序

**工具：** Hermes delegate_task + LLM

对过滤后的文章（预计每天 10-30 篇），使用 LLM 生成摘要：

```
Prompt 结构：
---
你是一个科技资讯编辑。请对以下文章生成一段 100 字以内的中文摘要，
提炼核心要点，适合快速阅读。

标题: {title}
来源: {source}
内容: {content_md (截取前 2000 字)}
---

输出 JSON: {"summary": "...", "key_points": ["...", "..."], "tags": ["..."]}
```

**并行处理：** 使用 delegate_task 的 batch 模式，每批最多 3 篇并行摘要。

**最终排序：**
```
final_score = initial_relevance_score
            + llm_quality_rating (1-5，由摘要模型顺便评估)
            × source_weight
```

取 TOP 5 进入推送，其余进入"值得关注"列表。

#### Phase 4: 推送飞书

**工具：** 复用 Davybase 的 `scripts/notify.py` 的 `send_feishu()` 函数

通过 `terminal` 调用 Python 脚本发送飞书 Interactive Card：

```
python /Users/qiming/workspace/davybase/scripts/notify.py \
  --title "每日科技资讯精华 [日期]" \
  --body "$(cat /tmp/davylinks/daily-digest.md)"
```

**推送内容模板：**

```
# 每日科技资讯精华 2026-04-25

## 今日 TOP 5

### 1. {标题}
> {AI 摘要，100字以内}
来源: {source} | 分类: {category} | [原文]({url})
标签: {tag1}, {tag2}

### 2. ...
（共5条）

## 值得关注

- **{标题}** — {一句话描述} | {source} | [链接]({url})
（共5-10条）

---
由 DavyLinks 知识助理自动生成 | 共扫描 {N} 篇，筛选 {M} 篇
```

**飞书 Card 格式适配：**
- Header: 绿色主题 + 日期
- TOP 5: 每条一个 markdown 区块
- 值得关注: 简洁列表
- Footer: 统计信息

#### Phase 5: 沉淀 Obsidian

**工具：** obsidian skill (文件系统操作)

仅将 TOP 5 文章写入 Obsidian，避免知识库膨胀：

```
路径: ObsidianWiki/知识助理/每日精华/YYYY-MM-DD.md
格式: 标准 Obsidian markdown + frontmatter
```

**Frontmatter 规范：**

```yaml
---
type: daily-digest
date: 2026-04-25
sources_count: 42
articles_count: 8
auto_generated: true
tags: [davylinks, daily-digest, AI, 效率]
---
```

**每周聚合：** 每周一额外生成 `YYYY-Wxx.md` 周报，汇总上周 TOP 内容。

### 2.4 定时任务配置

**使用 Hermes cronjob 实现：**

```
名称: davylinks-daily
计划: 0 8 * * *    （每天早上 8:00）
```

Cronjob prompt 大纲：

```
你是 DavyLinks 知识助理。请执行每日信息聚合任务：

1. 运行 Python 脚本 scan_articles.py 扫描所有信息源
2. 对新文章进行去重（查 SQLite state.db）
3. 用关键词过滤出相关文章
4. 对筛选后的文章用 LLM 生成摘要（delegate_task 并行）
5. 按相关性评分排序，取 TOP 5
6. 调用 Davybase notify.py 推送飞书
7. 将 TOP 5 写入 Obsidian 知识助理目录

信息源配置: config/sources.json
状态库: ~/.davylinks/state.db
Obsidian vault: /Users/qiming/ObsidianWiki
```

### 2.5 项目结构

```
DavyLinks/
├── requirement.md              # 本设计文档
├── config/
│   └── sources.json            # 信息源 + 关键词配置
├── scripts/
│   ├── scan_articles.py        # Phase 1-2: 扫描 + 去重过滤
│   ├── summarize.py            # Phase 3: LLM 摘要 + 排序
│   ├── feishu_bitable.py       # Phase 4: 推送飞书多维表格
│   ├── save_obsidian.py        # Phase 5: 沉淀到 Obsidian
│   ├── state_db.py             # SQLite 状态管理（共用模块）
│   ├── logging_config.py       # 统一日志配置
│   └── pipeline.py             # 主流程编排
└── skills/
    └── davylinks-pipeline.md   # Hermes skill（管线编排）
```

## 3. 与原设计相比的改进点

| 原设计 | 问题 | 改进方案 |
|--------|------|----------|
| 依赖 OpenClaw npm 生态 | OpenClaw 插件不稳定，生态小 | 改用 Hermes + Python，依赖成熟的 blogwatcher、pandoc |
| 无去重机制 | 每天重复推送相同文章 | SQLite state.db 记录已处理文章，URL 主键去重 |
| 无错误处理 | 一个源失败会阻塞全部 | 每个源独立处理，失败跳过+记录，不阻塞 |
| 关键词过滤太简单 | `includes()` 匹配太粗糙 | 加权评分：标题权重 > 内容权重 + 时效性加分 |
| 推送格式未适配飞书 | 飞书 Card 需要特定 JSON 格式 | 复用 Davybase notify.py，已验证的飞书 Card 实现 |
| 无状态追踪 | 不知道每天跑了什么 | run_log 表记录每次运行的统计信息 |
| 小红书列入支持 | 反爬严格，实际不可行 | 标注"暂不支持"，优先接入有 RSS 的源 |
| 单文件实现 | daily-digest.js 300 行全塞一起 | 按阶段拆分脚本，各司其职 |
| 无并发控制 | 大量请求可能被限流 | delegate_task 限制 3 并发 + 源间请求间隔 |
| 无知识库容量控制 | 所有文章都写入 Obsidian | 仅 TOP 5 写入 + 90 天自动清理 |
| 无增量概念 | 每次全量抓取 | blogwatcher 本身追踪已读状态 + SQLite 去重 |

## 4. 实现优先级

### Phase A: MVP（先跑通）

1. 安装 blogwatcher-cli
2. 创建 `config/sources.json`（先配 3-5 个有 RSS 的源）
3. 实现 `scripts/scan_articles.py`（扫描 + 去重）
4. 实现 `scripts/summarize.py`（LLM 摘要，先用 Hermes 内置 LLM）
5. 实现 `scripts/push_feishu.py`（调用 Davybase notify.py）
6. 创建 Hermes cronjob，每天 8:00 触发

### Phase B: 完善

7. 实现 `scripts/save_obsidian.py`（Obsidian 沉淀）
8. 添加 `scripts/weekly_digest.py`（周报）
9. 扩充信息源（RSSHub 接入微信、B站）
10. 前端看板（统计扫描/推送数据）

### Phase C: 进阶

11. 用户反馈闭环（飞书消息加"有用/没用"按钮，调整权重）
12. 个性化推荐（基于历史阅读行为调整关键词权重）
13. 多语言支持（中英文内容统一处理）
14. Twitter/X 接入（xitter skill）

## 5. 环境准备清单

| 项目 | 状态 | 操作 |
|------|------|------|
| Hermes Agent | 已就绪 | — |
| blogwatcher-cli | 未安装 | `brew install blogwatcher-cli` 或从 GitHub release 下载 |
| 飞书 Webhook | 需确认 | 检查 Davybase secrets.yaml 中的 webhook 配置 |
| Obsidian vault | 已就绪 | `/Users/qiming/ObsidianWiki` |
| Python 3 | 已就绪 | 系统 Python 3.x |
| pandoc (可选) | 未确认 | HTML→Markdown 转换用，`brew install pandoc` |
| Davybase notify.py | 已就绪 | `/Users/qiming/workspace/davybase/scripts/notify.py` |
| LLM API | 已就绪 | 全局配置 `~/.config/llm-providers.yaml` |

## 6. 风险与应对

| 风险 | 影响 | 应对 |
|------|------|------|
| RSSHub 公共实例限流/下线 | 微信/B站源不可用 | 自建 RSSHub 实例（Docker 一键部署） |
| 全文抓取被反爬 | 只拿到标题和 RSS 摘要 | 降级使用 RSS feed 自带摘要，不阻塞流程 |
| LLM API 限流 | 摘要生成慢或失败 | 分批处理 + 重试 + 降级为关键词提取 |
| 信息源变更 RSS 格式 | 解析失败 | blogwatcher 自动发现 + 手动 fallback URL |
| 飞书 Webhook 失效 | 推送不到 | run_log 记录失败状态，下次运行时补发 |
| 文章量太大（>100篇/天） | 处理时间过长 | Phase 2 阈值收紧 + 每源每日上限 20 篇 |
