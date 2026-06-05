#!/usr/bin/env python3
"""DavyLinks 主流程：串联全部 5 个阶段

用法:
    python pipeline.py                # 完整执行
    python pipeline.py --dry-run      # 跑到推送前停止
    python pipeline.py --skip-push    # 跳过飞书推送
    python pipeline.py --skip-save    # 跳过 Obsidian 保存
    python pipeline.py --cleanup      # 清理旧记录
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

from logging_config import setup_logging

logger = setup_logging(__name__)


def run_phase(name, cmd, input_data=None):
    """运行一个阶段，返回输出"""
    logger.info("\n%s", "="*50)
    logger.info("[%s] 开始...", name)
    logger.info("%s", "="*50)

    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            input=input_data,
            capture_output=True,
            text=True,
            timeout=300,
            cwd=SCRIPT_DIR,
            env={**os.environ, "PYTHONPATH": SCRIPT_DIR},
        )
        elapsed = time.time() - start

        if result.returncode != 0:
            logger.error("[%s] 失败 (exit=%d)", name, result.returncode)
            logger.info(result.stderr)
            return None, elapsed

        logger.info("[%s] 完成 (%.1fs)", name, elapsed)
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                if line.strip():
                    logger.info("  %s", line)
        return result.stdout, elapsed

    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        logger.error("[%s] 超时 (%.1fs)", name, elapsed)
        return None, elapsed


def main():
    import argparse
    parser = argparse.ArgumentParser(description="DavyLinks 完整管线")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-push", action="store_true")
    parser.add_argument("--skip-save", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--db", default=None)
    args = parser.parse_args()

    total_start = time.time()
    stats = {"scanned": 0, "filtered": 0, "summarized": 0, "pushed": 0, "errors": 0}

    # 初始化数据库
    from state_db import get_db, record_run, mark_processed, cleanup_old
    db = get_db(args.db)

    if args.cleanup:
        cleanup_old(db)
        logger.info("旧记录清理完成")
        return

    logger.info("%s", "="*60)
    logger.info(" DavyLinks 每日信息聚合 — %s", datetime.now().strftime('%Y-%m-%d %H:%M'))
    logger.info("%s", "="*60)

    # Phase 1-2: 扫描 + 去重 + 过滤
    output_scan, t1 = run_phase(
        "Phase 1-2: 扫描+过滤",
        [sys.executable, os.path.join(SCRIPT_DIR, "scan_articles.py")],
    )

    if not output_scan:
        logger.info("\n[ABORT] 扫描阶段失败")
        stats["status"] = "scan_failed"
        stats["errors"] = 1
        record_run(db, {**stats, "duration_s": time.time() - total_start, "status": "failed"})
        return stats

    try:
        scan_data = json.loads(output_scan)
    except json.JSONDecodeError:
        logger.info("[ABORT] 扫描输出解析失败")
        stats["status"] = "parse_failed"
        stats["errors"] = 1
        record_run(db, {**stats, "duration_s": time.time() - total_start, "status": "parse_failed"})
        return stats

    stats["scanned"] = scan_data.get("scanned", 0)
    stats["filtered"] = scan_data.get("filtered", 0)
    articles = scan_data.get("articles", [])

    if not articles:
        logger.info("\n[DONE] 今天没有新的相关文章")
        record_run(db, {**stats, "duration_s": time.time() - total_start, "status": "no_articles"})
        return stats

    if args.dry_run:
        logger.info("\n[DRY RUN] 找到 %d 篇相关文章，停止执行", len(articles))
        for i, a in enumerate(articles[:10], 1):
            logger.info("  %d. [%s] %s (score=%d)", i, a.get('source', '?'), a.get('title', '?')[:50], a.get('relevance_score', 0))
        return stats

    # Phase 3: LLM 摘要 + 排序
    output_sum, t3 = run_phase(
        "Phase 3: AI摘要+排序",
        [sys.executable, os.path.join(SCRIPT_DIR, "summarize.py")],
        input_data=output_scan,
    )

    if not output_sum:
        logger.warning("[WARN] 摘要阶段失败，使用原始数据继续")
        sum_data = {"top5": articles[:5], "other": articles[5:15], "total": len(articles)}
        stats["errors"] += 1
    else:
        try:
            sum_data = json.loads(output_sum)
        except json.JSONDecodeError:
            logger.warning("[WARN] 摘要输出解析失败，使用原始数据")
            sum_data = {"top5": articles[:5], "other": articles[5:15], "total": len(articles)}
            stats["errors"] += 1

    stats["summarized"] = sum_data.get("total", len(articles))

    # Phase 3.5: 写入飞书多维表格
    if not args.skip_push:
        output_bitable, t_bitable = run_phase(
            "Phase 3.5: 写入飞书表格",
            [sys.executable, os.path.join(SCRIPT_DIR, "feishu_bitable.py")],
            input_data=json.dumps({
                "articles": sum_data.get("articles", sum_data.get("top5", []) + sum_data.get("other", [])),
                "date": datetime.now().strftime("%Y-%m-%d"),
            }, ensure_ascii=False),
        )
        if not output_bitable:
            stats["errors"] += 1
        else:
            try:
                bitable_data = json.loads(output_bitable)
                stats["errors"] += int(bitable_data.get("bitable_fail", 0))
            except json.JSONDecodeError:
                stats["errors"] += 1

    # Phase 4: 推送飞书
    if not args.skip_push:
        output_push, t4 = run_phase(
            "Phase 4: 推送飞书",
            [sys.executable, os.path.join(SCRIPT_DIR, "push_feishu.py")],
            input_data=json.dumps(sum_data, ensure_ascii=False),
        )
        if output_push:
            try:
                push_data = json.loads(output_push)
                stats["pushed"] = push_data.get("pushed", 0)
            except json.JSONDecodeError:
                stats["errors"] += 1
        else:
            stats["errors"] += 1

    # Phase 5: 沉淀 Obsidian
    if not args.skip_save:
        output_save, t5 = run_phase(
            "Phase 5: 沉淀Obsidian",
            [sys.executable, os.path.join(SCRIPT_DIR, "save_obsidian.py")],
            input_data=json.dumps(sum_data, ensure_ascii=False),
        )
        if not output_save:
            stats["errors"] += 1
        else:
            try:
                json.loads(output_save)
            except json.JSONDecodeError:
                stats["errors"] += 1

    # 记录状态
    all_processed = sum_data.get("articles") or (sum_data.get("top5", []) + sum_data.get("other", []))
    mark_processed(db, all_processed)

    total_elapsed = time.time() - total_start
    stats["duration_s"] = round(total_elapsed, 1)
    stats["status"] = "success" if stats["errors"] == 0 else "partial"
    record_run(db, stats)

    # 汇总
    logger.info("\n%s", "="*60)
    logger.info(" DavyLinks 执行完成 — %.1fs", total_elapsed)
    logger.info(" 扫描: %d | 过滤: %d | 摘要: %d | 推送: %d",
                stats['scanned'], stats['filtered'], stats['summarized'], stats['pushed'])
    logger.info(" 状态: %s", stats['status'])
    logger.info("%s", "="*60)

    # 标记 blogwatcher 文章为已读
    try:
        subprocess.run(
            ["blogwatcher-cli", "read-all"],
            capture_output=True, timeout=10,
            env={**os.environ, "BLOGWATCHER_YES": "1"},)
    except Exception as e:
        logger.debug("blogwatcher-cli read-all 失败: %s", e)

    return stats


if __name__ == "__main__":
    result = main()
    if result and isinstance(result, dict) and result.get("errors", 0) > 0:
        sys.exit(1)
