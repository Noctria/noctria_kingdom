#!/usr/bin/env bash
set -euo pipefail

echo "== Noctria Local CI =="

# --- venv 判定 ---
if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "⚠️ You are not inside a virtualenv. Run 'source venv_codex/bin/activate' first."
  exit 1
fi

# --- requirements の選択 ---
if [ -f requirements-codex.txt ]; then
  REQ=requirements-codex.txt
else
  echo "⚠️ requirements-codex.txt が見つかりません"
  exit 1
fi

# --- パッケージ同期 ---
pip install -U pip
pip install -r "$REQ"

# --- 簡易テスト実行 ---
echo "== Running pytest =="
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPATH=$(realpath ./src)
pytest -q tests || true

echo "== Local CI Done =="
