# LLM API 格式速查

> 快速参考：各供应商的 API 格式差异。背景见 [domain/llm-landscape.md](../domain/llm-landscape.md)。

## 格式阵营

| 供应商 | API 格式 | 典型端点 |
|--------|----------|----------|
| Qwen | OpenAI 格式 | `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions` |
| MiniMax | OpenAI 格式 | `/v1/chat/completions` |
| DeepSeek | OpenAI 格式 | `https://api.deepseek.com/v1/chat/completions` |
| Kimi | **Anthropic 格式** | `https://api.moonshot.cn/v1/messages` |
| Zhipu | **Anthropic 格式** | `/v1/messages` |

## 代码中的区分方式

```python
# scripts/summarize.py
ANTHROPIC_PROVIDERS = {"kimi", "zhipu"}  # 白名单判断

# Anthropic 格式 → POST {base_url}/v1/messages
# OpenAI 格式    → POST {base_url}/chat/completions
```

**新增供应商时，第一件事是确认 API 格式**。配置错格式会直接 404。

## 请求体差异

### OpenAI 格式

```json
POST /v1/chat/completions
{
  "model": "qwen-plus",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 100
}
```

响应：`choices[0].message.content`

### Anthropic 格式

```json
POST /v1/messages
{
  "model": "moonshot-v1-8k",
  "messages": [{"role": "user", "content": "..."}],
  "max_tokens": 100
}
```

响应：`content[0].text`

认证头都是 `Authorization: Bearer <api_key>`（Anthropic 官方用 `x-api-key`，但国产兼容端点统一用 Bearer）。

## 摘要 Prompt（当前实现）

```
请用一句话（50 字以内）总结这篇文章的要点。

标题：{title}
来源：{source}
内容：{content 前 2000 字}
```

修改摘要风格 → 编辑 `scripts/summarize.py` 的 prompt 模板。

## 连通性测试

```bash
# OpenAI 格式（以 Qwen 为例）
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"test"}]}'
```
