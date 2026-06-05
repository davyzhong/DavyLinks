# Davybase (DavyLinks)

**Python 3.9+** | 科技资讯聚合管线 | 飞书 + Obsidian 输出

## 快速命令

```bash
# 安装依赖
pip install -r requirements.txt

# 配置密钥 (首次运行)
cp config/secrets.example.yaml config/secrets.yaml
# 编辑 config/secrets.yaml 填入飞书凭证和 LLM API Key

# 运行完整管线
python scripts/pipeline.py

# 预览模式 (不推送、不保存)
python scripts/pipeline.py --dry-run

# 查看运行统计
python scripts/state_db.py
```

## 配置加载优先级

1. **环境变量** (最高) → `FEISHU_APP_ID`, `LOG_LEVEL` 等
2. **config/secrets.yaml** (推荐)
3. **~/.davylinks/secrets.yaml** (备用)

## 项目结构

```
DavyLinks/
├── scripts/
│   ├── pipeline.py          # 主入口 (五阶段编排)
│   ├── scan_articles.py     # Phase 1-2: 扫描 + 聚类 (O(n) 倒排索引)
│   ├── summarize.py         # Phase 3: LLM 并行摘要 (4 路 fallback)
│   ├── feishu_bitable.py    # Phase 4: 飞书推送
│   └── save_obsidian.py     # Phase 5: Obsidian 沉淀
├── config/
│   ├── sources.json         # 信息源 + 关键词配置
│   └── secrets.yaml         # 密钥 (不提交 git)
└── skills/
    └── davylinks-pipeline.md # Hermes skill
```

## 核心管线

```
RSS/Atom → 扫描去重 → 话题聚类 → AI 摘要 → 飞书/Obsidian
```

## 关键注意事项

- **blogwatcher-cli 命令**: 用 `blogwatcher-cli articles` (不是 `blogwatcher scan`)
- **LLM API 格式**: Kimi/Zhipu 用 Anthropic 格式，Qwen/MiniMax 用 OpenAI 格式
- **聚类阈值**: `chinese_overlap >= 0.35`，调低可增加敏感度
- **飞书权限**: 应用需添加为多维表格协作者 (编辑权限)
- **状态库位置**: `~/.davylinks/state.db` (90 天自动清理)

## 故障排查

```bash
# 测试飞书连接
python scripts/feishu_bitable.py --test

# 调试模式
LOG_LEVEL=DEBUG python scripts/pipeline.py

# 分阶段执行 (调试用)
python scripts/scan_articles.py > articles.json
cat articles.json | python scripts/summarize.py > summarized.json
```

## 验证命令

```bash
python scripts/pipeline.py --help    # 查看命令行选项
python -c "import yaml; print('OK')"  # 验证 YAML 依赖
```
