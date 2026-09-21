# ADR-002: 不可变数据流

**状态**: ✅ 已实施 (v2.0, 2026-06)

## 背景

v1.0 的管线函数直接修改传入的 article dict（mutation 风格）：`filter_by_keywords` 就地加 `relevance_score` 字段，`summarize_one` 就地写摘要。导致的实际问题：

- 调试时难以追踪"这个字段是谁加的"
- 测试时必须 deep copy 输入，否则断言被污染
- 副作用不可预测，函数重试可能重复累积字段

## 备选方案

| 方案 | 评价 |
|------|------|
| 保持 mutation + 深拷贝防御 | 性能浪费，治标不治本 |
| 引入 dataclass/Pydantic 强类型 | 收益有限，对纯内部管线是过度设计 |
| **函数返回新 dict** | 与 Python 惯用法一致，改动小 |

## 决策

所有管线函数**返回新 dict，不修改输入**（`{**article, "summary": ...}` 模式）：

- `filter_by_keywords()` — 返回带 score 的新列表
- `summarize_one()` — 返回带摘要的新 dict
- `final_sort()` — 返回新列表
- 所有错误路径（LLM 失败、超时）也返回新 dict，不静默吞掉

由 `tests/test_immutability.py`（7 个测试）强制保证：验证输入对象在调用后保持原样。

## 后果

- ✅ 测试直接比较输入输出，无需拷贝
- ✅ 数据流清晰：每个阶段输入什么、输出什么一目了然
- ✅ 函数可安全重试（无副作用累积）
- ⚠️ 内存中多份 dict 副本——对每天 <100 篇的规模完全无感
