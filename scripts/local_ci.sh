#!/usr/bin/env bash
set -euo pipefail

echo "== Noctria Local CI =="

# --- venv 判定 ---
if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "⚠️ You are not inside a virtualenv. Run 'source venv_codex/bin/activate' first."
  exit 1
fi

# --- requirements の選択 ---
REQ=""
if [ -f requirements-codex.txt ]; then
  REQ=requirements-codex.txt
elif [ -f requirements-dev.txt ]; then
  REQ=requirements-dev.txt
else
  echo "⚠️ requirements-codex.txt が見つかりません"
  exit 1
fi

# --- パッケージ同期 ---
pip install -U pip
pip install -r "$REQ"

# --- pytest の対象を決定 ---
# 既定: Codex 軽量プロファイルでは軽量テストのみ
TEST_SUITE=("tests/test_quality_gate_alerts.py" "tests/test_noctus_gate_block.py")

# CODEX_FULL=1 を付けて呼ぶと全テスト（重依存も）を実行
if [ "${CODEX_FULL:-0}" = "1" ]; then
  TEST_SUITE=("tests")
  echo "📦 Running FULL test suite (CODEX_FULL=1)"
else
  echo "🧪 Running LIGHT test subset for Codex:"
  printf '  - %s\n' "${TEST_SUITE[@]}"
fi

# --- pytest 実行 ---
echo "== Running pytest =="
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPATH="$(realpath ./src)"

# 軽量サブセットでも失敗は検知したいので '|| true' は付けない
pytest -q "${TEST_SUITE[@]}"

echo "== Local CI Done =="
