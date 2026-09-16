# 故障排查手册

> 常见问题的诊断与修复方法，以及日常使用的最佳实践。

## 故障排查

### 飞书推送失败

```bash
# 1. 检查环境变量
echo $FEISHU_APP_ID
echo $FEISHU_APP_SECRET

# 2. 测试连接
.venv/bin/python scripts/feishu_bitable.py --test
```

更多飞书相关问题见 [feishu-setup.md](feishu-setup.md)。

### LLM 摘要失败

```bash
# 1. 检查 LLM 配置
sed -n '/llm_providers:/,$p' config/secrets.yaml

# 2. 测试 API 连接
curl -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
  -H "Authorization: Bearer *** " \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen-plus","messages":[{"role":"user","content":"test"}]}'
```

### feishu_bitable.py 问题

- **Token 获取失败 (401/403)**: 检查 `app_id`/`app_secret` 是否正确，确认应用已发布
- **多维表格权限错误**: 确认飞书应用已添加为多维表格的协作者（编辑权限）
- **字段不匹配**: 检查飞书表格字段名与代码中一致（日期、标题、来源、摘要、热度评分、链接等）

### 聚类效果不佳

调整 `scripts/scan_articles.py` 中的阈值：

```python
# 默认 0.35，降低可增加聚类敏感度
if chinese_overlap(title1, title2) >= 0.30:  # 改为 0.30
    return True
```

## 最佳实践

### 1. 信息源选择

- 优先选择有原生 RSS 的源（稳定性高）
- 权重设置：核心源 5 分，次要源 3 分
- 定期清理不活跃的源

### 2. 关键词调优

- 初始设置较宽泛的关键词
- 根据实际过滤结果调整
- 添加负面关键词（可选扩展）

### 3. 日志管理

```bash
# 定期清理日志
find ~/.davylinks -name "*.log" -mtime +30 -delete
```

### 4. 数据备份

```bash
# 备份 SQLite 状态库
cp ~/.davylinks/state.db ~/.davylinks/state.db.backup.$(date +%F)
```

## 常见问题 FAQ

**Q: 每天处理多少篇文章合适？**

A: 建议 20-80 篇。太多说明关键词太宽泛，太少说明来源不足。

**Q: 如何跳过某篇文章？**

A: 在 `state_db.py` 中手动插入 URL 标记为已处理。

**Q: 如何修改摘要风格？**

A: 编辑 `scripts/summarize.py` 中的 `SUMMARIZE_PROMPT`。

**Q: 飞书表格满了怎么办？**

A: 飞书多维表格支持 10 万行，可用 `feishu_bitable.py` 的清理功能（待实现）。

## 相关资源

- [飞书开放平台文档](https://open.feishu.cn/document/)
- [Blogwatcher CLI](https://github.com/blogwatcher/blogwatcher-cli)
- [Davybase 项目](https://github.com/your-repo/davybase)
