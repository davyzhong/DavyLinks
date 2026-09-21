# 飞书配置指南

> 飞书开放平台凭证的获取步骤，以及飞书相关故障的排查方法。

## 获取飞书凭证

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建企业自建应用
3. 获取 App ID 和 App Secret
4. 添加机器人权限，获取 Webhook URL
5. 创建多维表格，从 URL 获取 app_token 和 table_id

获取后填入 `config/secrets.yaml`：

```yaml
feishu:
  app_id: "cli_xxx"
  app_secret: "xxx"
  webhook_url: "https://open.feishu.cn/..."
  bitable:
    app_token: "xxx"
    table_id: "tblxxx"
```

## 故障排查

### 飞书推送失败

```bash
# 1. 检查环境变量
echo $FEISHU_APP_ID
echo $FEISHU_APP_SECRET

# 2. 测试连接
.venv/bin/python scripts/feishu_bitable.py --test
```

### feishu_bitable.py 问题

- **Token 获取失败 (401/403)**: 检查 `app_id`/`app_secret` 是否正确，确认应用已发布
- **多维表格权限错误**: 确认飞书应用已添加为多维表格的协作者（编辑权限）
- **字段不匹配**: 检查飞书表格字段名与代码中一致（日期、标题、来源、摘要、热度评分、链接等）

## 相关资源

- [飞书开放平台文档](https://open.feishu.cn/document/)
