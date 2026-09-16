# LLM 选型格局（中文场景）

> 领域知识：DavyLinks 摘要管线所用的国产 LLM 对比与选型逻辑。更新于 2026-09。

## 当前接入的 4 家供应商

| 供应商 | API 格式 | 模型 | 定位 | 备注 |
|--------|----------|------|------|------|
| Qwen 通义千问 | OpenAI 格式 | qwen-plus | 主力摘要 | 阿里云 dashscope，性价比高 |
| Kimi 月之暗面 | **Anthropic 格式** | moonshot-v1-8k | 摘要 + fallback | 长文本理解强 |
| Zhipu 智谱 | **Anthropic 格式** | glm 系列 | fallback | 清华系，国内合规性好 |
| MiniMax | OpenAI 格式 | abab 系列 | fallback | 多模态见长 |

## 关键事实：API 格式不统一

国产 LLM 阵营分裂为两种 API 格式：

- **OpenAI 格式**（`/v1/chat/completions`）：Qwen、MiniMax、DeepSeek
- **Anthropic 格式**（`/v1/messages`）：Kimi、Zhipu

DavyLinks 用 `ANTHROPIC_PROVIDERS = {"kimi", "zhipu"}` 白名单区分。**新增供应商时必须先确认其 API 格式**，配置错了会直接 404。

## 为什么 4 路 Fallback

单点依赖 LLM API 有三类风险：

1. **限流**：免费/低价档位 QPS 限制严格，摘要批量请求容易触发
2. **故障**：国产 API 全年总有几次不可用窗口
3. **下线**：模型迭代快，老模型可能被下架（如 moonshot-v1-8k 这类命名可能被新版本替代）

Round-robin 分配 + 失败自动 fallback 的设计，使任何一家挂掉都不阻塞管线。

## 摘要场景的选型考量

DavyLinks 的摘要任务特点：输入短（前 2000 字）、输出短（50 字以内）、批量（每天 20-80 篇）、中文。

这意味着：
- **不需要最强模型**：摘要不是推理任务，qwen-plus 档位足够，旗舰模型是浪费
- **8k 上下文够用**：输入被截断到 2000 字，无需 128k 长上下文
- **成本敏感**：每天几十次调用，各厂差距不大，稳定性比单价重要
- **中文质量**：国产模型中文摘要质量普遍好于 GPT 系

## 配置位置

```yaml
# config/secrets.yaml
llm_providers:
  qwen:
    api_key: "sk-xxx"
    base_url: "https://dashscope.aliyuncs.com/compatible-mode/v1"
    model: "qwen-plus"
```

配置加载由 `config_loader.get_llm_provider_configs()` 统一处理，兼容旧位置 `~/.config/llm-providers.yaml`。
