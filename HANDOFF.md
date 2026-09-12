# HANDOFF — 会话交接文档

> 会话日期: 2026-09-12 | 分支: `docs/claude-md-improvements` | 工作区已 clean，全部已推送
> 本文件为会话交接用途，下次会话确认无事可补后可归档至 `docs/archive/`。

---

## 1. 本次任务是什么

用户（qiming）提出：项目经历几次大方向调整后文档混乱，要求把积累的行业知识/业务知识**全部整理为静态知识库**，再基于这些素材写**项目设计报告**——彻底摆脱"依赖对话记忆的动态知识"。

执行分四步（用户已确认方案）：

1. 设计知识库/素材结构
2. 重构项目文档结构（目录、命名、导航）
3. 沉淀领域知识
4. 撰写设计报告

## 2. 已完成的内容

**全部完成，无遗留。** 两个 commit 均已推送：`b41a7cd`（文档体系重构）、`257594b`(设计报告)。测试 19/19 通过，全库 markdown 链接检查通过。

### 文档体系（最终形态）

```
根目录: README.md / CLAUDE.md / CHANGELOG.md / CONTRIBUTING.md / AGENTS.md(存根) / HANDOFF.md(本文件)
docs/       — "怎么用"
├── architecture/  overview, pipeline, clustering, summarization, data-flow (拆自 ARCHITECTURE.md)
├── guides/        quickstart, configuration, feishu-setup, obsidian-setup, troubleshooting (拆自 USAGE.md)
├── api/           pipeline-cli, config-format, state-db-schema
└── design/        design-report.md(设计报告·权威入口), current-design.md, original-requirement.md(归档)
knowledge/  — "为什么这么做"
├── domain/        rss-ecosystem, llm-landscape, feishu-platform, obsidian-workflow, tech-news-landscape
├── decisions/     ADR-001~008 + README 索引
├── evolution/     v1.0-mvp, v2.0-code-review, direction-changes(方向调整记录)
└── reference/     sources-analysis, llm-api-cheatsheet, feishu-api-cheatsheet
```

### 关键动作清单

| 动作 | 结果 |
|------|------|
| ARCHITECTURE.md (513行) 拆分 | → docs/architecture/ 5 篇，35 个关键技术 token 对照验证无遗漏 |
| USAGE.md (323行) 拆分 | → docs/guides/ 5 篇 |
| OPTIMIZATION_COMPLETE.md 拆分 | → CHANGELOG.md + knowledge/evolution/ 两篇演进文档 |
| requirement.md 归档 | → docs/design/original-requirement.md（原文件已 git rm） |
| CLAUDE.md + AGENTS.md 合并 | CLAUDE.md 为唯一指令来源；AGENTS.md 改为存根（见坑 #3） |
| 新增 20 篇知识文档 | domain×5、ADR×8、reference×3、evolution×3、索引×1 |
| 新增设计报告 | docs/design/design-report.md，10 章，总-分结构链接全部子文档 |
| 新增 CONTRIBUTING.md | 代码约定 + **文档与代码同步义务表**（改什么必须同步哪些文档） |
| 删除 4 个旧根目录文档 | ARCHITECTURE.md / USAGE.md / OPTIMIZATION_COMPLETE.md / requirement.md（git rm，历史可恢复） |
| 导航更新 | docs/README.md、knowledge/README.md、CLAUDE.md 文档表 |

### 本次会话产出的重要事实修正

- **延迟配置加载实为 3 个模块**（feishu_bitable / push_feishu / save_obsidian）。旧 CLAUDE.md 写 2 个是错的，经代码验证 `save_obsidian.py:24` 的 `get_obsidian_config()` 在 `load_vault_path()` 函数内首次调用，已修正。

## 3. 卡住的问题

**无阻塞问题。** 以下为已知非阻塞事项：

1. `templates/` 目录存在但为空，未纳入本次文档体系——可考虑删除或放入 Obsidian frontmatter 模板（未动，删除需用户确认）
2. `docs/design/original-requirement.md` 顶部的历史提示仍指向旧文档名（README/ARCHITECTURE/USAGE），已由归档 agent 更新过一轮，未逐一复核表述是否完全对齐新结构
3. 根目录 HANDOFF.md（本文件）是纪律外的临时文件，处理完后建议归档

## 4. 下一步计划

### 功能规划（已写入 design-report.md 第 9 章，按优先级）

| 优先级 | 事项 | 说明 |
|--------|------|------|
| 近期 | 负面关键词过滤 | 排除广告/软文；改 scan_articles.py + sources.json，成本低 |
| 近期 | 代码小清理 | 提取 pipeline.py phase runners；移除 build_candidate_pairs 未用的 articles 参数、state_db.py 未用的 timedelta import（v2.0 已识别的 LOW 项） |
| 中期 | 用户反馈闭环 | 飞书消息加"有用/没用"按钮 → 回调写 SQLite → 调整权重 |
| 中期 | 个性化推荐 | 依赖反馈闭环先行 |
| 远期 | 语义向量聚类 | embedding 辅助跨语言同话题合并（当前二元组方案做不到中英合并） |
| 远期 | Twitter/X 接入 | 依赖第三方工具，成本待评估 |

### 文档维护义务（新纪律，见 CONTRIBUTING.md）

- 改管线行为 → 同步 `docs/architecture/pipeline.md` + `docs/design/current-design.md` + 设计报告对应章节
- 新增重要设计决策 → `knowledge/decisions/` 新 ADR（序号从 009 起），并更新其 README 索引
- 配置格式变更 → `docs/api/config-format.md`
- 版本级变更 → `CHANGELOG.md` 追加
- **根目录不再新增 .md**（HANDOFF.md 是临时例外）

## 5. 踩过的坑（本次会话新踩 + 必须记住的）

1. **CLAUDE.md 与 AGENTS.md 曾内容漂移**：同一事实（延迟加载模块数）两份文件写了不同版本。教训已制度化——AGENTS.md 现为存根，事实只维护在 CLAUDE.md 一处。
2. **相对链接层级易错**：knowledge/decisions/ 引用 docs/ 需要 `../../docs/...`（两层），首写多了一层。全库链接检查脚本已在本会话验证可用（见下方命令），建议每次文档改动后跑一遍：
   ```bash
   python3 - <<'EOF'
   import os, re
   broken = []
   for root, dirs, files in os.walk('.'):
       dirs[:] = [d for d in dirs if d not in ('.git','.venv','__pycache__','.pytest_cache')]
       for f in files:
           if not f.endswith('.md'): continue
           path = os.path.join(root, f)
           for m in re.finditer(r'\]\(([^)#]+?)(#[^)]*)?\)', open(path).read()):
               link = m.group(1).strip()
               if link.startswith(('http','mailto:')) or '{' in link: continue
               if not os.path.exists(os.path.normpath(os.path.join(root, link))):
                   broken.append(f"{path} -> {link}")
   print('\n'.join(broken) if broken else 'OK')
   EOF
   ```
3. **方案偏差记录**：原方案是"删除 AGENTS.md"，实际改为存根指向 CLAUDE.md——因部分工具仍读取 AGENTS.md，且 Davybase 项目同款做法，删除不如存根稳妥。用户未提出异议，如需彻底删除请确认。
4. **项目固有坑**（已沉淀进知识库，此处仅索引）：
   - blogwatcher 命令是 `blogwatcher-cli articles`，不是 `blogwatcher scan`
   - LLM API 格式分裂：Kimi/Zhipu = Anthropic 格式，Qwen/MiniMax/DeepSeek = OpenAI 格式，新增供应商先确认格式（ADR-008）
   - 飞书最常踩：只开 API scope 不够，**必须把应用加为多维表格协作者（编辑权限）**
   - 中文 RSS 持续萎缩：机器之心/虎嗅/InfoQ 已失效；微信公众号依赖 wewe-rss（本地 :4000），存在账号风控断供风险
   - Python `hash()` 受 PYTHONHASHSEED 影响进程间不一致——本项目仅单进程内使用，无实际影响（ADR-007）
   - `INSERT OR REPLACE` 意味着同一天多次运行会覆盖当日 run_log 记录（设计取舍，非 bug）

## 6. 验证状态

```bash
sh scripts/check.sh        # ✅ 19 passed (本次两次验证)
git log --oneline -2       # 257594b 设计报告 / b41a7cd 文档重构
git status                 # clean，均已推送
```
