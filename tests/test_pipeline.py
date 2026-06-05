import importlib
import json
import sys


def test_pipeline_counts_downstream_failures_and_marks_all_articles(monkeypatch):
    sys.path.insert(0, "scripts")
    sys.modules.pop("pipeline", None)
    pipeline = importlib.import_module("pipeline")
    import state_db

    articles = [
        {
            "title": f"Article {i}",
            "url": f"https://example.com/{i}",
            "source": "Test",
            "relevance_score": 10,
        }
        for i in range(16)
    ]
    scan_data = {"scanned": 16, "filtered": 16, "articles": articles}
    sum_data = {
        "articles": articles,
        "top5": articles[:5],
        "other": articles[5:15],
        "total": 16,
    }

    def fake_run_phase(name, cmd, input_data=None):
        if "扫描" in name:
            return json.dumps(scan_data), 0.1
        if "摘要" in name:
            return json.dumps(sum_data), 0.1
        if "写入飞书表格" in name:
            return None, 0.1
        if "推送飞书" in name:
            return json.dumps({"pushed": 15, "status": "success"}), 0.1
        if "沉淀Obsidian" in name:
            return None, 0.1
        raise AssertionError(f"unexpected phase {name}")

    recorded = {}
    marked = {}
    monkeypatch.setattr(pipeline, "run_phase", fake_run_phase)
    monkeypatch.setattr(state_db, "get_db", lambda db_path=None: object())
    monkeypatch.setattr(state_db, "record_run", lambda db, stats: recorded.update(stats))
    monkeypatch.setattr(state_db, "mark_processed", lambda db, items: marked.update({"items": items}))
    monkeypatch.setattr(state_db, "cleanup_old", lambda db: None)
    monkeypatch.setattr(sys, "argv", ["pipeline.py"])

    pipeline.main()

    assert recorded["errors"] == 2
    assert recorded["status"] == "partial"
    assert recorded["pushed"] == 15
    assert len(marked["items"]) == 16
