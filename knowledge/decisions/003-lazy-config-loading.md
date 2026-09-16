# ADR-003: 延迟配置加载

**状态**: ✅ 已实施 (v2.0, 2026-06)

## 背景

v1.0 在**模块顶层**加载配置：

```python
# 旧代码（import 时立即执行）
_feishu_config = load_feishu_config()
FEISHU_APP_ID = _feishu_config["app_id"]  # 配置缺失 → import 即崩
```

三个问题：

1. `import feishu_bitable` 就读取 secrets.yaml——测试环境没配置就直接崩
2. 凭证在进程启动时即进入内存，测试时难以隔离
3. 单元测试必须 mock 模块级变量，侵入性强

## 决策

**延迟加载**：配置在首次调用时初始化，import 时不读任何 secrets。

```python
_config = None
def _get_config():
    global _config
    if _config is None:
        _config = config_loader.get_feishu_config()
    return _config
```

已应用到三个模块：`feishu_bitable.py`、`push_feishu.py`、`save_obsidian.py`（均验证过函数内首次调用，非 import 时）。

## 后果

- ✅ import 无副作用：`import feishu_bitable` 永远不崩
- ✅ 配置缺失只在真正用到时报错，错误信息指向具体功能
- ✅ 测试只需 mock `_get_config()` 函数，不用动模块状态
- ⚠️ 全局变量 `_config` 缓存后不会刷新——进程内配置变更需重启（对本场景无影响：管线是短生命周期进程）
