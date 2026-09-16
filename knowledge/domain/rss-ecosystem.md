# RSS 生态现状

> 领域知识：中文科技资讯源的 RSS 可用性现状与替代方案。更新于 2026-09。

## 核心结论

**中文科技媒体的 RSS 正在消失。** 越来越多的站点关闭或弱化了 RSS 输出，DavyLinks 实测结果：

| 源 | RSS 状态 | 说明 |
|----|----------|------|
| 36氪 | ✅ 可用 | `https://36kr.com/feed`，稳定 |
| 少数派 sspai | ✅ 可用 | `https://sspai.com/feed`，稳定 |
| 量子位 | ✅ 可用 | `https://www.qbitai.com/feed`，稳定 |
| IT之家 | ✅ 可用 | `https://www.ithome.com/rss/`，稳定 |
| Hacker News | ✅ 可用 | `https://hnrss.org/frontpage`，第三方官方支持 |
| 机器之心 | ❌ 不可用 | 官方 RSS 已失效 |
| 虎嗅 | ❌ 不可用 | 官方 RSS 已失效 |
| InfoQ 中文 | ❌ 不可用 | 从未提供过全量 RSS |

## 微信公众号：没有 RSS，只有变通方案

微信公众号内容完全封闭，无任何官方 RSS。获取途径按可靠性排序：

1. **wewe-rss（自建，当前方案）** — 基于读书账号的方案，本地部署后提供 Atom feed：`http://localhost:4000/feeds/all.atom`。缺点：依赖微信读书账号额度，有被风控风险。
2. **RSSHub 公共实例** — `rsshub.app/wechat/mp/:id`。缺点：公共实例限流严重，微信路由经常失效。
3. **自建 RSSHub** — Docker 一键部署，比公共实例稳定，但微信路由本身依赖第三方逆向接口，仍不稳定。

## 替代抓取方案对比

| 方案 | 可靠性 | 维护成本 | 适用场景 |
|------|--------|----------|----------|
| 原生 RSS | 高 | 零 | 有 RSS 的站点，首选 |
| blogwatcher-cli | 高 | 低 | 自动发现 feed + 追踪已读状态 |
| wewe-rss | 中 | 中（需保持本地服务） | 微信公众号 |
| RSSHub | 中 | 中 | B站、播客等长尾源 |
| HTML 抓取 + CSS 选择器 | 低 | 高（站点改版即失效） | 最后手段 |

## 给DavLinks 的实操建议

- 新增源时优先验证原生 RSS 是否存在（浏览器直接访问 feed URL）
- RSS 失效的中文媒体（机器之心、虎嗅），考虑通过聚合源间接覆盖（量子位/36氪会转载其热点）
- 每次 wewe-rss 失效时，检查是否账号额度用尽，而非急于换方案
- feed URL 变更后，更新 `config/sources.json` 并在 `disabled_reason` 记录原因，保留配置便于日后恢复
