# DavyLinks 深度 Review 报告

> 生成时间：2026-05-04

---

## 严重问题（建议尽快修复）

### 1. 飞书凭证硬编码在源码中
- **文件**: `scripts/feishu_bitable.py` 第20-21行, `scripts/push_feishu.py` 第21行
- **问题**: APP_ID、APP_SECRET、Webhook URL 直接写在代码里
- **建议**: 迁移到环境变量或 `secrets.yaml`，添加 `.gitignore`

### 2. LLM API 格式判断 bug
- **文件**: `scripts/summarize.py` 第24行
- **问题**: `ANTHROPIC_PROVIDERS = {"kimi", "zhipu", "minimax", "qwen"}` 把所有 LLM 都标为 Anthropic 格式，但 Qwen 和 MiniMax 实际是 OpenAI 格式
- **影响**: Qwen 和 MiniMax 的摘要调用会发送错误的请求格式，导致摘要失败
- **修复**: 改为 `ANTHROPIC_PROVIDERS = {"kimi", "zhipu"}`

### 3. weekly_digest 缺少 timedelta 导入
- **文件**: `scripts/save_obsidian.py` 第112行
- **问题**: `generate_weekly_note()` 使用 `timedelta` 但未在模块级别导入
- **修复**: 将 `from datetime import timedelta` 移到文件顶部

### 4. mark_processed 无法更新摘要
- **文件**: `scripts/state_db.py` 第75行
- **问题**: `INSERT OR IGNORE` 导致已有记录的 summary 字段不会被更新
- **建议**: 改用 `INSERT OR REPLACE` 或增加 `UPDATE ... WHERE url = ?` 逻辑

---

## 中等问题

### 5. blogwatcher 输出解析脆弱
- **文件**: `scripts/scan_articles.py` 第108-144行
- **问题**: 依赖 blogwatcher-cli 的文本输出格式，版本更新就会失效
- **建议**: 使用 `--json` 参数（如有）或直接读取 blogwatcher 的 SQLite 数据库

### 6. O(n²) 话题聚类
- **文件**: `scripts/scan_articles.py` 第286-289行
- **问题**: 两两比较所有文章，信息源增加后会变慢
- **建议**: 先按关键词索引预分组，再在组内比较

### 7. 管线 subprocess 调用开销
- **文件**: `scripts/pipeline.py`
- **问题**: 每个 phase 都启动独立 Python 进程 + JSON 序列化/反序列化
- **建议**: 可考虑重构为模块调用（import + 调用函数），保留 CLI 独立运行能力

### 8. 跳过的文章摘要为空
- **文件**: `scripts/summarize.py` 第363行
- **问题**: 非 TOP 5 的文章摘要为"(摘要已跳过)"
- **建议**: 降级为取 description 前 50 字或提取标题关键词

### 9. 没有 logging 系统
- **问题**: 全部用 `print` + `file=sys.stderr`，无法分级、无法写文件
- **建议**: 统一使用 `logging` 模块

### 10. run_log 同日覆盖
- **文件**: `scripts/state_db.py` 第96行
- **问题**: `INSERT OR REPLACE` 导致同一天多次运行只保留最后一次记录
- **建议**: 改为追加模式

---

## 低优先级改进

### 11. 缺少 .gitignore
- 建议添加：`__pycache__/`, `*.pyc`, `secrets.yaml`, `.env`

### 12. 缺少依赖声明
- 建议添加 `pyproject.toml` 或 `requirements.txt`

### 13. requirement.md 文档过时
- 文档提到"Hermes Agent + delegate_task"，实际是纯 Python + subprocess

### 14. 没有测试
- 建议至少覆盖: `calculate_relevance()`, `should_cluster()`, `parse_articles_output()`, `filter_new_articles()`

### 15. 未匹配来源的 weight 默认为 0
- **文件**: `scripts/scan_articles.py` 第192行
- **建议**: 为 `source_map` 中找不到的来源给默认权重 3

### 16. Obsidian 路径硬编码
- **文件**: `scripts/save_obsidian.py` 第17行
- **建议**: 从统一配置文件读取，或与 Davybase 共享配置
