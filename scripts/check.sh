#!/usr/bin/env sh
set -eu

PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
PROJECT_ROOT=$(dirname "$SCRIPT_DIR")

cd "$PROJECT_ROOT"

"$PYTHON_BIN" -m py_compile scripts/*.py
"$PYTHON_BIN" -m pytest -q -o cache_dir="$PROJECT_ROOT/.pytest_cache"
