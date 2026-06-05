import importlib
import sys


def test_summarize_uses_shared_llm_provider_loader(monkeypatch):
    sys.path.insert(0, "scripts")
    sys.modules.pop("summarize", None)
    summarize = importlib.import_module("summarize")

    monkeypatch.setattr(
        summarize,
        "get_llm_provider_configs",
        lambda: {
            "qwen": {
                "api_key": "sk-project",
                "base_url": "https://dashscope.example/v1",
                "model": "qwen-plus",
            }
        },
    )

    configs = summarize.get_all_llm_configs()

    assert configs == [
        {
            "name": "qwen",
            "api_key": "sk-project",
            "base_url": "https://dashscope.example/v1",
            "model": "qwen-plus",
            "format": "openai",
        }
    ]


def test_save_obsidian_uses_shared_obsidian_loader(monkeypatch):
    sys.path.insert(0, "scripts")
    sys.modules.pop("save_obsidian", None)
    save_obsidian = importlib.import_module("save_obsidian")

    monkeypatch.setattr(
        save_obsidian,
        "get_obsidian_config",
        lambda: {"vault_path": "/tmp/project-vault"},
    )

    assert save_obsidian.load_vault_path() == "/tmp/project-vault"
