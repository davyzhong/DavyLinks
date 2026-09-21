# 飞书 API 速查

> 快速参考：DavyLinks 用到的飞书 API 端点与认证。背景与坑见 [domain/feishu-platform.md](../domain/feishu-platform.md)。

## 认证：tenant_access_token

```bash
POST https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
{
  "app_id": "cli_xxx",
  "app_secret": "xxx"
}
```

- 有效期约 2 小时，需缓存复用
- 获取失败 (401/403)：检查 app_id/app_secret、应用是否已发布

## 多维表格写入

```bash
POST https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records
Authorization: Bearer {tenant_access_token}
{
  "fields": {
    "标题": "文章标题",
    "链接": {"link": "https://...", "text": "文章标题"},
    "热度评分": 87.5
  }
}
```

- 批量端点：`.../records/batch_create`，每批最多 **500 条**
- Date 字段：毫秒时间戳
- URL 字段：`{"link": url, "text": display_text}` 对象格式
- Checkbox 字段：布尔值

## 权限检查清单（推送失败时按序排查）

1. ✅ 应用开通了 `bitable:app` API 权限 scope
2. ✅ **应用已添加为多维表格协作者（编辑权限）** —— 最常漏
3. ✅ 表格字段名与代码完全一致
4. ✅ app_token 和 table_id 从表格 URL 中正确提取

## 连接测试

```bash
.venv/bin/python scripts/feishu_bitable.py --test
```

## Webhook 推送（Phase 4 fallback）

自定义机器人 webhook 无需 app 凭证，直接 POST：

```json
POST {webhook_url}
{
  "msg_type": "interactive",
  "card": {
    "header": {"template": "green", "title": {"tag": "plain_text", "content": "每日精华 2026-09-12"}},
    "elements": [{"tag": "markdown", "content": "..."}]
  }
}
```

DavyLinks 优先走 Davybase notify.py（已验证的 Card 实现），webhook 是 fallback。
