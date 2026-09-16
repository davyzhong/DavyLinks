# ADR-008: 双 LLM API 格式适配

**状态**: ✅ 已实施 (v1.0, 2026-05，修复于 v1.0 当日)

## 背景

国产 LLM 的 API 格式分裂为两个阵营（详见 [domain/llm-landscape.md](../domain/llm-landscape.md)）：

- **OpenAI 格式**（`/chat/completions`）：Qwen、MiniMax、DeepSeek
- **Anthropic 格式**（`/v1/messages`）：Kimi、Zhipu

多路 fallback（[ADR-004](004-multi-llm-fallback.md)）必须能对两种格式发请求、解析两种响应。

## 决策

**白名单判断 + 双格式适配**，不做抽象层：

```python
# scripts/summarize.py
ANTHROPIC_PROVIDERS = {"kimi", "zhipu"}

def call_llm(provider, prompt):
    if provider in ANTHROPIC_PROVIDERS:
        # POST {base_url}/v1/messages  → content[0].text
    else:
        # POST {base_url}/chat/completions  → choices[0].message.content
```

**为什么不引入 litellm 等统一库**：摘要管线只用到"单轮对话 + 文本响应"这一个能力面，统一库是重依赖换小收益，且出问题时多一层排查成本。白名单 3 行代码解决 95% 的差异。

## 历史教训

v1.0 上线当天就踩过此坑：初期实现把所有供应商按 OpenAI 格式调用，Kimi/Zhipu 全部 404。当天修复为白名单方案。

## 后果

- ✅ 零依赖，逻辑一目了然
- ⚠️ **新增供应商时必须人工确认格式**——这是唯一的维护点，配置错直接 404
- ⚠️ 若未来需要多轮对话/工具调用等能力，白名单方案会膨胀，届时再评估统一库
