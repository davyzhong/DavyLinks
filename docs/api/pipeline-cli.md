# 命令行接口

## 主管线 (pipeline.py)

```bash
.venv/bin/python scripts/pipeline.py [OPTIONS]
```

### 选项

| 参数 | 说明 |
|------|------|
| (无参数) | 执行完整管线（扫描→摘要→飞书表格→飞书推送→Obsidian） |
| `--dry-run` | 预览模式：只扫描和摘要，不推送不保存 |
| `--skip-push` | 跳过飞书消息推送（Phase 4） |
| `--skip-save` | 跳过 Obsidian 保存（Phase 5） |
| `--cleanup` | 仅清理 90 天前的旧数据 |
| `--db PATH` | 指定 SQLite 数据库路径（默认 ~/.davylinks/state.db） |

### 退出码

| 退出码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1 | 有错误（查看日志或 stderr） |

## 分阶段执行

### Phase 1-2: 扫描 + 聚类
```bash
.venv/bin/python scripts/scan_articles.py > articles.json
```

### Phase 3: LLM 摘要
```bash
cat articles.json | .venv/bin/python scripts/summarize.py > summarized.json
```

### Phase 3.5: 飞书多维表格
```bash
cat summarized.json | .venv/bin/python scripts/feishu_bitable.py
```

### Phase 4: 飞书推送
```bash
cat summarized.json | .venv/bin/python scripts/push_feishu.py
```

### Phase 5: Obsidian 保存
```bash
cat summarized.json | .venv/bin/python scripts/save_obsidian.py
```

## 状态查询

```bash
.venv/bin/python scripts/state_db.py
```

## 本地校验

```bash
sh scripts/check.sh   # 编译检查 + 运行测试
```

## 调试

```bash
LOG_LEVEL=DEBUG .venv/bin/python scripts/pipeline.py
```
