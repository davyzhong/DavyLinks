#!/usr/bin/env python3
"""DavyLinks Phase 3: 多LLM并行摘要 + 失败fallback

4个LLM并行处理TOP 5文章：
  - Qwen  (qwen3.5-plus)    — OpenAI格式，最稳
  - Kimi  (kimi-for-coding) — Anthropic格式
  - Zhipu (glm-5)           — Anthropic格式
  - MiniMax (M2.7)          — OpenAI格式

分配策略：round-robin + 失败自动fallback到下一个LLM
理论耗时：串行250s → 并行 ~50s
"""

import json
import sys
import os
import re
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Anthropic格式的provider（所有LLM都用Anthropic格式）
ANTHROPIC_PROVIDERS = {"kimi", "zhipu"}

# ============================================================
# 配置读取
# ============================================================

def get_all_llm_configs():
    """获取所有可用的LLM配置，按优先级排序返回列表"""
    config_path = os.path.expanduser("~/.config/llm-providers.yaml")
    if not os.path.exists(config_path):
        return _fallback_env_config()

    try:
        try:
            import yaml
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
        except ImportError:
            config = _parse_yaml_simple(config_path)

        # 提取 providers
        providers = config.get("providers", {})
        if not providers:
            for key, val in config.items():
                if isinstance(val, dict) and val.get("api_key") and val.get("base_url"):
                    providers[key] = val

        # 按优先级排序构建配置列表
        preferred_order = ["qwen", "kimi", "zhipu", "minimax"]
        configs = []

        for name in preferred_order:
            if name not in providers:
                continue
            conf = providers[name]
            if not conf.get("api_key") or not conf.get("base_url"):
                continue

            api_format = "anthropic" if name in ANTHROPIC_PROVIDERS else "openai"
            configs.append({
                "name": name,
                "api_key": str(conf["api_key"]),
                "base_url": str(conf["base_url"]),
                "model": str(conf.get("model", "gpt-3.5-turbo")),
                "format": api_format,
            })

        # 添加不在优先列表中的其他provider
        for name, conf in providers.items():
            if name in preferred_order:
                continue
            if not conf.get("api_key") or not conf.get("base_url"):
                continue
            configs.append({
                "name": name,
                "api_key": str(conf["api_key"]),
                "base_url": str(conf["base_url"]),
                "model": str(conf.get("model", "gpt-3.5-turbo")),
                "format": "openai",
            })

        return configs
    except Exception as e:
        print(f"[WARN] 读取LLM配置失败: {e}", file=sys.stderr)
        return _fallback_env_config()


def _fallback_env_config():
    """环境变量 fallback"""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return []
    return [{
        "name": "env",
        "api_key": api_key,
        "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "model": os.environ.get("OPENAI_MODEL", "gpt-4o-mini"),
        "format": "openai",
    }]


def _parse_yaml_simple(path):
    """简易 YAML 解析（不依赖 PyYAML）"""
    result = {}
    current_top = None
    current_mid = None

    with open(path, "r") as f:
        for line in f:
            stripped = line.rstrip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())

            # 顶级 key
            m = re.match(r'^(\w[^:]*):\s*$', stripped)
            if m and indent == 0:
                current_top = m.group(1).strip()
                current_mid = None
                if current_top not in result:
                    result[current_top] = {}
                continue

            # 二级 key: value
            m = re.match(r'^\s{2}(\w+):\s*(.+)$', stripped)
            if m and indent == 2 and current_top:
                key = m.group(1)
                val = m.group(2).strip().strip('"').strip("'")
                if isinstance(result.get(current_top), dict):
                    result[current_top][key] = val
                continue

            # 二级容器 key:
            m = re.match(r'^\s{2}(\w[^:]*):\s*$', stripped)
            if m and indent == 2 and current_top:
                current_mid = m.group(1).strip()
                if isinstance(result.get(current_top), dict):
                    result[current_top][current_mid] = {}
                continue

            # 三级 key: value
            m = re.match(r'^\s{4}(\w+):\s*(.+)$', stripped)
            if m and indent == 4 and current_top and current_mid:
                key = m.group(1)
                val = m.group(2).strip().strip('"').strip("'")
                if isinstance(result.get(current_top, {}).get(current_mid), dict):
                    result[current_top][current_mid][key] = val
                continue

    return result


# ============================================================
# LLM API 调用 — 两种格式
# ============================================================

def call_llm(config, prompt):
    """根据 format 调度到正确的 API"""
    if config.get("format") == "anthropic":
        return _call_anthropic(config, prompt)
    return _call_openai(config, prompt)


def _call_openai(config, prompt):
    """OpenAI 兼容 API (Qwen, MiniMax)"""
    base_url = config["base_url"].rstrip("/")
    # MiniMax base_url 本身就是完整 endpoint
    if "chatcompletion" in base_url or base_url.endswith("/chat/completions"):
        url = base_url
    else:
        url = f"{base_url}/chat/completions"

    payload = json.dumps({
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 300,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Authorization", f"Bearer {config['api_key']}")

    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()


def _call_anthropic(config, prompt):
    """Anthropic 兼容 API (Kimi, Zhipu)"""
    base_url = config["base_url"].rstrip("/")
    url = f"{base_url}/v1/messages"

    payload = json.dumps({
        "model": config["model"],
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 300,
    }).encode("utf-8")

    req = urllib.request.Request(url, data=payload, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("x-api-key", config["api_key"])
    req.add_header("anthropic-version", "2023-06-01")

    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        # Anthropic 响应: {"content": [{"type": "text", "text": "..."}]}
        if "content" in data and data["content"]:
            for block in data["content"]:
                if block.get("type") == "text":
                    return block["text"].strip()
        raise ValueError(f"意外的响应格式: {str(data)[:200]}")


# ============================================================
# 摘要逻辑
# ============================================================

SUMMARIZE_PROMPT = """请用一句话（50字以内）总结这篇文章的要点。

标题: {title}
来源: {source}
内容: {content}

直接输出总结文字，不要输出其他内容。"""


def summarize_one(article, llm_config):
    """对单篇文章生成摘要（可能抛异常，由调用方处理）"""
    content = article.get("description", article.get("content", ""))
    if not content:
        content = "(无正文内容，仅根据标题摘要)"
    elif len(content) > 2000:
        content = content[:2000] + "..."

    prompt = SUMMARIZE_PROMPT.format(
        title=article.get("title", ""),
        source=article.get("source", ""),
        content=content,
    )

    raw = call_llm(llm_config, prompt)
    article["summary"] = raw
    article["tags"] = []
    article["quality_rating"] = 3
    article["summarized_by"] = llm_config["name"]
    return article


def summarize_parallel(articles, llm_configs):
    """多LLM并行摘要 + 失败 fallback

    Round-robin 分配：art[0]→LLM[0], art[1]→LLM[1], ...
    某篇失败时，自动 fallback 到下一个 LLM 重试。
    """
    n_llm = len(llm_configs)

    def _try_with_fallback(idx, article):
        """尝试用指定 LLM 摘要，失败则 fallback 到下一个"""
        tried = set()
        current = idx % n_llm
        art = dict(article)  # 浅拷贝

        while current not in tried:
            tried.add(current)
            config = llm_configs[current]
            try:
                result = summarize_one(art, config)
                return idx, result, config["name"]
            except Exception as e:
                err_msg = str(e)[:80]
                print(f"    [fallback] #{idx+1} {config['name']} 失败: {err_msg}", file=sys.stderr)
                current = (current + 1) % n_llm

        # 所有 LLM 都失败
        art["summary"] = "(所有LLM摘要均失败)"
        art["tags"] = []
        art["quality_rating"] = 2
        art["summarized_by"] = "none"
        return idx, art, "none"

    # 并行执行
    results = [None] * len(articles)
    with ThreadPoolExecutor(max_workers=min(len(articles), n_llm)) as pool:
        futures = {}
        for i, article in enumerate(articles):
            f = pool.submit(_try_with_fallback, i, article)
            futures[f] = i

        for future in as_completed(futures):
            idx = futures[future]
            try:
                _, result, used_llm = future.result(timeout=120)
                results[idx] = result
                title = result.get("title", "?")[:40]
                print(f"    [{idx+1}/{len(articles)}] {title}... -> {used_llm} OK", file=sys.stderr)
            except Exception as e:
                print(f"    [{idx+1}] 超时或异常: {e}", file=sys.stderr)
                results[idx] = dict(articles[idx])
                results[idx]["summary"] = "(摘要超时)"
                results[idx]["tags"] = []
                results[idx]["quality_rating"] = 2
                results[idx]["summarized_by"] = "timeout"

    return results


def final_sort(articles):
    """最终排序: relevance + quality + cross_source"""
    for a in articles:
        base = a.get("relevance_score", 0)
        quality = a.get("quality_rating", 3)
        cross = a.get("cross_source_score", 0)
        a["final_score"] = base + quality * 2 + cross
    articles.sort(key=lambda x: x.get("final_score", 0), reverse=True)
    return articles


# ============================================================
# Main
# ============================================================

def main():
    if not sys.stdin.isatty():
        data = json.load(sys.stdin)
    else:
        print("[ERROR] 请通过管道输入JSON", file=sys.stderr)
        sys.exit(1)

    articles = data.get("articles", data if isinstance(data, list) else [])
    if not articles:
        print("[INFO] 没有文章需要摘要", file=sys.stderr)
        print(json.dumps({"articles": [], "top5": [], "other": []}))
        return

    llm_configs = get_all_llm_configs()
    if not llm_configs:
        print("[WARN] 未找到LLM配置，跳过摘要生成", file=sys.stderr)
        for a in articles:
            a["summary"] = "(未生成摘要)"
            a["tags"] = []
            a["quality_rating"] = 3
    else:
        max_summarize = 5
        to_summarize = articles[:max_summarize]
        skip = articles[max_summarize:]

        provider_names = ", ".join(f"{c['name']}({c['model']})" for c in llm_configs)
        print(f"[Phase 3] 多LLM并行摘要: {provider_names}", file=sys.stderr)
        print(f"  摘要 {len(to_summarize)} 篇，跳过 {len(skip)} 篇", file=sys.stderr)

        summarized = summarize_parallel(to_summarize, llm_configs)

        for i, s in enumerate(summarized):
            if s is not None:
                articles[i] = s

        for a in skip:
            a["summary"] = "(摘要已跳过)"
            a["tags"] = []
            a["quality_rating"] = 2

    sorted_articles = final_sort(articles)
    top5 = sorted_articles[:5]
    other = sorted_articles[5:15]

    output = {
        "articles": sorted_articles,
        "top5": top5,
        "other": other,
        "total": len(sorted_articles),
    }

    print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
