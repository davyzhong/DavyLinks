#!/usr/bin/env python3
"""DavyLinks SQLite 状态管理模块 — 去重 + 运行日志"""

import sqlite3
import os
from datetime import datetime, timedelta

DB_PATH = os.path.expanduser("~/.davylinks/state.db")

SCHEMA_ARTICLES = """
CREATE TABLE IF NOT EXISTS processed_articles (
    url         TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    source      TEXT NOT NULL,
    category    TEXT DEFAULT '',
    published_at DATETIME,
    processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    relevance_score REAL DEFAULT 0,
    summary     TEXT DEFAULT '',
    pushed      INTEGER DEFAULT 0
)
"""

SCHEMA_RUN_LOG = """
CREATE TABLE IF NOT EXISTS run_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    run_date    DATE NOT NULL UNIQUE,
    scanned     INTEGER DEFAULT 0,
    filtered    INTEGER DEFAULT 0,
    summarized  INTEGER DEFAULT 0,
    pushed      INTEGER DEFAULT 0,
    errors      INTEGER DEFAULT 0,
    duration_s  REAL DEFAULT 0,
    status      TEXT DEFAULT 'success',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CLEANUP_SQL = """
DELETE FROM processed_articles
WHERE processed_at < datetime('now', '-90 days')
"""


def get_db(db_path=None):
    """获取数据库连接，首次使用自动建表"""
    path = db_path or DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(SCHEMA_ARTICLES)
    conn.execute(SCHEMA_RUN_LOG)
    conn.commit()
    return conn


def is_processed(conn, url):
    """检查 URL 是否已处理过"""
    row = conn.execute(
        "SELECT 1 FROM processed_articles WHERE url = ?", (url,)
    ).fetchone()
    return row is not None


def filter_new_articles(conn, articles):
    """从文章列表中过滤出未处理过的，返回新文章列表"""
    return [a for a in articles if not is_processed(conn, a.get("url", ""))]


def mark_processed(conn, articles):
    """批量标记文章为已处理（使用 INSERT OR REPLACE 支持摘要更新）"""
    for a in articles:
        conn.execute(
            """INSERT OR REPLACE INTO processed_articles
               (url, title, source, category, published_at, relevance_score, summary, pushed, processed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (
                a.get("url", ""),
                a.get("title", ""),
                a.get("source", ""),
                a.get("category", ""),
                a.get("published_at"),
                a.get("relevance_score", 0),
                a.get("summary", ""),
                1 if a.get("pushed") else 0,
            )
        )
    conn.commit()


def record_run(conn, stats):
    """记录一次运行日志"""
    today = datetime.now().strftime("%Y-%m-%d")
    conn.execute(
        """INSERT OR REPLACE INTO run_log
           (run_date, scanned, filtered, summarized, pushed, errors, duration_s, status)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            today,
            stats.get("scanned", 0),
            stats.get("filtered", 0),
            stats.get("summarized", 0),
            stats.get("pushed", 0),
            stats.get("errors", 0),
            stats.get("duration_s", 0),
            stats.get("status", "success"),
        )
    )
    conn.commit()


def cleanup_old(conn, days=90):
    """清理超过 N 天的已处理记录"""
    conn.execute(f"DELETE FROM processed_articles WHERE processed_at < datetime('now', '-{days} days')")
    conn.commit()


def get_stats(conn):
    """获取统计信息"""
    total = conn.execute("SELECT COUNT(*) FROM processed_articles").fetchone()[0]
    pushed = conn.execute("SELECT COUNT(*) FROM processed_articles WHERE pushed = 1").fetchone()[0]
    last_run = conn.execute("SELECT * FROM run_log ORDER BY id DESC LIMIT 1").fetchone()
    return {"total_processed": total, "total_pushed": pushed, "last_run": dict(last_run) if last_run else None}


if __name__ == "__main__":
    db = get_db()
    print("数据库初始化完成:", DB_PATH)
    stats = get_stats(db)
    print(f"已处理文章: {stats['total_processed']}, 已推送: {stats['total_pushed']}")
    if stats["last_run"]:
        lr = stats["last_run"]
        print(f"上次运行: {lr['run_date']} 扫描={lr['scanned']} 推送={lr['pushed']}")
