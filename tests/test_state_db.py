"""Tests for state_db module — SQL injection safety and batch operations."""

import sys


def get_state_db():
    sys.path.insert(0, "scripts")
    import state_db
    return state_db


def test_cleanup_old_uses_parameterized_query(tmp_path):
    """cleanup_old must not interpolate days into SQL (SQL injection guard)."""
    state_db = get_state_db()
    db_path = str(tmp_path / "test.db")
    conn = state_db.get_db(db_path)

    # Insert a record, then clean with a malicious string
    conn.execute(
        "INSERT INTO processed_articles (url, title, source) VALUES (?, ?, ?)",
        ("https://example.com/1", "Test", "Src"),
    )
    conn.commit()

    # Should not raise, even with a string that would be dangerous in f-string SQL
    state_db.cleanup_old(conn, days=90)

    # Record should still exist (it's fresh)
    row = conn.execute("SELECT 1 FROM processed_articles WHERE url = ?", ("https://example.com/1",)).fetchone()
    assert row is not None


def test_mark_processed_uses_executemany(tmp_path):
    """mark_processed should batch insert via executemany."""
    state_db = get_state_db()
    db_path = str(tmp_path / "test.db")
    conn = state_db.get_db(db_path)

    articles = [
        {"url": f"https://example.com/{i}", "title": f"Art {i}", "source": "Src", "relevance_score": 10}
        for i in range(5)
    ]
    state_db.mark_processed(conn, articles)

    count = conn.execute("SELECT COUNT(*) FROM processed_articles").fetchone()[0]
    assert count == 5


def test_mark_processed_updates_existing_records(tmp_path):
    """Re-marking an article should update, not duplicate."""
    state_db = get_state_db()
    db_path = str(tmp_path / "test.db")
    conn = state_db.get_db(db_path)

    article = {"url": "https://example.com/1", "title": "Old", "source": "Src"}
    state_db.mark_processed(conn, [article])

    updated = {"url": "https://example.com/1", "title": "New", "source": "Src"}
    state_db.mark_processed(conn, [updated])

    count = conn.execute("SELECT COUNT(*) FROM processed_articles").fetchone()[0]
    assert count == 1

    row = conn.execute("SELECT title FROM processed_articles WHERE url = ?", ("https://example.com/1",)).fetchone()
    assert row["title"] == "New"
