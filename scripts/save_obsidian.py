#!/usr/bin/env python3
"""DavyLinks Phase 5: 沉淀到 Obsidian

将 TOP 5 文章写入 Obsidian vault 的知识助理目录。

用法:
    python scan_articles.py | python summarize.py | python save_obsidian.py
    python save_obsidian.py --input result.json
    python save_obsidian.py --weekly    # 生成周报
"""

import json
import sys
import os
from datetime import datetime, timedelta

VAULT_PATH = os.environ.get("OBSIDIAN_VAULT_PATH", "/Users/qiming/ObsidianWiki")
DIGEST_DIR = os.path.join(VAULT_PATH, "知识助理", "每日精华")


def generate_note_content(top5, other, today):
    """生成 Obsidian 笔记内容"""
    lines = []

    # Frontmatter
    lines.append("---")
    lines.append("type: daily-digest")
    lines.append(f"date: {today}")
    lines.append(f"sources_count: {len(set(a.get('source', '') for a in top5 + other))}")
    lines.append(f"articles_count: {len(top5) + len(other)}")
    lines.append("auto_generated: true")
    tags = set()
    for a in top5 + other:
        tags.update(a.get("tags", []))
    tags.add("davylinks")
    tags.add("daily-digest")
    lines.append(f"tags: [{', '.join(sorted(tags))}]")
    lines.append("---")
    lines.append("")

    lines.append(f"# 每日科技资讯精华 {today}")
    lines.append("")

    # TOP 5
    lines.append("## TOP 5")
    lines.append("")
    for i, article in enumerate(top5, 1):
        title = article.get("title", "(无标题)")
        summary = article.get("summary", "")
        source = article.get("source", "")
        category = article.get("category", "")
        url = article.get("url", "")
        tags_str = ", ".join(f"#{t}" for t in article.get("tags", []))
        score = article.get("final_score", 0)

        lines.append(f"### {i}. {title}")
        lines.append(f"> [!info] 摘要")
        lines.append(f"> {summary}")
        lines.append(f"")
        lines.append(f"| 属性 | 值 |")
        lines.append(f"|------|-----|")
        lines.append(f"| 来源 | {source} |")
        lines.append(f"| 分类 | {category} |")
        lines.append(f"| 评分 | {score:.1f} |")
        if url:
            lines.append(f"| 链接 | [{url[:50]}...]({url}) |")
        if tags_str:
            lines.append(f"| 标签 | {tags_str} |")
        lines.append("")

    # 值得关注
    if other:
        lines.append("## 值得关注")
        lines.append("")
        for article in other:
            title = article.get("title", "(无标题)")
            source = article.get("source", "")
            url = article.get("url", "")
            summary_short = article.get("summary", "")[:80]
            lines.append(f"- **{title}** — {summary_short} | {source}")
            if url:
                lines.append(f"  - [链接]({url})")
        lines.append("")

    lines.append("---")
    lines.append(f"*由 DavyLinks 知识助理自动生成*")

    return "\n".join(lines)


def save_daily_note(top5, other):
    """保存每日笔记到 Obsidian"""
    today = datetime.now().strftime("%Y-%m-%d")

    os.makedirs(DIGEST_DIR, exist_ok=True)
    filepath = os.path.join(DIGEST_DIR, f"{today}.md")

    content = generate_note_content(top5, other, today)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"[OK] 已保存到 {filepath}", file=sys.stderr)
    return filepath


def generate_weekly_note(daily_dir):
    """生成本周的周报（汇总本周所有每日精华）"""
    import glob

    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())  # 本周一
    week_num = today.isocalendar()[1]
    week_label = f"{today.year}-W{week_num:02d}"

    weekly_dir = os.path.join(os.path.dirname(daily_dir), "每周精华")
    os.makedirs(weekly_dir, exist_ok=True)

    # 收集本周的每日笔记
    all_articles = []
    for i in range(7):
        day = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
        filepath = os.path.join(daily_dir, f"{day}.md")
        if os.path.exists(filepath):
            # 简单策略：读取元数据行
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            # 提取 TOP 5 标题
            for line in text.split("\n"):
                if line.startswith("### ") and line[4].isdigit():
                    title = line[5:].strip()
                    all_articles.append({"title": title, "day": day})

    if not all_articles:
        print(f"[INFO] 本周({week_label})暂无内容", file=sys.stderr)
        return None

    lines = ["---", f"type: weekly-digest", f"week: {week_label}", "---", ""]
    lines.append(f"# 每周科技精华 {week_label}")
    lines.append("")
    lines.append(f"本周共收录 {len(all_articles)} 篇精选文章：")
    lines.append("")
    for a in all_articles:
        lines.append(f"- [{a['day']}] {a['title']}")

    filepath = os.path.join(weekly_dir, f"{week_label}.md")
    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"[OK] 周报已保存到 {filepath}", file=sys.stderr)
    return filepath


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DavyLinks Obsidian 沉淀")
    parser.add_argument("--input", help="输入 JSON 文件路径")
    parser.add_argument("--weekly", action="store_true", help="生成周报")
    args = parser.parse_args()

    if args.weekly:
        generate_weekly_note(DIGEST_DIR)
        return

    # 读取输入
    if args.input:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    elif not sys.stdin.isatty():
        data = json.load(sys.stdin)
    else:
        print("[ERROR] 请通过管道或 --input 输入 JSON", file=sys.stderr)
        sys.exit(1)

    top5 = data.get("top5", [])
    other = data.get("other", [])

    if not top5 and not other:
        print("[INFO] 没有内容需要保存", file=sys.stderr)
        return

    filepath = save_daily_note(top5, other)
    print(json.dumps({"saved": filepath, "articles": len(top5) + len(other)}))


if __name__ == "__main__":
    main()
