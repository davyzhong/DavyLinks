# HANDOFF — 会话交接文档

> 会话日期: 2026-09-12 / 2026-09-16（两轮） | 分支: `docs/claude-md-improvements` | 工作区 clean，全部已推送
> 本文件为会话交接用途，下次会话确认无事可补后可归档至 `docs/archive/`。

---

## 1. 项目背景（两轮会话的总体任务）

用户（qiming）提出：项目经历几次大方向调整后文档混乱，要求：

1. **第一轮 (09-12)**：把积累的行业知识/业务知识整理为静态知识库 → 重构文档体系 → 撰写设计报告 ✅ 全部完成
2. **第二轮 (09-16)**：盘点可视化提交物 + 大幅美化 README（要求大量图形/图像）✅ 全部完成

## 2. 已完成的内容

### 第一轮：文档体系重构（commit `b41a7cd`、`257594b`、`b6085fc`）

```
根目录: README.md / CLAUDE.md / CHANGELOG.md / CONTRIBUTING.md / AGENTS.md(存根) / HANDOFF.md(本文件)
docs/       — "怎么用"
├── architecture/  overview, pipeline, clustering, summarization, data-flow (拆自 ARCHITECTURE.md)
├── guides/        quickstart, configuration, feishu-setup, obsidian-setup, troubleshooting (拆自 USAGE.md)
├── api/           pipeline-cli, config-format, state-db-schema
├── design/        design-report.md(设计报告·权威入口), current-design.md, original-requirement.md(归档)
└── assets/        hero-pipeline.svg, clustering.svg, outputs.svg, performance.svg  ← 第二轮新增
knowledge/  — "为什么这么做"
├── domain/        rss-ecosystem, llm-landscape, feishu-platform, obsidian-workflow, tech-news-landscape
├── decisions/     ADR-001~008 + README 索引
├── evolution/     v1.0-mvp, v2.0-code-review, direction-changes(方向调整记录)
└── reference/     sources-analysis, llm-api-cheatsheet, feishu-api-cheatsheet
```

- CLAUDE.md 为 AI 指令唯一来源，AGENTS.md 改为存根；CONTRIBUTING.md 定义文档与代码同步义务
- 旧文件 ARCHITECTURE.md / USAGE.md / OPTIMIZATION_COMPLETE.md / requirement.md 已 git rm（内容 100% 迁移）
- 设计报告 `docs/design/design-report.md` 10 章：业务背景、架构、决策索引、**已知局限**（跨语言聚类弱/无负面关键词/wewe-rss 断供风险）+ 分优先级路线图

### 第二轮：README 美化 + 可视化资产（commit `13de78f`）

**可视化提交物盘点结论**：项目是 headless 管线，无 GUI。产出在三个外部出口：

| 出口 | 位置 | 状态 |
|------|------|------|
| Obsidian 每日精华 | `~/ObsidianWiki/知识助理/每日精华/` | 本机 6 份历史产出（2026-04-24 ~ 06-06），最新 `2026-06-06.md` |
| 飞书群消息卡片 | 飞书群 | 需登录飞书查看 |
| 飞书多维表格 | 飞书 Bitable | 全量档案，需登录飞书查看 |
| SQLite 状态库 | `~/.davylinks/state.db` | 已处理 147 篇，最后运行 2026-06-06（`python scripts/state_db.py` 只读查询） |

**新增 4 张 SVG**（`docs/assets/`，手绘、GitHub/本地 md 均可渲染）：

| 文件 | 内容 |
|------|------|
| `hero-pipeline.svg` | 六阶段管线总览：信息源 → 漏斗（100+→20-80→15→5）→ 多源交叉验证机制 |
| `clustering.svg` | 聚类算法原理四步图 + 2400x 提速对比（用 DeepSeek V4 真实例子） |
| `outputs.svg` | 三层出口**真实产出还原**（内容取自 2026-06-06 运行：飞书卡片 + Bitable + Obsidian） |
| `performance.svg` | 性能对比：聚类 2400x、LLM 并行 5x、4 张指标卡 |

**README 重构**：居中 hero + 5 badges + Mermaid 管线图 + 痛点/方案表 + 真实产出节选（折叠块：Obsidian 笔记原文 + 终端输出）+ 折叠运行模式/配置 + 质量保障表 + 文档导航。

## 3. 卡住的问题

**无阻塞问题。** 非阻塞事项：

1. `templates/` 目录存在但为空，未纳入文档体系——可删除或放 Obsidian frontmatter 模板（删除需用户确认）
2. `docs/design/original-requirement.md` 顶部历史提示的表述未逐一复核是否完全对齐新结构
3. **管线自 2026-06-06 后未再运行**（3 个多月）——下次实际运行前建议先检查 wewe-rss 本地服务（:4000）是否存活、LLM API Key 是否仍有效
4. 根目录 HANDOFF.md 是纪律外临时文件，处理完后建议归档

## 4. 下一步计划

### 功能规划（已写入 design-report.md 第 9 章）

| 优先级 | 事项 | 说明 |
|--------|------|------|
| 近期 | 负面关键词过滤 | 排除广告/软文；改 scan_articles.py + sources.json，成本低 |
| 近期 | 代码小清理 | 提取 pipeline.py phase runners；移除 build_candidate_pairs 未用参数、state_db.py 未用 timedelta import（v2.0 LOW 项） |
| 中期 | 用户反馈闭环 | 飞书消息"有用/没用"按钮 → 写 SQLite → 调整权重 |
| 中期 | 个性化推荐 | 依赖反馈闭环先行 |
| 远期 | 语义向量聚类 | embedding 辅助跨语言同话题合并 |
| 远期 | Twitter/X 接入 | 依赖第三方工具，成本待评估 |

### 文档维护义务（见 CONTRIBUTING.md）

- 改管线行为 → 同步 `docs/architecture/pipeline.md` + `docs/design/current-design.md` + 设计报告对应章节
- 新增设计决策 → `knowledge/decisions/` 新 ADR（序号从 009 起）+ 更新其 README 索引
- 配置格式变更 → `docs/api/config-format.md`；版本级变更 → `CHANGELOG.md`
- **根目录不再新增 .md**（HANDOFF.md 是临时例外）
- README 用到的 4 张 SVG 若架构变更需同步重绘（源码即文件，直接编辑）

## 5. 踩过的坑

**本次新增（第二轮）**：

1. **SVG 渲染验证工具链**：`qlmanage -t` 对 SVG 不可用（报错）；ImageMagick `magick` 虽已安装（/opt/homebrew/bin/magick）但 MSVG 渲染器缺字体报 `unable to read font`。**可靠路径是 Chrome headless**：
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
     --screenshot=/tmp/check.png --window-size=960,2120 --hide-scrollbars "file:///tmp/view.html"
   ```
   把 SVG 用 `<img>` 引进一个 html 再截图，与 GitHub 实际渲染最接近。改 SVG 后建议走一遍此验证。
2. **SVG 属性值尾随空格**（`width="420 "`）Chrome 容忍但严格解析器可能出错——写 SVG 时注意。

**第一轮的坑（仍需记住）**：

3. CLAUDE.md 与 AGENTS.md 曾内容漂移（延迟加载模块数 2 vs 3，代码验证实为 3：feishu_bitable / push_feishu / save_obsidian）——事实只维护 CLAUDE.md 一处
4. `knowledge/decisions/` 引用 `docs/` 的相对链接是 `../../docs/...`（两层），首写容易多一层；全库链接检查脚本见下方"验证状态"
5. 方案偏差记录：原方案"删除 AGENTS.md"，实际改为存根指向 CLAUDE.md（兼容读取 AGENTS.md 的工具，Davybase 同款）
6. 项目固有坑（已沉淀进知识库，此处仅索引）：`blogwatcher-cli articles`（不是 `blogwatcher scan`）；LLM 格式分裂 Kimi/Zhipu=Anthropic、Qwen/MiniMax=OpenAI（ADR-008）；飞书必须把应用加为多维表格协作者（编辑权限）；中文 RSS 持续萎缩 + wewe-rss 有账号风控断供风险；`INSERT OR REPLACE` 同日重跑覆盖 run_log（设计取舍）

## 6. 验证状态

```bash
sh scripts/check.sh        # ✅ 19 passed (每轮改动后均验证)
git log --oneline -5       # 13de78f README美化 / b6085fc HANDOFF / 257594b 设计报告 / b41a7cd 文档重构
git status                 # clean，均已推送

# 链接完整性检查（文档改动后跑一遍，含 <img src> 检查）
python3 - <<'EOF'
import os, re
broken = []
for root, dirs, files in os.walk('.'):
    dirs[:] = [d for d in dirs if d not in ('.git','.venv','__pycache__','.pytest_cache')]
    for f in files:
        if not f.endswith('.md'): continue
        path = os.path.join(root, f)
        content = open(path).read()
        for m in re.finditer(r'\]\(([^)#]+?)(#[^)]*)?\)', content):
            link = m.group(1).strip()
            if link.startswith(('http','mailto:')) or '{' in link: continue
            if not os.path.exists(os.path.normpath(os.path.join(root, link))):
                broken.append(f"{path} -> {link}")
        for m in re.finditer(r'<img src="([^"]+)"', content):
            if not os.path.exists(os.path.normpath(os.path.join(root, m.group(1)))):
                broken.append(f"{path} img -> {m.group(1)}")
print('\n'.join(broken) if broken else 'OK')
EOF
```
