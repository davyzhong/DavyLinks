import sys


def test_project_secrets_override_user_secrets(tmp_path, monkeypatch):
    sys.path.insert(0, "scripts")
    from config_loader import load_secrets

    project_root = tmp_path / "project"
    project_config = project_root / "config"
    project_config.mkdir(parents=True)
    project_secrets = project_config / "secrets.yaml"
    project_secrets.write_text(
        "feishu:\n  webhook_url: https://project.example/hook\n",
        encoding="utf-8",
    )

    user_secrets = tmp_path / "user-secrets.yaml"
    user_secrets.write_text(
        "feishu:\n  webhook_url: https://user.example/hook\n",
        encoding="utf-8",
    )

    config = load_secrets(project_root=str(project_root), user_config_path=str(user_secrets))

    assert config["feishu"]["webhook_url"] == "https://project.example/hook"


def test_environment_overrides_feishu_config(tmp_path, monkeypatch):
    sys.path.insert(0, "scripts")
    from config_loader import get_feishu_config

    project_root = tmp_path / "project"
    project_config = project_root / "config"
    project_config.mkdir(parents=True)
    (project_config / "secrets.yaml").write_text(
        "feishu:\n"
        "  app_id: cli_project\n"
        "  app_secret: project_secret\n"
        "  webhook_url: https://project.example/hook\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("FEISHU_WEBHOOK_URL", "https://env.example/hook")

    config = get_feishu_config(project_root=str(project_root), user_config_path="")

    assert config["webhook_url"] == "https://env.example/hook"


def test_llm_providers_load_from_project_secrets(tmp_path):
    sys.path.insert(0, "scripts")
    from config_loader import get_llm_provider_configs

    project_root = tmp_path / "project"
    project_config = project_root / "config"
    project_config.mkdir(parents=True)
    (project_config / "secrets.yaml").write_text(
        "llm_providers:\n"
        "  qwen:\n"
        "    api_key: sk-project\n"
        "    base_url: https://dashscope.example/v1\n"
        "    model: qwen-plus\n",
        encoding="utf-8",
    )

    configs = get_llm_provider_configs(project_root=str(project_root), user_config_path="")

    assert configs["qwen"]["api_key"] == "sk-project"
    assert configs["qwen"]["model"] == "qwen-plus"
