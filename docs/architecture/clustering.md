# 聚类与筛选算法

> 本文档描述 Phase 1-2（`scripts/scan_articles.py`）中的关键词过滤评分算法与话题聚类算法，以及倒排索引聚类的设计决策。
> 该阶段的整体职责、数据来源与输出格式见 [pipeline.md](pipeline.md)；聚类相关的性能对比见 [data-flow.md](data-flow.md)。

## 关键词过滤评分算法

```
score = source_weight × 2
      + title_matches × 3
      + content_matches × 1
      + recency_bonus (24h:+5, 48h:+3, 72h:+1)
```

阈值：score >= 8

## 话题聚类算法

- **Phase 1**: 预计算每篇文章的实体名（英文词汇）和中文二元组
- **Phase 2**: 构建两个倒排索引（实体索引 + 二元组索引）
- **Phase 3**: 从索引生成候选对（跳过过大的泛化桶，`max_bucket_size=50`）
- **Phase 4**: Union-Find 聚类，只比较有候选对的文章
- **Phase 5**: 按根节点分组
- **Phase 6**: 构建话题对象，评分加成 `cross_bonus = min(source_count, 5) × 15`

## 复杂度分析

O(n) 建索引 → O(k²) 组内比较 (k<<n)，比较次数减少 80-95%

## 设计决策：为什么用倒排索引聚类？

**问题**: O(n²) 两两比较在文章数>100 时成为瓶颈

**方案**:
1. 提取标题中的英文实体名（DeepSeek、LLaMA 等）
2. 提取中文二元组
3. 构建两个倒排索引：`entity → [文章 ID]` 和 `bigram → [文章 ID]`
4. 只比较有共享实体或二元组的文章对（跳过过大的泛化桶）

**收益**: 比较次数减少 80-95%，聚类质量保持不变

## 调优

聚类敏感度由 `chinese_overlap` 阈值控制（默认 0.35），调低可增加敏感度。排查聚类不准的问题时优先检查该参数，详见 [overview.md](overview.md) 的常见问题表。
