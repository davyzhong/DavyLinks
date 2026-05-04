#!/usr/bin/env python3
"""DavyLinks Phase 1-2: 扫描所有信息源 + 去重过滤 + 关键词评分 + 话题聚类

用法:
    python scan_articles.py                  # 扫描全部源，输出聚类后的文章 JSON
    python scan_articles.py --scan-only      # 仅扫描，不过滤（调试用）
    python scan_articles.py --cleanup        # 清理 90 天前的旧记录
"""

# 导入日志配置
import sys
import os
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from logging_config import setup_logging

logger = setup_logging(__name__)


import json
import subprocess
import sys
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_PATH = os.path.join(PROJECT_DIR, "config", "sources.json")

sys.path.insert(0, SCRIPT_DIR)
from state_db import get_db, filter_new_articles, cleanup_old


def load_config():
    """加载信息源配置"""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


WEWE_RSS_URL = "http://localhost:4000/feeds/all.atom"


def scan_wewe_rss():
    """直接从 wewe-rss Atom feed 抓取公众号文章"""
    articles = []
    try:
        req = urllib.request.Request(WEWE_RSS_URL, headers={"User-Agent": "DavyLinks/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
        root = ET.fromstring(data)
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            updated_el = entry.find("atom:updated", ns)
            # 尝试从 content 中提取来源（公众号名）
            content_el = entry.find("atom:content", ns)
            source_name = "微信公众号"
            # Atom entry 没有 author/name 就用默认
            author_el = entry.find("atom:author/atom:name", ns)
            if author_el is not None and author_el.text:
                source_name = author_el.text

            title = title_el.text if title_el is not None else ""
            # 去掉 CDATA 包裹的 HTML 标签
            if title:
                title = re.sub(r'<[^>]+>', '', title).strip()
            url = link_el.get("href", "") if link_el is not None else ""
            pub = updated_el.text if updated_el is not None else ""

            articles.append({
                "title": title,
                "url": url,
                "source": source_name,
                "published_at": pub[:19].replace("T", " ") if pub else "",
                "id": hash(url) & 0x7FFFFFFF,
            })
        logger.info("  [wewe-rss] 获取到 {len(articles)} 篇公众号文章", file=sys.stderr)
    except Exception as e:
        logger.warning("[WARN] wewe-rss 抓取失败: {e}")
    return articles


def scan_blogwatcher():
    """调用 blogwatcher-cli scan 扫描所有源，返回文章列表"""
    try:
        result = subprocess.run(
            ["blogwatcher-cli", "scan"],
            capture_output=True, text=True, timeout=120,
            env={**os.environ, "BLOGWATCHER_YES": "1", "BLOGWATCHER_SILENT": "1"}
        )
        if result.returncode != 0:
            logger.warning("[WARN] blogwatcher scan 返回非零: {result.stderr.strip()}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        logger.warning("[WARN] blogwatcher scan 超时(120s)", file=sys.stderr)
    except FileNotFoundError:
        logger.warning("[ERROR] blogwatcher-cli 未安装")
        sys.exit(1)


def list_articles():
    """获取 blogwatcher 中的未读文章"""
    try:
        result = subprocess.run(
            ["blogwatcher-cli", "articles", "--all"],
            capture_output=True, text=True, timeout=30,
            env={**os.environ, "BLOGWATCHER_SILENT": "1"}
        )
        return parse_articles_output(result.stdout)
    except Exception as e:
        logger.warning("[WARN] 获取文章列表失败: {e}")
        return []


def parse_articles_output(output):
    """解析 blogwatcher-cli articles 的输出为结构化列表"""
    articles = []
    current = {}
    id_re = re.compile(r"^\s*\[(\d+)\]\s+\[(\w+)\]\s+(.+)$")
    field_re = re.compile(r"^\s+(Blog|URL|Published|Category):\s+(.+)$")

    for line in output.split("\n"):
        m = id_re.match(line)
        if m:
            if current.get("url"):
                articles.append(current)
            current = {
                "id": int(m.group(1)),
                "status": m.group(2),
                "title": m.group(3).strip(),
            }
            continue

        m = field_re.match(line)
        if m:
            key = m.group(1).lower()
            val = m.group(2).strip()
            if key == "blog":
                current["source"] = val
            elif key == "url":
                current["url"] = val
            elif key == "published":
                current["published_at"] = val
            elif key == "category":
                current["category"] = val
            continue

    if current.get("url"):
        articles.append(current)

    return articles


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
            dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00").replace("+00:00", ""))
            hours_ago = (datetime.now() - dt).total_seconds() / 3600
            if hours_ago <= 24:
                score += 5
            elif hours_ago <= 48:
                score += 3
            elif hours_ago <= 72:
                score += 1
        except (ValueError, TypeError):
            pass

    return score


def filter_by_keywords(articles, config):
    """按关键词过滤 + 评分"""
    global_keywords = [k.lower() for k in config.get("global_keywords", [])]
    source_map = {s["name"]: s for s in config.get("sources", [])}

    scored = []
    for article in articles:
        source_name = article.get("source", "")
        source_config = source_map.get(source_name, {})

        if source_config.get("category"):
            article["category"] = source_config["category"]

        score = calculate_relevance(article, source_config, global_keywords)
        article["relevance_score"] = score

        if score >= 8:
            scored.append(article)

    scored.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)
    return scored


# ============================================================
# 话题聚类：合并相同主题 + 交叉验证评分
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


def chinese_overlap(title1, title2):
    """中文二元组包含度（短标题的 bigram 有多少出现在长标题中）"""
    def cn_bigrams(t):
        chars = re.findall(r'[\u4e00-\u9fff]', t)
        return set(chars[i] + chars[i+1] for i in range(len(chars) - 1))

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


def cluster_by_topic(articles):
    """将相似文章聚类为话题，按交叉验证数评分

    核心逻辑:
    - 多个媒体同时报道同一话题 = 热点 → 排名靠前
    - 每个话题合并为一篇，展示所有来源
    - 评分 = max(相关度) + 来源数 × 15
    """
    n = len(articles)
    if n == 0:
        return []

    # Union-Find 聚类
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    # 两两比较，决定是否归为同一话题
    for i in range(n):
        for j in range(i + 1, n):
            if should_cluster(articles[i].get("title", ""), articles[j].get("title", "")):
                union(i, j)

    # 按根节点分组
    groups = {}
    for i in range(n):
        root = find(i)
        if root not in groups:
            groups[root] = []
        groups[root].append(i)

    # 构建话题对象
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

    # 按 final_score 降序
    clusters.sort(key=lambda c: c["final_score"], reverse=True)
    return clusters


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DavyLinks 扫描+过滤+聚类")
    parser.add_argument("--scan-only", action="store_true", help="仅扫描，不过滤")
    parser.add_argument("--cleanup", action="store_true", help="清理旧记录")
    parser.add_argument("--db", default=None, help="自定义数据库路径")
    args = parser.parse_args()

    db = get_db(args.db)

    if args.cleanup:
        cleanup_old(db)
        logger.info("清理完成")
        return

    # Phase 1: 扫描
    logger.info("[Phase 1] 扫描信息源...")
    scan_blogwatcher()
    articles = list_articles()
    logger.info("  扫描到 {len(articles)} 篇文章", file=sys.stderr)

    # 合并 wewe-rss 公众号文章
    wewe_articles = scan_wewe_rss()
    if wewe_articles:
        articles.extend(wewe_articles)
        logger.info("  合并后共 {len(articles)} 篇文章", file=sys.stderr)

    if args.scan_only:
        for a in articles:
            logger.info("  - [{a.get('source', '?')}] {a.get('title', '(无标题)')}")
        return

    # Phase 2: 去重 + 过滤
    config = load_config()

    new_articles = filter_new_articles(db, articles)
    logger.info("  去重后 {len(new_articles)} 篇新文章", file=sys.stderr)

    filtered = filter_by_keywords(new_articles, config)
    logger.info("  关键词过滤后 {len(filtered)} 篇相关文章", file=sys.stderr)

    # Phase 2.5: 话题聚类 + 交叉验证排序
    clustered = cluster_by_topic(filtered)
    multi_source = sum(1 for c in clustered if c["source_count"] > 1)
    logger.info("  聚类为 {len(clustered)} 个话题（{multi_source} 个多源交叉验证）", file=sys.stderr)

    # 调试：打印 TOP 10
    for i, c in enumerate(clustered[:10]):
        badge = f"[{c['source_count']}源]" if c["source_count"] > 1 else ""
        logger.info("    {i+1}. {badge} {c['title'][:50]} (score={c['final_score']})", file=sys.stderr)

    # 输出 JSON (stdout only, 用于管道传递)
    output = {
        "scanned": len(articles),
        "new": len(new_articles),
        "filtered": len(filtered),
        "clustered": len(clustered),
        "articles": clustered,
    }
    logger.info(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
