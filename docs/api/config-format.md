# 配置文件格式

## config/secrets.yaml

飞书凭证、LLM API Key、Obsidian 路径等敏感配置。不提交 git。

### 完整模板

```yaml
# 飞书开放平台凭证
feishu:
  app_id: "cli_xxx"                # 飞书应用 App ID
  app_secret: "xxx"                # 飞书应用 App Secret
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
  bitable:
    app_token: "bascnxxx"          # 多维表格 App Token
    table_id: "tblxxx"             # 数据表 ID

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

### 配置加载优先级

1. **环境变量**（最高优先级）
2. **config/secrets.yaml**（推荐位置）
3. **~/.davylinks/secrets.yaml**（备用位置）

### 对应环境变量

| 配置路径 | 环境变量 |
|----------|----------|
| feishu.app_id | FEISHU_APP_ID |
| feishu.app_secret | FEISHU_APP_SECRET |
| feishu.webhook_url | FEISHU_WEBHOOK_URL |
| feishu.bitable.app_token | FEISHU_BITABLE_TOKEN |
| feishu.bitable.table_id | FEISHU_TABLE_ID |
| obsidian.vault_path | OBSIDIAN_VAULT_PATH |
| davybase.notify_path | DAVYBASE_NOTIFY_PATH |
| davybase.secrets_path | DAVYBASE_SECRETS_PATH |

## config/sources.json

信息源和关键词配置。

### 格式

```json
{
  "sources": [
    {
      "name": "36氪",
      "url": "https://36kr.com/feed",
      "category": "科技创投",
      "weight": 5,
      "keywords": ["AI", "大模型", "创业"],
      "enabled": true
    }
  ],
  "global_keywords": ["AI", "LLM", "开源"]
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | ✅ | 来源名称 |
| url | string | ✅ | RSS/Atom feed URL |
| category | string | ✅ | 分类（用于推送分组） |
| weight | int | ❌ | 权重 1-5，默认 3。5=核心必读 |
| keywords | array | ❌ | 该来源专属关键词（与 global_keywords 取并集） |
| enabled | bool | ❌ | 是否启用，默认 true |
