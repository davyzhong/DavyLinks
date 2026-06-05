#!/usr/bin/env python3
"""Shared configuration loading for DavyLinks."""

from __future__ import annotations

import copy
import os
from typing import Any


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_USER_CONFIG = os.path.expanduser("~/.davylinks/secrets.yaml")


def _read_yaml(path: str) -> dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}

    try:
        import yaml

        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except ImportError:
        return _parse_yaml_simple(path)


def _parse_yaml_simple(path: str) -> dict[str, Any]:
    """Small YAML subset parser for simple secrets files."""
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            raw = line.rstrip()
            stripped = raw.strip()
            if not stripped or stripped.startswith("#") or ":" not in stripped:
                continue

            indent = len(raw) - len(raw.lstrip())
            key, value = stripped.split(":", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            while stack and indent <= stack[-1][0]:
                stack.pop()
            parent = stack[-1][1]

            if value:
                parent[key] = value
            else:
                child: dict[str, Any] = {}
                parent[key] = child
                stack.append((indent, child))

    return result


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = copy.deepcopy(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = copy.deepcopy(value)
    return merged


def load_secrets(
    project_root: str | None = None,
    user_config_path: str | None = None,
) -> dict[str, Any]:
    """Load secrets with project config taking precedence over user config."""
    root = project_root or PROJECT_ROOT
    user_path = DEFAULT_USER_CONFIG if user_config_path is None else user_config_path
    project_path = os.path.join(root, "config", "secrets.yaml")

    config = _read_yaml(user_path)
    config = _deep_merge(config, _read_yaml(project_path))
    return config


def get_feishu_config(
    project_root: str | None = None,
    user_config_path: str | None = None,
) -> dict[str, str]:
    config = load_secrets(project_root, user_config_path)
    feishu = config.get("feishu", {}) or {}
    bitable = feishu.get("bitable", {}) or {}

    return {
        "app_id": os.environ.get("FEISHU_APP_ID", feishu.get("app_id", "")),
        "app_secret": os.environ.get("FEISHU_APP_SECRET", feishu.get("app_secret", "")),
        "webhook_url": os.environ.get("FEISHU_WEBHOOK_URL", feishu.get("webhook_url", "")),
        "bitable_token": os.environ.get("FEISHU_BITABLE_TOKEN", bitable.get("app_token", "")),
        "bitable_table_id": os.environ.get("FEISHU_TABLE_ID", bitable.get("table_id", "")),
    }


def get_llm_provider_configs(
    project_root: str | None = None,
    user_config_path: str | None = None,
) -> dict[str, dict[str, Any]]:
    config = load_secrets(project_root, user_config_path)
    providers = config.get("llm_providers", {}) or {}
    if not providers:
        providers = config.get("providers", {}) or {}
    return providers


def get_obsidian_config(
    project_root: str | None = None,
    user_config_path: str | None = None,
) -> dict[str, str]:
    config = load_secrets(project_root, user_config_path)
    obsidian = config.get("obsidian", {}) or {}
    return {
        "vault_path": os.environ.get(
            "OBSIDIAN_VAULT_PATH",
            obsidian.get("vault_path", "/Users/qiming/ObsidianWiki"),
        )
    }


def get_davybase_config(
    project_root: str | None = None,
    user_config_path: str | None = None,
) -> dict[str, str]:
    config = load_secrets(project_root, user_config_path)
    davybase = config.get("davybase", {}) or {}
    return {
        "notify_path": os.environ.get("DAVYBASE_NOTIFY_PATH", davybase.get("notify_path", "")),
        "secrets_path": os.environ.get("DAVYBASE_SECRETS_PATH", davybase.get("secrets_path", "")),
    }
