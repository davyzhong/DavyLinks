#!/usr/bin/env python3
"""DavyLinks Phase 1: 扫描信息源 + 话题聚类

从多个 RSS 源获取文章，去重、聚类为话题。

用法:
    python scan_articles.py | python summarize.py
"""

import json
import sys
import os
import re
import hashlib
import subprocess
from datetime import datetime, timezone
from collections import defaultdict

# 导入日志配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from logging_config import setup_logging

logger = setup_logging(__name__)

# ============================================================
# 配置读取
# ============================================================

def load_config():
    """加载信息源配置"""
    config_paths = [
        os.path.expanduser("~/.davylinks/sources.yaml"),
        os.path.join(os.path.dirname(__file__), "..", "config", "sources.json"),
    ]

    for path in config_paths:
        if os.path.exists(path):
            try:
                if path.endswith(".json"):
                    with open(path, "r") as f:
                        return json.load(f)
                else:
                    import yaml
                    with open(path, "r") as f:
                        return yaml.safe_load(f)
            except Exception as e:
                logger.warning("读取配置失败：%s", e)

    # 默认配置
    return {
        "sources": [
            {"name": "36Kr", "url": "https://36kr.com/feed", "weight": 5},
            {"name": "Hacker News", "url": "https://news.ycombinator.com/rss", "weight": 3},
        ],
        "global_keywords": ["AI", "LLM", "开源", "大模型"],
    }


# ============================================================
# 文章获取
# ============================================================

def fetch_wewe_articles():
    """从 wewe-rss Docker 容器获取微信公众号文章 (直接抓 Atom feed)"""
    import urllib.request
    import xml.etree.ElementTree as ET

    try:
        req = urllib.request.Request(
            "http://localhost:4000/feeds/all.atom",
            headers={"User-Agent": "DavyLinks/1.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = resp.read()

        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        articles = []

        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            updated_el = entry.find("atom:updated", ns)

            if title_el is None or link_el is None:
                continue

            url = link_el.get("href", "")
            title = (title_el.text or "").strip()
            published = updated_el.text[:10] if updated_el is not None and updated_el.text else ""

            articles.append({
                "title": title,
                "url": url,
                "source": "微信公众号",
                "published_at": published,
                "id": hash_url(url),
            })

        logger.info("[wewe-rss] 获取到 %d 篇公众号文章", len(articles))
        return articles
    except Exception as e:
        logger.warning("wewe-rss 抓取失败：%s", e)
        return []


def fetch_blogwatcher_articles():
    """从 blogwatcher-cli 获取未读 RSS 文章"""
    try:
        result = subprocess.run(
            ["blogwatcher-cli", "articles"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode != 0:
            logger.warning("blogwatcher-cli articles 返回非零：%s", result.stderr.strip())
            return []

        return parse_blogwatcher_output(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("blogwatcher-cli articles 超时 (30s)")
        return []
    except FileNotFoundError:
        logger.error("blogwatcher-cli 未安装")
        return []
    except Exception as e:
        logger.warning("获取文章列表失败：%s", e)
        return []


def parse_blogwatcher_output(text):
    """解析 blogwatcher-cli articles 的文本输出为文章列表

    格式示例:
      [489] [new] Title Here
           Blog: Hacker News
           URL: https://...
           Published: 2026-05-04
    """
    articles = []
    current = {}

    for line in text.split("\n"):
        line_stripped = line.strip()
        if not line_stripped:
            # 空行 = 一篇文章结束
            if current.get("title") and current.get("url"):
                current["id"] = hash_url(current["url"])
                articles.append(current)
            current = {}
            continue

        # 标题行: [id] [new] Title
        m = re.match(r'\[\d+\]\s+\[new\]\s+(.*)', line_stripped)
        if m:
            current["title"] = m.group(1).strip()
            continue

        # Blog: ...
        m = re.match(r'Blog:\s+(.*)', line_stripped)
        if m:
            current["source"] = m.group(1).strip()
            continue

        # URL: ...
        m = re.match(r'URL:\s+(.*)', line_stripped)
        if m:
            current["url"] = m.group(1).strip()
            continue

        # Published: ...
        m = re.match(r'Published:\s+(.*)', line_stripped)
        if m:
            current["published_at"] = m.group(1).strip()
            continue

    # 处理最后一篇（如果文件不以空行结尾）
    if current.get("title") and current.get("url"):
        current["id"] = hash_url(current["url"])
        articles.append(current)

    return articles


def hash_url(url):
    """为 URL 生成短 hash（64 bit，碰撞概率极低）"""
    return int(hashlib.md5(url.encode()).hexdigest()[:16], 16)


# ============================================================
# 话题聚类优化版本
# ============================================================

# 通用词汇，不算"特定实体"
GENERIC_TERMS = {
    'ai', 'llm', 'app', 'api', 'web', 'ios', 'android', 'pc', 'gpu', 'cpu',
    'gpt', 'ml', 'dl', 'nlp', 'cv', 'sdk', 'rss', 'sql', 'ui', 'ux',
    'saas', 'paas', 'vm', 'os', 'db', 'io', 'it', 'mr', 'vr', 'ar',
    'ceo', 'cto', 'ai agent', 'open', 'source', 'code', 'data',
}


def extract_entities(title):
    """从标题提取特定实体名（英文词汇，排除通用词）"""
    terms = set()
    for word in re.findall(r'[A-Za-z][A-Za-z0-9._-]*', title):
        w = word.lower()
        if len(w) >= 2 and w not in GENERIC_TERMS:
            terms.add(w)
    return terms


def cn_bigrams(title):
    """提取中文二元组"""
    chars = re.findall(r'[一-鿿]', title)
    return set(chars[i] + chars[i+1] for i in range(len(chars) - 1))


def chinese_overlap(title1, title2):
    """中文二元组包含度（短标题的 bigram 有多少出现在长标题中）"""
    bg1, bg2 = cn_bigrams(title1), cn_bigrams(title2)
    if not bg1 or not bg2:
        return 0
    shared = bg1 & bg2
    smaller = min(len(bg1), len(bg2))
    return len(shared) / smaller if smaller > 0 else 0


def should_cluster(title1, title2):
    """判断两篇文章是否属于同一话题"""
    # 1. 共享特定实体名（如 DeepSeek, V4, Huawei → 强信号）
    ents1 = extract_entities(title1)
    ents2 = extract_entities(title2)
    if ents1 & ents2:
        return True

    # 2. 中文文本高重叠（标题讲的是同一件事）
    if chinese_overlap(title1, title2) >= 0.35:
        return True

    return False


def build_entity_index(article_features):
    """构建实体名倒排索引（使用预计算的特征）

    Returns:
        dict: {entity: [article_indices]}
    """
    index = defaultdict(list)
    for i, features in enumerate(article_features):
        for entity in features.get("entities", set()):
            index[entity].append(i)
    return index


def build_bigram_index(article_features):
    """构建中文二元组倒排索引"""
    index = defaultdict(list)
    for i, features in enumerate(article_features):
        for bigram in features.get("bigrams", set()):
            index[bigram].append(i)
    return index


def _add_pairs_from_index(candidates, index, max_bucket_size=50):
    """从倒排索引中添加候选对，跳过过大的泛化桶。"""
    for indices in index.values():
        if len(indices) > max_bucket_size:
            continue
        for i in range(len(indices)):
            for j in range(i + 1, len(indices)):
                candidates.add((indices[i], indices[j]))


def build_candidate_pairs(articles, entity_index, bigram_index=None):
    """根据实体索引构建候选比较对

    Returns:
        set: {(i, j), ...} 需要比较的文章对索引
    """
    candidates = set()
    _add_pairs_from_index(candidates, entity_index)
    if bigram_index:
        _add_pairs_from_index(candidates, bigram_index)
    return candidates


def should_cluster_fast(entities1, entities2, bigrams1, bigrams2):
    """快速判断 - 使用预计算的实体和二元组

    Args:
        entities1, entities2: 预计算的实体集合
        bigrams1, bigrams2: 预计算的二元组集合
    """
    # 实体交集检查
    if entities1 & entities2:
        return True

    # 二元组重叠度
    if not bigrams1 or not bigrams2:
        return False

    shared = bigrams1 & bigrams2
    smaller = min(len(bigrams1), len(bigrams2))
    if smaller > 0 and len(shared) / smaller >= 0.35:
        return True

    return False


def cluster_by_topic(articles):
    """将相似文章聚类为话题，按交叉验证数评分

    优化版本：使用倒排索引减少比较次数

    核心逻辑:
    - 多个媒体同时报道同一话题 = 热点 → 排名靠前
    - 每个话题合并为一篇，展示所有来源
    - 评分 = max(相关度) + 来源数 × 15
    """
    n = len(articles)
    if n == 0:
        return []

    # ========== Phase 1: 预计算特征 ==========
    logger.debug("预计算 %d 篇文章的实体和二元组...", n)
    article_features = []
    for article in articles:
        title = article.get("title", "")
        article_features.append({
            "entities": extract_entities(title),
            "bigrams": cn_bigrams(title),
        })

    # ========== Phase 2: 构建倒排索引 ==========
    entity_index = build_entity_index(article_features)
    bigram_index = build_bigram_index(article_features)
    logger.debug("实体索引：%d 个实体，覆盖 %d 篇文章", len(entity_index), sum(len(v) for v in entity_index.values()))

    # ========== Phase 3: 获取候选对 ==========
    candidate_pairs = build_candidate_pairs(articles, entity_index, bigram_index)

    # 添加孤立文章的自循环（确保它们被单独分组）
    all_indexed = set()
    for indices in entity_index.values():
        all_indexed.update(indices)
    isolated = [i for i in range(n) if i not in all_indexed]

    logger.debug("候选比较对：%d 对 (原始 O(n²)=%d)", len(candidate_pairs), n * (n - 1) // 2)

    # ========== Phase 4: Union-Find 聚类 ==========
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]  # 路径压缩
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # 只在候选对内比较
    comparison_count = 0
    for i, j in candidate_pairs:
        comparison_count += 1
        if should_cluster_fast(
            article_features[i]["entities"],
            article_features[j]["entities"],
            article_features[i]["bigrams"],
            article_features[j]["bigrams"],
        ):
            union(i, j)

    # 处理孤立文章之间的中文重叠（可选，小数据量下可跳过）
    if len(isolated) > 1:
        for ii in range(len(isolated)):
            for jj in range(ii + 1, len(isolated)):
                i, j = isolated[ii], isolated[jj]
                comparison_count += 1
                if chinese_overlap(
                    articles[i].get("title", ""),
                    articles[j].get("title", "")
                ) >= 0.35:
                    union(i, j)

    logger.debug("实际比较次数：%d (节省 %.1f%%)", comparison_count,
                 100 * (1 - comparison_count / (n * (n - 1) // 2)) if n > 1 else 0)

    # ========== Phase 5: 按根节点分组 ==========
    groups = {}
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)

    # ========== Phase 6: 构建话题对象 ==========
    clusters = []
    for indices in groups.values():
        ca = [articles[i] for i in indices]
        # 去重来源（保持顺序）
        sources = list(dict.fromkeys(a.get("source", "") for a in ca))

        # 选代表标题：优先最高相关度，其次最长标题
        best = max(ca, key=lambda a: (a.get("relevance_score", 0), len(a.get("title", ""))))

        max_rel = max(a.get("relevance_score", 0) for a in ca)

        # 交叉验证加分：每多一个来源 +15（上限 5 个来源）
        cross_bonus = min(len(sources), 5) * 15

        cluster = {
            "title": best.get("title", ""),
            "source": best.get("source", ""),
            "source_list": sources,
            "source_count": len(sources),
            "url": best.get("url", ""),
            "urls": [a.get("url", "") for a in ca if a.get("url")],
            "category": best.get("category", ""),
            "description": best.get("description", ""),
            "published_at": max((a.get("published_at", "") for a in ca), default=""),
            "relevance_score": max_rel,
            "is_cluster": len(ca) > 1,
            "cluster_size": len(ca),
            "cross_source_score": cross_bonus,
            "final_score": max_rel + cross_bonus,
            "articles": ca,
        }
        clusters.append(cluster)

    # 按最终评分降序排序
    clusters.sort(key=lambda c: c.get("final_score", 0), reverse=True)

    return clusters


# ============================================================
# Main
# ============================================================

def main():
    logger.info("开始扫描信息源...")

    # 获取文章
    all_articles = []

    # 1. wewe-rss (微信公众号)
    wewe_articles = fetch_wewe_articles()
    all_articles.extend(wewe_articles)

    # 2. blogwatcher (RSS)
    bw_articles = fetch_blogwatcher_articles()
    all_articles.extend(bw_articles)

    logger.info("扫描到 %d 篇文章", len(all_articles))

    if not all_articles:
        logger.warning("没有获取到文章")
        print(json.dumps({"articles": [], "clusters": []}, ensure_ascii=False))
        return

    # 去重 (按 URL hash)
    seen = set()
    unique_articles = []
    for a in all_articles:
        url_hash = a.get("id") or hash_url(a.get("url", ""))
        if url_hash not in seen:
            seen.add(url_hash)
            unique_articles.append(a)

    logger.info("去重后 %d 篇", len(unique_articles))

    # 关键词过滤
    config = load_config()
    filtered = filter_by_keywords(unique_articles, config)
    logger.info("关键词过滤后 %d 篇相关文章", len(filtered))

    # 话题聚类
    clustered = cluster_by_topic(filtered)

    # 输出
    multi_source = sum(1 for c in clustered if c.get("source_count", 1) > 1)
    logger.info("聚类为 %d 个话题（%d 个多源交叉）", len(clustered), multi_source)

    output = {
        "scanned": len(all_articles),
        "filtered": len(filtered),
        "articles": clustered,
        "total": len(clustered),
        "multi_source": multi_source,
    }

    print(json.dumps(output, ensure_ascii=False))


def filter_by_keywords(articles, config):
    """按关键词过滤 + 评分

    返回新列表，不修改原始 article。
    """
    global_keywords = [k.lower() for k in config.get("global_keywords", [])]
    source_map = {s["name"]: s for s in config.get("sources", [])}

    scored = []
    for article in articles:
        source_name = article.get("source", "")
        source_config = source_map.get(source_name, {})

        score = calculate_relevance(article, source_config, global_keywords)
        enriched = {**article, "relevance_score": score}
        if source_config.get("category"):
            enriched["category"] = source_config["category"]

        if score >= 8:
            scored.append(enriched)

    scored.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return scored


def calculate_relevance(article, source_config, global_keywords):
    """计算文章相关性评分"""
    title = article.get("title", "").lower()
    source_weight = source_config.get("weight", 3)
    source_keywords = [k.lower() for k in source_config.get("keywords", [])]
    all_keywords = list(set(source_keywords + [k.lower() for k in global_keywords]))

    score = source_weight * 2  # 基础分 = 来源权重 × 2

    # 标题关键词匹配 (权重高)
    title_matches = sum(1 for kw in all_keywords if kw in title)
    score += title_matches * 3

    # 内容关键词匹配
    content = article.get("description", article.get("summary", "")).lower()
    if content:
        content_matches = sum(1 for kw in all_keywords if kw in content)
        score += content_matches * 1

    # 时效性加分
    pub_date = article.get("published_at", "")
    if pub_date:
        try:
            dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            hours_ago = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
            if hours_ago <= 24:
                score += 5
            elif hours_ago <= 48:
                score += 3
            elif hours_ago <= 72:
                score += 1
        except (ValueError, TypeError):
            pass

    return score


if __name__ == "__main__":
    main()
