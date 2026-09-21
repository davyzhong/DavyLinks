# 开发规范

> 本文件定义 DavyLinks 的开发纪律。AI 助手额外遵循 [CLAUDE.md](CLAUDE.md)。

## 环境与验证

```bash
# 本地校验（提交前必跑）
sh scripts/check.sh        # 编译检查 + 全部测试

# 仅测试
.venv/bin/python -m pytest tests/ -v
```

改动代码后必须跑 `check.sh`，测试不过不提交。

## 代码约定

- **Python 3.9+** 兼容（不用 3.10+ 语法，如 `match`、`X | Y` 类型联合）
- **不可变数据流**：管线函数返回新 dict，不修改输入（有 `test_immutability.py` 强制保证）
- **延迟配置加载**：不在模块顶层读取 secrets，统一通过 `config_loader` 的 getter 函数
- **SQL 安全**：一律参数化查询；批量写入用 `executemany`
- **密钥不进代码、不进 commit、不进日志**

## 文档维护

**代码改动与文档同步是提交的一部分**，不是"以后再补"：

| 改动类型 | 必须同步 |
|----------|----------|
| 管线阶段行为 | `docs/architecture/pipeline.md` + `docs/design/current-design.md` |
| 聚类/评分算法 | `docs/architecture/clustering.md` |
| LLM 摘要逻辑 | `docs/architecture/summarization.md` |
| 配置格式 | `docs/api/config-format.md` |
| 状态库 Schema | `docs/api/state-db-schema.md` |
| 新增重要设计决策 | `knowledge/decisions/` 新增 ADR（三位序号递增，更新其 README 索引） |
| 信息源增删 | `config/sources.json` + `knowledge/reference/sources-analysis.md` |
| 用户可见功能 | `README.md` + `CHANGELOG.md` |
| CLI 选项 | `docs/api/pipeline-cli.md` |

### 文档命名

- 文件名 kebab-case 全小写：`tech-news-landscape.md`
- ADR：`001-短横线描述.md`
- 目录全小写：`docs/`、`knowledge/`、`guides/`

### 根目录纪律

根目录只保留 4 个 .md：`README.md`、`CLAUDE.md`、`CHANGELOG.md`、`CONTRIBUTING.md`。新文档一律进 `docs/` 或 `knowledge/`，不再往根目录堆。

## 提交规范

Conventional Commits：`feat:` / `fix:` / `refactor:` / `docs:` / `test:` / `chore:` / `perf:`

大幅修改（批量修复/重构/功能交付）完成后测试通过即 commit + push；日常小改动正常提交推送。

## 设计原则（跨项目）

1. **幂等性**：所有操作前检查是否已执行，支持断点续传
2. **增量同步调在线 API**，禁止只查本地
3. **状态必须写 SQLite**（`state_db.py`），不留内存态
4. **知识库目录最多两级**，一级 ≤20 个，二级 ≤10 个
