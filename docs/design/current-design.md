# DavyLinks 当前设计

> 与代码同步的权威设计文档。历史设计参见 [original-requirement.md](original-requirement.md)。

## 设计目标

构建自动化科技资讯聚合管线，每天从多个公开信息源抓取内容，经 AI 摘要排序后推送每日精华到飞书并沉淀到 Obsidian。

## 核心设计原则

1. **不可变数据流**: 各阶段函数返回新 dict，不修改输入数据
2. **延迟配置加载**: 首次调用时初始化，不在 import 时读取 secrets
3. **多路 LLM Fallback**: 4 个 LLM provider 并行 + 失败自动切换
4. **仅 TOP 5 入 Obsidian**: 避免知识库膨胀
5. **SQLite 状态管理**: URL 去重 + 断点续传 + 90 天自动清理

## 六阶段管线

详见 [architecture/pipeline.md](../architecture/pipeline.md)

## 关键参数

| 参数 | 值 | 说明 |
|------|---|------|
| 聚类阈值 | chinese_overlap >= 0.35 | 中文二元组重叠度 |
| 相关性阈值 | score >= 8 | 关键词过滤最低分 |
| TOP N | 5 | 每日精华数量 |
| 数据保留 | 90 天 | SQLite 自动清理 |
| 聚类桶上限 | max_bucket_size = 50 | 跳过过大的泛化桶 |

## 技术栈

- Python 3.9+
- SQLite（状态管理）
- blogwatcher-cli（RSS 扫描）
- wewe-rss（微信公众号 Atom feed）
- 飞书开放平台（多维表格 + 群消息）
- Obsidian（知识沉淀）

## 与 Davybase 的关系

| 维度 | Davybase | DavyLinks |
|------|----------|-----------|
| 数据源 | get 笔记 API（私有） | 公开 RSS/网站（开放） |
| 定位 | 私有笔记管理 | 外部信息聚合 |
| 知识库 | 同一 Obsidian vault | 同一 Obsidian vault |
| 通知 | notify.py | 复用 Davybase notify.py 或独立 webhook |
