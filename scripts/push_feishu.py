#!/usr/bin/env python3
"""DavyLinks Phase 4: 推送飞书

从 stdin 读取摘要后的文章 JSON，生成推送内容并发送到飞书。
复用 Davybase 的 notify.py。

用法:
    python scan_articles.py | python summarize.py | python push_feishu.py
    python push_feishu.py --input result.json
    python push_feishu.py --dry-run   # 仅输出内容，不发送
"""

import json
import os
import subprocess
import sys
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from logging_config import setup_logging
from config_loader import get_davybase_config, get_feishu_config

logger = setup_logging(__name__)

# 延迟加载配置
_davybase_config = None
_feishu_webhook = None


def _get_davybase_config():
    global _davybase_config
    if _davybase_config is None:
        _davybase_config = get_davybase_config()
    return _davybase_config


def _get_feishu_webhook():
    global _feishu_webhook
    if _feishu_webhook is None:
        _feishu_webhook = get_feishu_config().get("webhook_url", "")
    return _feishu_webhook


def _source_badge(article):
    """生成来源标记：多源显示「X家媒体报道」，单源显示来源名"""
    source_count = article.get("source_count", 1)
    source_list = article.get("source_list", [])
    if source_count > 1:
        names = "、".join(source_list[:5])
        return f"{source_count}家媒体报道: {names}"
    return article.get("source", "")


def generate_digest(top5, other, total_scanned):
    """生成每日精华推送内容（支持话题聚类展示）"""
    today = datetime.now().strftime("%Y-%m-%d")
    lines = []
    lines.append(f"**每日科技资讯精华 {today}**\n")

    lines.append("**今日 TOP 5**\n")
    for i, article in enumerate(top5, 1):
        title = article.get("title", "(无标题)")
        summary = article.get("summary", "")
        source_count = article.get("source_count", 1)
        category = article.get("category", "")
        url = article.get("url", "")

        # 话题标记
        badge = ""
        if source_count > 1:
            badge = f" [{source_count}源]"

        lines.append(f"**{i}. {title}{badge}**")
        lines.append(f">{summary}")
        lines.append(f"{_source_badge(article)} | {category}")
        if url:
            lines.append(f"[原文链接]({url})")
        lines.append("")

    if other:
        lines.append("**值得关注**\n")
        for article in other:
            title = article.get("title", "(无标题)")
            url = article.get("url", "")
            source_count = article.get("source_count", 1)
            source_badge = f"[{source_count}源] " if source_count > 1 else ""
            source = _source_badge(article)
            lines.append(f"- **{source_badge}{title}** — {source} | [链接]({url})")
        lines.append("")

    lines.append("---")
    lines.append(f"由 DavyLinks 知识助理自动生成 | 共扫描 {total_scanned} 篇")

    return "\n".join(lines)


def send_via_davybase_notify(content):
    """通过 Davybase 的 notify.py 发送飞书消息"""
    cfg = _get_davybase_config()
    notify_path = cfg.get("notify_path", "")
    secrets_path = cfg.get("secrets_path", "")

    if not notify_path or not os.path.exists(notify_path):
        logger.warning("[ERROR] Davybase notify.py 不存在: %s", notify_path)
        return False

    try:
        cmd = ["python3", notify_path, "--message", content, "--type", "feishu"]
        if secrets_path:
            cmd.extend(["--config", secrets_path])
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            logger.info("[OK] 飞书推送成功")
            return True
        else:
            logger.warning("[ERROR] 飞书推送失败: %s", result.stderr.strip())
            return False
    except subprocess.TimeoutExpired:
        logger.warning("[ERROR] 飞书推送超时(30s)")
        return False


def send_via_webhook(content):
    """直接调用飞书 webhook 发送（不依赖 yaml/httpx）"""
    import urllib.request

    webhook_url = _get_feishu_webhook()
    if not webhook_url:
        logger.warning("[ERROR] 未配置 FEISHU_WEBHOOK_URL 或 feishu.webhook_url")
        return False

    try:
        today = datetime.now().strftime("%Y-%m-%d")
        payload = json.dumps({
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": f"每日科技资讯精华 {today}"},
                    "template": "green"
                },
                "elements": [
                    {"tag": "markdown", "content": content}
                ]
            }
        }).encode("utf-8")

        req = urllib.request.Request(webhook_url, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")

        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("code", -1) == 0 or result.get("StatusCode", -1) == 0:
                logger.info("[OK] 飞书推送成功")
                return True
            else:
                logger.warning("[ERROR] 飞书返回错误: %s", result)
                return False
    except Exception as e:
        logger.warning("[ERROR] webhook 推送失败: %s", e)
        return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DavyLinks 飞书推送")
    parser.add_argument("--dry-run", action="store_true", help="仅输出，不发送")
    parser.add_argument("--webhook", action="store_true", help="直接用 webhook 发送")
    args = parser.parse_args()

    # 读取输入
    if not sys.stdin.isatty():
        data = json.load(sys.stdin)
    else:
        logger.warning("[ERROR] 请通过管道输入 JSON")
        sys.exit(1)

    top5 = data.get("top5", [])
    other = data.get("other", [])
    total_scanned = data.get("total", len(top5) + len(other))

    if not top5 and not other:
        logger.info("[INFO] 今天没有新内容需要推送")
        return

    content = generate_digest(top5, other, total_scanned)

    if args.dry_run:
        logger.info(content)
        return

    # 发送
    if args.webhook:
        success = send_via_webhook(content)
    else:
        success = send_via_davybase_notify(content)
        if not success:
            logger.info("[FALLBACK] 尝试直接 webhook...")
            success = send_via_webhook(content)

    if success:
        # 标记已推送
        print(json.dumps({"pushed": len(top5) + len(other), "status": "success"}))
    else:
        print(json.dumps({"pushed": 0, "status": "failed"}))


if __name__ == "__main__":
    main()
