# HANDOFF — 会话交接文档

> 会话日期: 2026-09-12 / 09-16（三轮） | 分支: `docs/claude-md-improvements` | 工作区 clean，全部已推送
> 本文件为会话交接用途，下次会话确认无事可补后可归档至 `docs/archive/`。

---

## 1. 项目背景（三轮会话的总体任务）

用户（qiming）主导的三轮工作：

1. **第一轮 (09-12)**：把积累的行业知识/业务知识整理为静态知识库 → 重构文档体系 → 撰写设计报告 ✅
2. **第二轮 (09-16 上午)**：盘点可视化提交物 + 大幅美化 README（4 张 SVG + 真实产出示例）✅
3. **第三轮 (09-16 下午)**：重复造轮子审查（"行业有标准库但我们手写了"）→ 落地修复 ✅

## 2. 已完成的内容

### 文档体系（第一轮，commit `b41a7cd`、`257594b`、`b6085fc`）

```
根目录: README.md / CLAUDE.md / CHANGELOG.md / CONTRIBUTING.md / AGENTS.md(存根) / HANDOFF.md(本文件)
docs/       — "怎么用"
├── architecture/  overview, pipeline, clustering, summarization, data-flow
├── guides/        quickstart, configuration, feishu-setup, obsidian-setup, troubleshooting
├── api/           pipeline-cli, config-format, state-db-schema
├── design/        design-report.md(设计报告·权威入口), current-design.md, original-requirement.md(归档)
└── assets/        hero-pipeline.svg, clustering.svg, outputs.svg, performance.svg
knowledge/  — "为什么这么做"
├── domain/        rss-ecosystem, llm-landscape, feishu-platform, obsidian-workflow, tech-news-landscape
├── decisions/     ADR-001~008 + README 索引
├── evolution/     v1.0-mvp, v2.0-code-review, direction-changes
└── reference/     sources-analysis, llm-api-cheatsheet, feishu-api-cheatsheet
```

CLAUDE.md 是 AI 指令唯一来源；CONTRIBUTING.md 定义文档与代码同步义务；旧文件 ARCHITECTURE/USAGE/OPTIMIZATION_COMPLETE/requirement.md 已 git rm。

### README 美化（第二轮，commit `13de78f`）

- 4 张手绘 SVG（管线总览/聚类算法/三层出口真实产出还原/性能对比），Chrome headless 渲染验证过
- README 重构：badges + Mermaid + 痛点方案表 + 真实产出节选（2026-06-06 数据）
- 可视化提交物结论：项目是 headless 管线，产出在 Obsidian（本机 6 份，最新 2026-06-06）、飞书卡片、飞书 Bitable 三处

### 重复造轮子审查 + 修复（第三轮，commit `3faf3b5`）

**审查结论**（已记入 CHANGELOG Unreleased 段）：

| 项 | 判定 | 处置 |
|----|------|------|
| 手写 YAML 子集解析器（config_loader.py） | ❌ 真造轮子 | **已删**（~40 行），pyyaml 转必装，消除静默解析错误风险 |
| 飞书 token 手工管理 | ✅ 缓存已存在（提前 60s 过期） | 无需改动（首次评估误判，见坑 #1） |
| LLM 双格式手写调用 | 刻意权衡（ADR-008） | 维持；触发换 litellm 的条件：要加流式/多轮/工具调用 |
| 聚类 bigram 不用分词/embedding | 刻意权衡（ADR-001） | 维持；触发换 embedding 的条件：跨语言同话题需求 |
| HTTP 用 urllib 标准库 | 刻意权衡（零依赖取向） | 维持 |
| RSS 抓取/Atom 解析/hash/SQLite/pytest | 无问题 | blogwatcher-cli 复用、ElementTree、hashlib.md5 均为正确做法 |

**落地改动**：`_parse_yaml_simple` 删除、`import yaml` 提顶、requirements.txt pyyaml 转必装、ADR-007 修正（hash_url 实为 `hashlib.md5` 截断而非内置 `hash()`）、data-flow.md 同步、CHANGELOG 加 Unreleased 段。

## 3. 卡住的问题

**无阻塞问题。** 非阻塞事项：

1. `templates/` 目录存在但为空——可删除或放 Obsidian frontmatter 模板（删除需用户确认）
2. `docs/design/original-requirement.md` 顶部历史提示的表述未逐一复核是否完全对齐新结构
3. **管线自 2026-06-06 后未再运行**（截至 09-16 已 3 个多月）——下次实际运行前先检查 wewe-rss 本地服务（:4000）存活、LLM API Key 有效性、飞书凭证有效性
4. 根目录 HANDOFF.md 是纪律外临时文件，处理完后建议归档

## 4. 下一步计划

### 功能规划（详见 design-report.md 第 9 章）

| 优先级 | 事项 | 说明 |
|--------|------|------|
| 近期 | 负面关键词过滤 | 排除广告/软文；改 scan_articles.py + sources.json |
| 近期 | 代码小清理 | 提取 pipeline.py phase runners；移除 build_candidate_pairs 未用参数、state_db.py 未用 timedelta import |
| 中期 | 用户反馈闭环 | 飞书"有用/没用"按钮 → 写 SQLite → 调整权重 |
| 中期 | 个性化推荐 | 依赖反馈闭环 |
| 远期 | 语义向量聚类 / Twitter/X | 触发条件与成本见 ADR-001 / direction-changes |

### 依赖演进边界（第三轮审查确立，写在各 ADR + CHANGELOG）

- LLM 调用换 litellm：需要流式/多轮/工具调用时
- 聚类换 embedding：出现跨语言同话题需求时
- 飞书换官方 SDK lark-oapi：功能扩展到更多端点/回调时（当前 token 缓存已够用）

### 文档维护义务（见 CONTRIBUTING.md）

- 改管线行为 → 同步 architecture/pipeline.md + design/current-design.md + 设计报告
- 新增设计决策 → knowledge/decisions/ 新 ADR（序号从 009 起）+ 更新索引
- 架构变更需重绘 docs/assets/ 4 张 SVG（Chrome headless 验证，命令见坑 #2）
- 根目录不再新增 .md

## 5. 踩过的坑

1. **⚠️ 下"缺失"结论前必须读完整实现**（第三轮新踩）：审查时只看 grep 函数签名就断言"飞书 token 无缓存"，实际 `_token_cache` + 60s 提前过期早已实现。已写入 CHANGELOG 评估记录防止下次再误判。**教训：grep 命中函数定义 ≠ 看过函数体；评估代码必须读实现。**
2. **SVG 渲染验证工具链**（第二轮）：qlmanage 不支持 SVG；ImageMagick 有但缺字体报错。可靠路径是 Chrome headless 截图（与 GitHub 渲染最接近）：
   ```bash
   "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless \
     --screenshot=/tmp/check.png --window-size=960,2120 --hide-scrollbars "file:///tmp/view.html"
   ```
3. **CLAUDE/AGENTS 内容漂移**（第一轮）：同一事实两份文件写不同版本（延迟加载 2 vs 3 个模块，代码验证为 3：feishu_bitable/push_feishu/save_obsidian）。事实只维护 CLAUDE.md 一处。
4. **相对链接层级**：knowledge/decisions/ 引 docs/ 是 `../../docs/...`（两层）；链接检查脚本见第 6 节，文档改动后必跑。
5. **方案偏差记录**：AGENTS.md 由"删除"改为存根（兼容读取 AGENTS.md 的工具，Davybase 同款）。
6. **项目固有坑**（详见知识库，仅索引）：`blogwatcher-cli articles`（非 `blogwatcher scan`）；Kimi/Zhipu=Anthropic 格式、Qwen/MiniMax=OpenAI 格式（ADR-008）；飞书应用必须加为多维表格协作者；中文 RSS 持续萎缩 + wewe-rss 账号风控断供风险；`INSERT OR REPLACE` 同日重跑覆盖 run_log（设计取舍）。

## 6. 验证状态

```bash
sh scripts/check.sh        # ✅ 19 passed（三轮改动后均验证）
git log --oneline -6       # 3faf3b5 造轮子修复 / 13de78f README美化 / b6085fc+257594b+b41a7cd 文档体系
git status                 # clean，均已推送
```

链接完整性检查（含 `<img src>`，文档改动后必跑）：

```bash
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
