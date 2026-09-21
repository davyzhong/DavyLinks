# AI 摘要与排序

> 本文档描述 Phase 3（`scripts/summarize.py`）的 LLM 配置、分配策略、不可变数据流、摘要 Prompt 与最终排序，以及相关的核心设计决策。
> 该阶段在管线中的位置见 [pipeline.md](pipeline.md)；配置加载优先级见 [data-flow.md](data-flow.md)。

## LLM 配置

- Qwen (OpenAI 格式)
- Kimi (Anthropic 格式)
- Zhipu (Anthropic 格式)
- MiniMax (OpenAI 格式)
- 配置来源：`config_loader.get_llm_provider_configs()` → 环境变量 > `config/secrets.yaml` > `~/.davylinks/secrets.yaml`；保留 `~/.config/llm-providers.yaml` 作为兼容 fallback

## 分配策略

- Round-robin 分配 TOP 5 文章
- 失败自动 fallback 到下一个 LLM
- 并行执行（ThreadPoolExecutor），理论耗时 ~50s (vs 串行 250s)

## 不可变数据流

- `summarize_one()` 返回新 dict，不修改输入 article
- `final_sort()` 返回新列表，不修改输入
- 所有错误路径（LLM 失败、超时）也返回新 dict

### 设计决策：为什么用不可变数据流？

**问题**: 早期版本函数直接修改传入的 article dict，导致：
- 调试时难以追踪数据流
- 测试时需要 deep copy 输入数据
- 副作用难以预测

**方案**: 所有函数返回新 dict（使用 `{**article, ...}` 模式），不修改输入

**收益**:
- 测试简单：直接比较输入输出
- 调试容易：数据流清晰
- 无副作用：函数可安全重试

## 摘要 Prompt

```
请用一句话（50 字以内）总结这篇文章的要点。

标题：{title}
来源：{source}
内容：{content (前 2000 字)}
```

## 最终排序

```
final_score = relevance_score + quality_rating × 2 + cross_bonus
```

其中 `cross_bonus` 来自话题聚类阶段（`min(source_count, 5) × 15`），详见 [clustering.md](clustering.md)。

## 设计决策：为什么 LLM 用 Anthropic + OpenAI 双格式？

**原因**: 不同厂商 API 格式不统一
- Kimi、Zhipu → Anthropic 格式 (`/v1/messages`)
- Qwen、MiniMax → OpenAI 格式 (`/chat/completions`)

**解决**: `ANTHROPIC_PROVIDERS = {"kimi", "zhipu"}` 白名单判断

新增 LLM Provider 时，如果是 Anthropic 格式需要加入该白名单，扩展步骤见 [overview.md](overview.md) 的扩展性一节。
