# 飞书开放平台能力与坑

> 领域知识：DavyLinks 用到的飞书 API 能力、权限模型和实践坑。更新于 2026-09。

## DavyLinks 用到的两类能力

### 1. 多维表格 Bitable（Phase 3.5）

用于保留**完整的**每日文章记录（不只 TOP 5），供回溯检索。

- 写入 API：`POST /open-apis/bitable/v1/apps/:app_token/tables/:table_id/records`
- 批量写入：每批最多 **500 条**（DavyLinks 每天写入 20-80 条，一批即可）
- 失败降级：批量失败时逐条写入，输出 `{"bitable_ok": N, "bitable_fail": M}`

### 2. 群消息推送（Phase 4）

两条路径，优先级：

1. **Davybase notify.py**（优先）：复用已验证的 Interactive Card 实现
2. **直接 Webhook**（fallback）：自定义机器人 webhook，无需 app 凭证

## 权限模型：最大的坑

飞书应用的权限体系有两个独立维度，缺一不可：

1. **API 权限 scope**：在开放平台为应用开通 `bitable:app` 等权限
2. **资源协作者**：**必须把应用添加为具体多维表格的协作者（编辑权限）**

只做第 1 步会得到 403，这是最常踩的坑。参见 [guides/feishu-setup.md](../../docs/guides/feishu-setup.md)。

## 认证机制

- `tenant_access_token`：应用身份凭证，有效期约 2 小时，需要自行缓存和刷新
- DavyLinks 在 `feishu_bitable.py` 中实现 token 获取逻辑（曾修复过一次获取逻辑 bug）

## 多维表格容量

- 单表上限约 10 万行记录
- DavyLinks 按天写 20-80 行，约 3-10 年才会触顶，暂不需要清理功能
- 字段名必须与代码中一致（日期、标题、来源、摘要、热度评分、链接等），改名即失败

## 数据表字段（当前 schema）

| 字段 | 类型 | 说明 |
|------|------|------|
| 日期 | Date | 毫秒时间戳 |
| 标题 | Text | |
| 来源 | Text | |
| 来源列表 | Text | 多源顿号分隔 |
| 来源数量 | Number | |
| 分类 | Text | |
| 摘要 | Text | AI 摘要 |
| 热度评分 | Number | final_score |
| 是否多源交叉 | Checkbox | |
| 链接 | URL | 超链接格式 |

## 相关速查

API 细节见 [reference/feishu-api-cheatsheet.md](../reference/feishu-api-cheatsheet.md)。
