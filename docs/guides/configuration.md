# 配置详解

> DavyLinks 的密钥配置、信息源配置与配置加载机制的完整参考。

## 密钥配置说明

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

完整配置模板：

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

**注意**: 飞书凭证的获取步骤见 [feishu-setup.md](feishu-setup.md)；Obsidian 路径配置详见 [obsidian-setup.md](obsidian-setup.md)。

## 配置信息源

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
- `global_keywords`: 全局关键词，对所有来源生效

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
