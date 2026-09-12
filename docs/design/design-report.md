# DavyLinks 项目设计报告

> 本报告是 DavyLinks 的权威设计文档，综合项目目标、业务背景、架构设计、关键决策与演进历程。
> 素材来源为项目静态知识库（`docs/` 与 `knowledge/`），细节均链接至对应文档。
> 版本: v2.0 | 日期: 2026-09-12

---

## 1. 项目概述

### 1.1 定位

DavyLinks 是一个**自动化科技资讯聚合管线**：每天从多个公开信息源定时抓取内容，经去重、话题聚类、AI 摘要与排序后，将每日精华推送到飞书（群消息 + 多维表格）并沉淀到 Obsidian 知识库。

一句话：**把每天几十上百条科技资讯，自动浓缩为 5 条最值得看的内容，并保留完整档案可回溯。**

### 1.2 与 Davybase 的关系

两者共享同一 Obsidian vault 和飞书通知基础设施，但职责互补：

| 维度 | Davybase | DavyLinks |
|------|----------|-----------|
| 数据源 | get 笔记 API（私有） | 公开 RSS/网站（开放） |
| 定位 | 私有笔记管理 | 外部信息聚合 |
| 写入区域 | wiki 主体区域 | 仅 `知识助理/` 子树 |

### 1.3 技术栈

- Python 3.9+（零重量级框架，标准库 + PyYAML）
- SQLite（状态管理，单文件零部署）
- blogwatcher-cli（RSS 扫描）+ wewe-rss（微信公众号 Atom feed）
- 飞书开放平台（多维表格 + 群消息）
- 4 家国产 LLM（Qwen / Kimi / Zhipu / MiniMax）

---

## 2. 业务背景与问题定义

### 2.1 要解决的问题

**信息过载 + 信息封闭的双重困境：**

1. **来源分散**：科技资讯散布在十几个平台（36氪、量子位、少数派、IT之家、Hacker News、微信公众号……），逐一浏览成本高
2. **中文 RSS 生态萎缩**：机器之心、虎嗅、InfoQ 中文等主流媒体的 RSS 已相继失效，微信公众号完全封闭——聚合的技术门槛逐年升高
3. **重复冗余**：同一热点事件被多个源反复报道，人工阅读大量重复
4. **转瞬即逝**：群消息里的资讯没有档案，"上周看过的那篇文章"找不回来

### 2.2 业务方案

对应四个痛点的业务设计：

| 痛点 | 方案 | 核心机制 |
|------|------|----------|
| 来源分散 | 多源统一扫描 | 配置驱动的 RSS 聚合（`sources.json`），加源不改代码 |
| RSS 萎缩 | 混合接入策略 | 原生 RSS 优先 + wewe-rss 补微信公众号 + 失效源保留配置待恢复 |
| 重复冗余 | 话题聚类 + 多源交叉验证 | 同话题合并，多源报道获得评分加成——**被多家报道本身就是重要性信号** |
| 转瞬即逝 | 三层出口分层 | 飞书表格存全量档案，群消息推 TOP 5 精华，Obsidian 沉淀长期知识 |

### 2.3 核心业务规则

**相关性评分**（决定哪些文章进入后续流程，阈值 `score >= 8`）：

```
score = source_weight × 2
      + title_matches × 3        # 标题命中关键词
      + content_matches × 1      # 正文命中关键词
      + recency_bonus            # 24h 内 +5，48h 内 +3，72h 内 +1
```

**最终排序**（决定 TOP 5）：

```
final_score = relevance_score + quality_rating × 2 + cross_bonus
其中 cross_bonus = min(来源数, 5) × 15    # 多源交叉验证加成
```

权重设计的业务含义：权重 5 的核心源（36氪、量子位）自带 10 分底分，天然过门槛；权重 3 的泛化源（IT之家、Hacker News）必须靠关键词命中把关。**调权重即调入口流量**。

详见 [knowledge/domain/tech-news-landscape.md](../../knowledge/domain/tech-news-landscape.md)。

---

## 3. 系统架构

### 3.1 总体数据流

```
┌─────────────────┐  ┌─────────────────┐
│  blogwatcher-cli │  │  wewe-rss Atom  │
│  (RSS sources)   │  │  (微信公众号)    │
└───────┬─────────┘  └───────┬─────────┘
        └──────────┬──────────┘
                   ▼
  Phase 1-2  扫描 + 去重 + 关键词过滤 + 话题聚类 (scan_articles.py)
                   ▼
  Phase 3    LLM 并行摘要 + 质量评分 + 最终排序 (summarize.py)
                   ▼
  Phase 3.5  飞书多维表格写入 — 全量档案 (feishu_bitable.py)
                   ▼
  Phase 4    飞书群消息推送 — TOP 5 精华 (push_feishu.py)
                   ▼
  Phase 5    Obsidian 沉淀 — TOP 5 + 周报 (save_obsidian.py)
```

各阶段职责与算法细节：[architecture/pipeline.md](../architecture/pipeline.md)

### 3.2 核心算法：话题聚类

聚类是本系统的算法核心，解决"同一事件多源报道"的合并问题：

- **倒排索引 + Union-Find**：预计算每篇文章的英文实体名（DeepSeek、LLaMA）和中文二元组，构建两个倒排索引，只比较有共享特征的文章对
- **泛化桶剪枝**：桶大小超过 `max_bucket_size=50` 的词无区分度，跳过
- **合并阈值**：中文二元组重叠度 `chinese_overlap >= 0.35`（调低可增加敏感度）
- **复杂度**：O(n) 建索引 + O(k²) 组内比较，比较次数减少 80-95%（100 篇文章从 4950 次比较降到约 127 次）

设计理由与权衡：[ADR-001](../../knowledge/decisions/001-inverted-index-clustering.md)；算法细节：[architecture/clustering.md](../architecture/clustering.md)

### 3.3 核心机制：多路 LLM 摘要

- 4 家供应商（Qwen / Kimi / Zhipu / MiniMax）Round-robin 分配 TOP 文章，ThreadPoolExecutor 并行
- 单篇失败自动 fallback 到下一家——任何一家限流/宕机不阻塞当天管线
- 并行耗时约 50s（串行需 250s）
- API 格式分裂：Kimi/Zhipu 用 Anthropic 格式，Qwen/MiniMax 用 OpenAI 格式，白名单 `ANTHROPIC_PROVIDERS` 适配

决策：[ADR-004](../../knowledge/decisions/004-multi-llm-fallback.md)、[ADR-008](../../knowledge/decisions/008-dual-llm-api-format.md)；细节：[architecture/summarization.md](../architecture/summarization.md)

### 3.4 输出分层

| 出口 | 内容 | 职能 |
|------|------|------|
| 飞书多维表格 | 每天 20-80 篇全量 | 完整档案，可筛选回溯（容量 10 万行） |
| 飞书群消息 | TOP 5 + 值得关注列表 | 日常阅读入口 |
| Obsidian | TOP 5 精华 + 每周周报 | 长期知识沉淀（仅增 365 文件/年） |

"仅 TOP 5 入 Obsidian"的决策逻辑：[ADR-005](../../knowledge/decisions/005-top5-only-obsidian.md)；Obsidian 规范：[knowledge/domain/obsidian-workflow.md](../../knowledge/domain/obsidian-workflow.md)

---

## 4. 数据设计

### 4.1 状态管理

SQLite 单文件（`~/.davylinks/state.db`），两张表：

- **processed_articles**：URL 主键去重、摘要缓存、推送状态，90 天自动清理
- **run_log**：每日运行统计（scanned / filtered / pushed / errors / duration），永久保留

写策略三原则：参数化查询（防注入）、`executemany` 批量写入（100 条 ~8ms）、`INSERT OR REPLACE`（支持摘要更新）。

完整 Schema：[api/state-db-schema.md](../api/state-db-schema.md)；决策：[ADR-006](../../knowledge/decisions/006-sqlite-state-management.md)

### 4.2 去重指纹

64 位 hash（v2.0 从 32 位扩展）。32 位在约 7 万篇时碰撞概率达 50%，而 90 天窗口存留量约 9 万篇已逼近危险区；64 位将 10 万篇碰撞概率降到 0.000001%。持久层主键始终是完整 URL，hash 仅作辅助。见 [ADR-007](../../knowledge/decisions/007-64bit-hash-dedup.md)。

### 4.3 数据流纪律

**不可变数据流**：各阶段函数返回新 dict，不修改输入——由 7 个专项测试强制保证。收益是测试无需拷贝、数据流可推理、函数可安全重试。见 [ADR-002](../../knowledge/decisions/002-immutable-data-flow.md)。

---

## 5. 配置与部署

### 5.1 配置体系

三层优先级：**环境变量 > `config/secrets.yaml` > `~/.davylinks/secrets.yaml`**，由 `scripts/config_loader.py` 单点加载，各模块延迟读取（import 时不碰 secrets）。

- **信息源**：`config/sources.json` — 5 个活跃 RSS 源 + wewe-rss 微信聚合；3 个失效源保留配置（机器之心/虎嗅/InfoQ），带 `disabled_reason`
- **密钥**：`config/secrets.yaml` — 飞书凭证、4 家 LLM API Key、Obsidian vault 路径、可选 Davybase notify 复用

格式规范：[api/config-format.md](../api/config-format.md)；延迟加载决策：[ADR-003](../../knowledge/decisions/003-lazy-config-loading.md)

### 5.2 运行模式

| 模式 | 命令 | 用途 |
|------|------|------|
| 完整管线 | `pipeline.py` | 每日定时执行（Hermes cron 触发） |
| 预览 | `pipeline.py --dry-run` | 只扫描+摘要，不推送不保存 |
| 跳过推送/保存 | `--skip-push` / `--skip-save` | 分阶段调试 |
| 数据清理 | `--cleanup` | 清理 90 天前旧记录 |

CLI 全参考：[api/pipeline-cli.md](../api/pipeline-cli.md)；快速上手：[guides/quickstart.md](../guides/quickstart.md)

### 5.3 性能指标

| 指标 | 数值 |
|------|------|
| 扫描速度 | ~50 篇/秒 |
| 聚类耗时（100 篇） | < 1ms（倒排索引优化后，较 O(n²) 提速最高 2400x） |
| 摘要耗时（TOP 5 并行） | ~30-50s（4 路并行，串行 250s） |
| 全管线端到端 | ~60s |

---

## 6. 质量保障

### 6.1 测试体系

19 个测试用例（7 个文件），覆盖五个维度：

| 维度 | 测试文件 | 要点 |
|------|----------|------|
| 配置加载 | test_config_loader.py | 优先级、环境变量覆盖、deep merge |
| 模块集成 | test_config_integration.py | 各模块统一走 config_loader |
| 管线编排 | test_pipeline.py | 错误计数、状态记录 |
| 聚类算法 | test_scan_articles.py | 中文二元组重叠合并 |
| 数据库 | test_state_db.py | 参数化查询、executemany、update 语义 |
| **不可变性** | test_immutability.py | 7 个测试保证输入不被修改、hash 确定性 |

### 6.2 安全设计

- SQL 一律参数化（`cleanup_old` 曾存在 f-string 注入风险，已修复）
- 密钥零硬编码，全部经 config_loader 加载，延迟初始化
- 失败时 exit code 非零（可观测），bare except 已清除

质量演进全记录：[knowledge/evolution/v2.0-code-review.md](../../knowledge/evolution/v2.0-code-review.md)

---

## 7. 设计决策索引

全部 8 条 ADR 见 [knowledge/decisions/](../../knowledge/decisions/)：

| # | 决策 | 一句话理由 |
|---|------|-----------|
| [001](../../knowledge/decisions/001-inverted-index-clustering.md) | 倒排索引聚类 | O(n²) 在百篇级成瓶颈；倒排索引零依赖提速 2400x |
| [002](../../knowledge/decisions/002-immutable-data-flow.md) | 不可变数据流 | 副作用不可预测是调试噩梦；返回新 dict 可推理可重试 |
| [003](../../knowledge/decisions/003-lazy-config-loading.md) | 延迟配置加载 | import 即读 secrets 导致测试脆弱；延迟初始化消除副作用 |
| [004](../../knowledge/decisions/004-multi-llm-fallback.md) | 4 路 LLM fallback | 单供应商全年必有故障窗口；异构冗余真正可用 |
| [005](../../knowledge/decisions/005-top5-only-obsidian.md) | 仅 TOP 5 入 Obsidian | 全量入库年增 18000 篇检索价值趋零；档案职能归飞书表格 |
| [006](../../knowledge/decisions/006-sqlite-state-management.md) | SQLite 状态管理 | 去重/断点/统计三需求，单文件零部署完美匹配 |
| [007](../../knowledge/decisions/007-64bit-hash-dedup.md) | 64 位哈希 | 32 位在业务规模下逼近 50% 碰撞区 |
| [008](../../knowledge/decisions/008-dual-llm-api-format.md) | 双 API 格式白名单 | 格式分裂是现实；3 行白名单优于引入统一库重依赖 |

---

## 8. 演进历程与方向调整

### 8.1 版本演进

| 版本 | 时间 | 主题 | 关键产出 |
|------|------|------|----------|
| 原始设计 | 2026-05-04 前 | Hermes Agent 编排的 5 阶段方案 | [original-requirement.md](original-requirement.md) |
| v1.0 | 2026-05-04 | MVP 跑通 | 4 项严重修复、倒排索引优化、基础文档 |
| v2.0 | 2026-06-05 | 质量/安全优先 | 14 项修复、19 测试、config_loader 统一 |

详细记录：[evolution/v1.0-mvp.md](../../knowledge/evolution/v1.0-mvp.md)、[evolution/v2.0-code-review.md](../../knowledge/evolution/v2.0-code-review.md)

### 8.2 重大方向调整

1. **Hermes Agent 编排 → 纯 Python 管线**：确定性流程不该用 LLM Agent 编排——不可预测、成本高、不可复现。Agent 适合决策不确定的环节，不适合流程确定的管道
2. **5 阶段 → 6 阶段**：新增飞书多维表格（Phase 3.5），建立"全量档案 + 精华推送 + 知识沉淀"三层出口
3. **配置自治 → 统一 config_loader**：三份复制的 YAML 解析器已出现行为漂移风险，单点加载是唯一可推理的方案
4. **功能优先 → 质量优先**：MVP 跑通后立即安排专项清理迭代，债务拖越久修复越贵

完整记录（含未决方向）：[evolution/direction-changes.md](../../knowledge/evolution/direction-changes.md)

---

## 9. 现状评估与后续规划

### 9.1 当前能力边界

**已稳定**：多源扫描、话题聚类、多路 LLM 摘要、三层出口推送、状态管理与断点续传、19 测试回归防线。

**已知局限**：

- 聚类依赖中文二元组近似语义，无语义向量，跨语言同话题（中文报道 vs Hacker News 英文原文）合并能力弱
- 关键词过滤为白名单模式，无负面关键词（广告/软文依赖权重压制）
- 摘要 prompt 固定单一风格
- 微信公众号链路依赖 wewe-rss 本地服务与读书账号额度，存在风控断供风险

### 9.2 规划路线

| 优先级 | 方向 | 说明 |
|--------|------|------|
| 近期 | 负面关键词过滤 | 排除广告/软文，成本低收益明确 |
| 近期 | 提取 pipeline.py phase runners | 降低 main() 复杂度（v2.0 已识别） |
| 中期 | 用户反馈闭环 | 飞书消息"有用/没用"按钮 → 调整权重 |
| 中期 | 个性化推荐 | 基于历史阅读行为调整关键词权重（依赖反馈闭环） |
| 远期 | 语义向量聚类 | embedding 辅助跨语言同话题合并 |
| 远期 | Twitter/X 接入 | 依赖第三方工具，成本待评估 |

---

## 10. 文档地图

| 层级 | 位置 | 内容 |
|------|------|------|
| 项目文档 | [docs/](../README.md) | 怎么用：architecture / guides / api / design |
| 知识库 | [knowledge/](../../knowledge/README.md) | 为什么：domain / decisions / evolution / reference |
| 变更记录 | [CHANGELOG.md](../../CHANGELOG.md) | 版本级变更 |
| 开发规范 | [CONTRIBUTING.md](../../CONTRIBUTING.md) | 代码约定 + 文档同步义务 |
| AI 指令 | [CLAUDE.md](../../CLAUDE.md) | AI 助手唯一指令来源 |

> 维护约定：本报告与代码同步更新（管线行为变更时同步第 3-5 章），完整规则见 CONTRIBUTING.md。
