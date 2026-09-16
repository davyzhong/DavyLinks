# Changelog

本文档记录 DavyLinks 的所有重要变更。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)。

各版本的详细演进过程（性能对比、code review 细节、架构演进）见 `knowledge/evolution/` 目录。

## [Unreleased]

### Changed

- **删除手写 YAML 子集解析器**：`config_loader.py` 移除 `_parse_yaml_simple` fallback，统一使用 PyYAML；`pyyaml` 从可选依赖转为必装依赖。消除手写解析器不支持列表/多行字符串导致的静默解析错误风险（该解析器历史上曾被复制 3 份引发行为漂移，见 evolution/v2.0）
- **修正 ADR-007 文档失配**：`hash_url` 实际实现为 `hashlib.md5` 截断（非内置 `hash()`），ADR 描述与代码对齐

### 评估记录（2026-09-16 重复造轮子审查）

- `feishu_bitable.py` 的 token 缓存已存在（提前 60s 过期），无需改动
- LLM 双格式手写调用、聚类 bigram 方案维持 ADR-008/ADR-001 记录的刻意权衡，边界条件见各 ADR

## [v2.0] - 2026-06-05

本次迭代聚焦代码质量、安全性、可测试性和文档完整性，通过系统性 code review 发现并修复 14 个问题。

### Fixed

- **SQL 注入漏洞**：`state_db.py` 的 `cleanup_old` 改为参数化查询，替代 f-string 拼接
- **`_parse_yaml_simple` 重复定义 3 份**：删除 `summarize.py`、`feishu_bitable.py` 中的副本，统一从 `config_loader` 导入
- **`pipeline.py` 重复 import**：合并为一次导入块
- **数据变异（Mutation）贯穿整个管线**：`filter_by_keywords`/`summarize_one`/`final_sort`/`main()` 全部改为返回新 dict
- **模块顶层加载配置**：`feishu_bitable.py`、`push_feishu.py` 改为 lazy init（`_get_config()` 首次调用时加载）
- **时区计算错误**：`scan_articles.py` 保留 tzinfo，使用 `datetime.now(timezone.utc)`
- **失败时 exit code 为 0**：`pipeline.py` 的 `main()` 返回 `stats`，`__main__` 根据 errors 数设置 exit code
- **`bare except: pass` 静默失败**：改为 `logger.debug` 记录异常
- **`score:.1f` 类型不安全**：`save_obsidian.py` 显式 `float(score)` 转换
- **特征重复计算**：`build_entity_index` 改为接受预计算的 `article_features`

### Added

- **`scripts/config_loader.py` 统一配置加载器**（135 行）：`load_secrets()` 多层 secrets 合并、`get_feishu_config()`、`get_llm_provider_configs()`、`get_obsidian_config()`、`get_davybase_config()`、内置 YAML 解析器（无依赖）、`_deep_merge()` 深度合并
- **19 个测试用例**（7 个测试文件，447 行）：
  - `tests/conftest.py` - pytest 配置，统一 `sys.path` 管理
  - `tests/test_config_loader.py` - 配置加载优先级、环境变量覆盖、deep merge（3 个测试）
  - `tests/test_config_integration.py` - 模块集成测试（2 个测试）
  - `tests/test_pipeline.py` - 管线编排测试（1 个测试）
  - `tests/test_push_feishu.py` - 飞书推送测试（2 个测试）
  - `tests/test_scan_articles.py` - 聚类算法测试（1 个测试）
  - `tests/test_state_db.py` - 数据库测试（3 个测试）
  - `tests/test_immutability.py` - 不可变性测试（7 个测试）
- **`scripts/check.sh`** 本地校验脚本（编译 + 测试）
- **`CLAUDE.md`** Claude Code 快速参考（项目指令）

### Changed

- **不可变数据流**：管线各阶段函数返回新 dict，不修改输入数据
- **延迟配置加载**：各模块首次调用时初始化，不在 import 时读取 secrets
- **批量写入**：`mark_processed` 用 `executemany` 替代逐条 INSERT（100 条写入约 12.5x 提升）
- **hash_url 扩展到 64 bit**（16 hex chars），消除 32 bit 碰撞风险
- **管线从 5 阶段扩展为 6 阶段**：新增 Phase 3.5（`feishu_bitable` 飞书多维表格写入独立成阶段）
- **`requirements.txt`** 移除未使用的 `requests` 依赖
- **文档全面更新**：README、CLAUDE、USAGE、ARCHITECTURE、requirement.md（历史标记）、skills/davylinks-pipeline.md 同步至当前实现

## [v1.0] - 2026-05-04

首个可用版本（MVP）：从单文件脚本演进为多阶段 Python 管线，补齐去重、日志、配置管理等基础设施。

### Fixed

- **飞书凭证硬编码**：改为 `load_feishu_config()` 支持环境变量 + secrets.yaml
- **LLM API 格式 bug**：`ANTHROPIC_PROVIDERS = {"kimi", "zhipu"}`，Kimi/Zhipu 用 Anthropic 格式，Qwen/MiniMax 用 OpenAI 格式
- **`timedelta` 导入缺失**：移到模块级导入
- **`mark_processed` 无法更新摘要**：改用 `INSERT OR REPLACE`
- **blogwatcher 输出解析脆弱**：重写 `parse_blogwatcher_output()` 支持多行文本
- **`feishu_bitable.py` 缺失 `import re`**：补上
- **`feishu_bitable.py` token 获取**：修复 tenant_access_token 获取逻辑

### Added

- **`README.md`** 项目概述和快速开始
- **`ARCHITECTURE.md`** 架构设计文档
- **`USAGE.md`** 详细使用指南
- **`scripts/logging_config.py`** 统一日志配置模块
- **`config/secrets.example.yaml`** 配置模板
- **`config/sources.json`** 信息源配置（6 个活跃源，3 个已禁用）
- **`config/secrets.yaml`** 作为主配置位置
- **`.gitignore`** Git 忽略规则
- **`requirements.txt`** Python 依赖声明
- **`skills/davylinks-pipeline.md`** Hermes skill 定义
- **`state_db.py` SQLite 状态库**：URL 主键去重 + run_log 运行日志 + 90 天自动清理

### Changed

- **架构拆分**：单文件 `scan_articles.js`（300 行）拆分为按阶段职责分离的 Python 脚本（scan / summarize / feishu_bitable / push_feishu / save_obsidian / pipeline）
- **话题聚类从 O(n²) 优化为 O(n)**：倒排索引预计算实体和二元组，比较次数减少 80-95%（100 篇文章约 2400x 提升）
- **信息源精简**：禁用机器之心、虎嗅、InfoQ（无可用 feed）
- **Python 版本**：确认支持 3.9+（非仅 3.10+）
- **blogwatcher 命令**：确认正确命令为 `blogwatcher-cli articles`

### Known Issues（遗留待办）

- 管线 subprocess 开销（保留 CLI 独立性，设计决策）
- 跳过的文章摘要为空（设计决策）
- run_log 同日覆盖（每日汇总日志，预期行为）
- Obsidian 路径硬编码（已支持环境变量，待完全配置化）
- 无单元测试（v2.0 补齐）
