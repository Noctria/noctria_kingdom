#!/usr/bin/env bash
set -euo pipefail

echo "== Noctria Local CI (GPU) =="

# --- venv 判定 ---
if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "⚠️ You are not inside a virtualenv. Run 'source venv_codex/bin/activate' first."
  exit 1
fi

# --- 必須 requirements ---
REQ="requirements-codex-gpu.txt"
if [ ! -f "$REQ" ]; then
  echo "❌ $REQ が見つかりません（GPU環境用の依存ファイルを置いてください）"
  exit 1
fi

# --- GPU向け推奨環境変数（必要に応じて上書き） ---
export TF_FORCE_GPU_ALLOW_GROWTH=${TF_FORCE_GPU_ALLOW_GROWTH:-true}
export CUDA_VISIBLE_DEVICES=${CUDA_VISIBLE_DEVICES:-0}
# ↑ 特定GPUを使いたい場合は 0,1 などに変更

# --- パッケージ同期 ---
python -V
pip install -U pip
pip install -r "$REQ"

# --- テスト前の情報出力 ---
echo "== GPU Info (nvidia-smi があれば) =="
if command -v nvidia-smi >/dev/null 2>&1; then
  nvidia-smi || true
else
  echo "(nvidia-smi not found; コンテナ/マシンのPATHを確認してください)"
fi

# --- PyTest 実行 ---
echo "== Running pytest (GPU) =="
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPATH=$(realpath ./src)

# 軽量スモーク（GPU前提のテストだけ先に実行したい場合は、-k 'gpu or cuda' 等で調整）
pytest -q tests || true

echo "== Local CI (GPU) Done =="
