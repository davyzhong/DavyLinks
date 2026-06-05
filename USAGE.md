# DavyLinks 使用指南

## 安装

### 1. 环境要求

- Python 3.9+
- venv / pip 包管理器

### 2. 安装依赖

```bash
cd /path/to/DavyLinks
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

### 3. 配置密钥

```bash
# 创建配置目录（备用位置）
mkdir -p ~/.davylinks

# 复制配置模板到项目目录（推荐位置）
cp config/secrets.example.yaml config/secrets.yaml

# 或复制到用户目录（备用位置）
# cp config/secrets.example.yaml ~/.davylinks/secrets.yaml

# 编辑配置（填入真实凭证）
vim config/secrets.yaml
```

### 4. 密钥配置说明

```yaml
# 飞书开放平台凭证
feishu:
  app_id: "cli_xxx"
  app_secret: "xxx"
  webhook_url: "https://open.feishu.cn/..."
  bitable:
    app_token: "xxx"
    table_id: "tblxxx"

# LLM Provider 配置
llm_providers:
  qwen:
    api_key: "sk-xxx"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: "qwen-plus"
  kimi:
    api_key: "xxx"
    base_url: "https://api.moonshot.cn/v1"
    model: "moonshot-v1-8k"

# Obsidian 配置
obsidian:
  vault_path: "/Users/qiming/ObsidianWiki"

# 可选：复用 Davybase 通知脚本
davybase:
  notify_path: "/path/to/davybase/scripts/notify.py"
  secrets_path: "/path/to/davybase/secrets.yaml"
```

### 5. 获取飞书凭证

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret
4. 添加机器人权限，获取 Webhook URL
5. 创建多维表格，从 URL 获取 app_token 和 table_id

### 6. 配置信息源

编辑 `config/sources.json`：

```json
{
  "sources": [
    {
      "name": "36 氪",
      "url": "https://36kr.com/feed",
      "category": "科技创投",
      "weight": 5,
      "keywords": ["AI", "大模型", "创业"]
    }
  ],
  "global_keywords": ["AI", "LLM", "开源"]
}
```

**字段说明**:
- `weight` (1-5): 来源权重，5=核心必读
- `category`: 用于分类
- `keywords`: 该来源专属关键词

## 运行

### 基本用法

```bash
# 执行完整流程
.venv/bin/python scripts/pipeline.py

# 预览模式（不推送、不保存）
.venv/bin/python scripts/pipeline.py --dry-run

# 跳过飞书推送
.venv/bin/python scripts/pipeline.py --skip-push

# 跳过 Obsidian 保存
.venv/bin/python scripts/pipeline.py --skip-save

# 仅清理 90 天前旧数据
.venv/bin/python scripts/pipeline.py --cleanup
```

### 独立运行各阶段

```bash
# Phase 1-2: 扫描 + 聚类
.venv/bin/python scripts/scan_articles.py > articles.json

# Phase 3: 摘要
cat articles.json | .venv/bin/python scripts/summarize.py > summarized.json

# Phase 3.5: 飞书多维表格
cat summarized.json | .venv/bin/python scripts/feishu_bitable.py

# Phase 4: 飞书消息推送
cat summarized.json | .venv/bin/python scripts/push_feishu.py

# Phase 5: Obsidian 保存
cat summarized.json | .venv/bin/python scripts/save_obsidian.py
```

**注意**: blogwatcher 的正确命令是 `blogwatcher-cli articles`（不是 `blogwatcher scan`）。

### 查看状态

```bash
# 查看运行统计
.venv/bin/python scripts/state_db.py

# 查看日志
LOG_LEVEL=DEBUG .venv/bin/python scripts/pipeline.py
```

### 本地校验

```bash
sh scripts/check.sh
```

## 测试

项目包含 19 个测试用例：

```bash
# 运行全部测试
.venv/bin/python -m pytest tests/ -v

# 运行特定模块
.venv/bin/python -m pytest tests/test_immutability.py -v

# 带覆盖率
.venv/bin/python -m pytest tests/ --cov=scripts --cov-report=term-missing
```

测试覆盖：
- 配置加载优先级和覆盖逻辑
- 管线编排和错误计数
- 话题聚类算法正确性
- 数据库操作（批量插入、参数化查询）
- 不可变性保证（验证函数不修改输入数据）

## 配置参考

### 配置加载优先级

1. **环境变量** (最高优先级) — 见下表
2. **config/secrets.yaml** (推荐主位置) — 项目目录下
3. **~/.davylinks/secrets.yaml** (备用位置) — 用户目录下

所有配置通过 `scripts/config_loader.py` 统一加载，各模块延迟读取（首次调用时初始化，不在 import 时读取 secrets）。

### 环境变量

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `FEISHU_APP_ID` | 飞书 App ID | `cli_xxx` |
| `FEISHU_APP_SECRET` | 飞书 App Secret | `xxx` |
| `FEISHU_WEBHOOK_URL` | 飞书机器人 Webhook | `https://...` |
| `FEISHU_BITABLE_TOKEN` | 多维表格 Token | `bascnxxx` |
| `FEISHU_TABLE_ID` | 数据表 ID | `tblxxx` |
| `LOG_LEVEL` | 日志级别 | `DEBUG`, `INFO`, `WARNING` |
| `OBSIDIAN_VAULT_PATH` | Obsidian 仓库路径 | `/path/to/vault` |
| `DAVYBASE_NOTIFY_PATH` | 可选 Davybase 通知脚本 | `/path/to/notify.py` |
| `DAVYBASE_SECRETS_PATH` | 可选 Davybase 配置 | `/path/to/secrets.yaml` |

### 日志级别

```bash
# 输出详细调试信息
export LOG_LEVEL=DEBUG
.venv/bin/python scripts/pipeline.py

# 仅输出警告和错误
export LOG_LEVEL=WARNING
.venv/bin/python scripts/pipeline.py
```

## 定时任务

### 使用 cron

```bash
# 编辑 crontab
crontab -e

# 添加每日任务（早上 8 点）
0 8 * * * cd /path/to/DavyLinks && .venv/bin/python scripts/pipeline.py >> ~/.davylinks/cron.log 2>&1
```

### 使用 Hermes Agent

创建 skill 配置文件 `skills/davylinks-pipeline.md`，设置 cron 触发。

## 故障排查

### 飞书推送失败

```bash
# 1. 检查环境变量
echo $FEISHU_APP_ID
echo $FEISHU_APP_SECRET

# 2. 测试连接
.venv/bin/python scripts/feishu_bitable.py --test
```

### LLM 摘要失败

```bash
# 1. 检查 LLM 配置
sed -n '/llm_providers:/,$p' config/secrets.yaml

# 2. 测试 API 连接
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer *** " \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"test"}]}'
```

### feishu_bitable.py 问题

- **Token 获取失败 (401/403)**: 检查 `app_id`/`app_secret` 是否正确，确认应用已发布
- **多维表格权限错误**: 确认飞书应用已添加为多维表格的协作者（编辑权限）
- **字段不匹配**: 检查飞书表格字段名与代码中一致（日期、标题、来源、摘要、热度评分、链接等）

### 聚类效果不佳

调整 `scripts/scan_articles.py` 中的阈值：

```python
# 默认 0.35，降低可增加聚类敏感度
if chinese_overlap(title1, title2) >= 0.30:  # 改为 0.30
    return True
```

## 最佳实践

### 1. 信息源选择

- 优先选择有原生 RSS 的源（稳定性高）
- 权重设置：核心源 5 分，次要源 3 分
- 定期清理不活跃的源

### 2. 关键词调优

- 初始设置较宽泛的关键词
- 根据实际过滤结果调整
- 添加负面关键词（可选扩展）

### 3. 日志管理

```bash
# 定期清理日志
find ~/.davylinks -name "*.log" -mtime +30 -delete
```

### 4. 数据备份

```bash
# 备份 SQLite 状态库
cp ~/.davylinks/state.db ~/.davylinks/state.db.backup.$(date +%F)
```

## 常见问题

**Q: 每天处理多少篇文章合适？**

A: 建议 20-80 篇。太多说明关键词太宽泛，太少说明来源不足。

**Q: 如何跳过某篇文章？**

A: 在 `state_db.py` 中手动插入 URL 标记为已处理。

**Q: 如何修改摘要风格？**

A: 编辑 `scripts/summarize.py` 中的 `SUMMARIZE_PROMPT`。

**Q: 飞书表格满了怎么办？**

A: 飞书多维表格支持 10 万行，可用 `feishu_bitable.py` 的清理功能（待实现）。

## 相关资源

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [Blogwatcher CLI](https://github.com/blogwatcher/blogwatcher-cli)
- [Davybase 项目](https://github.com/your-repo/davybase)
