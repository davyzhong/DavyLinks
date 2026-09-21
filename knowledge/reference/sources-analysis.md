# 信息源速查表

> 快速参考：当前配置的所有信息源及状态。深度分析见 [domain/tech-news-landscape.md](../domain/tech-news-landscape.md)。

## 活跃源

| 源 | Feed URL | 权重 | 分类 |
|----|----------|------|------|
| 36氪 | `https://36kr.com/feed` | 5 | 科技创投 |
| 少数派 | `https://sspai.com/feed` | 4 | 效率工具 |
| 量子位 | `https://www.qbitai.com/feed` | 5 | AI资讯 |
| IT之家 | `https://www.ithome.com/rss/` | 3 | 科技资讯 |
| Hacker News | `https://hnrss.org/frontpage` | 3 | 技术 |
| 微信公众号（聚合） | `http://localhost:4000/feeds/all.atom`（wewe-rss） | — | 多源 |

## 禁用源（保留配置便于恢复）

| 源 | Feed URL | 禁用原因 |
|----|----------|----------|
| 机器之心 | `https://www.jiqizhixin.com/rss` | RSS feed 不可用 |
| InfoQ中文 | `https://www.infoq.cn/feed` | 无可用 feed |
| 虎嗅 | `https://www.huxiu.com/rss/0.xml` | RSS feed 不可用 |

## 新增源操作步骤

1. 验证 feed URL 可访问（浏览器直接打开）
2. 编辑 `config/sources.json`，添加到 `sources` 数组
3. 设置合理权重：核心源 5，垂类源 4，泛化源 3
4. 下次运行管线自动生效，无需改代码

## 状态标记约定

```json
{
  "disabled": true,
  "disabled_reason": "RSS feed 不可用"
}
```

禁用源**不从配置中删除**，保留记录以便日后恢复或换方案。
