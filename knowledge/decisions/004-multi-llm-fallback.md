# ADR-004: 多路 LLM Fallback

**状态**: ✅ 已实施 (v1.0, 2026-05)

## 背景

摘要管线每天要调用 LLM 数十次。单一供应商意味着：它限流或宕机时，当天摘要产出直接失败。国产 LLM API（Qwen/Kimi/Zhipu/MiniMax）全年各有几次不可用窗口，单点依赖不可接受。

## 备选方案

| 方案 | 评价 |
|------|------|
| 重试 + 退避 | 解决瞬时故障，解决不了持续宕机 |
| 单一供应商 + 备用 key | 同一供应商的故障是共因，无效 |
| **多供应商 + 自动 fallback** | 异构故障域，真正冗余 |

## 决策

**4 路供应商（Qwen / Kimi / Zhipu / MiniMax）+ Round-robin 分配 + 失败自动切换**：

1. TOP 5 文章轮询分配给 4 个供应商（并行执行，ThreadPoolExecutor）
2. 单篇摘要失败 → 自动 fallback 到下一个供应商
3. 理论耗时约 50s（4 路并行），对比串行 250s

供应商配置来自 `config_loader.get_llm_provider_configs()`，纯配置驱动——新增供应商只需改 `config/secrets.yaml`，不改代码。

## 后果

- ✅ 任何一家故障不阻塞当天管线
- ✅ 并行使摘要阶段耗时降为 1/5
- ⚠️ 不同供应商摘要风格略有差异（可接受：都是 50 字一句话摘要）
- ⚠️ API 格式不统一，需要双格式适配 → 详见 [ADR-008](008-dual-llm-api-format.md)
