import importlib
import io
import json
import sys


def import_push_feishu(monkeypatch, webhook_url="https://example.com/hook"):
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", webhook_url)
    sys.modules.pop("push_feishu", None)
    sys.path.insert(0, "scripts")
    return importlib.import_module("push_feishu")


def test_success_result_is_written_to_stdout(monkeypatch, capsys):
    push_feishu = import_push_feishu(monkeypatch)
    payload = {
        "top5": [{"title": "A", "summary": "S", "url": "https://a.example"}],
        "other": [],
        "total": 1,
    }

    stdin = io.StringIO(json.dumps(payload))
    monkeypatch.setattr(stdin, "isatty", lambda: False)
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(push_feishu, "send_via_davybase_notify", lambda content: True)
    monkeypatch.setattr(sys, "argv", ["push_feishu.py"])

    push_feishu.main()

    stdout = capsys.readouterr().out.strip()
    assert json.loads(stdout) == {"pushed": 1, "status": "success"}


def test_webhook_is_loaded_from_environment(monkeypatch):
    push_feishu = import_push_feishu(monkeypatch, "https://example.com/custom-hook")

    assert push_feishu._get_feishu_webhook() == "https://example.com/custom-hook"
