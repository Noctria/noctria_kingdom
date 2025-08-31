#!/usr/bin/env bash
set -euo pipefail

echo "== Noctria Local CI =="

# 1. venv作成
if [ ! -d .venv ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

# 2. 依存更新
pip install --upgrade pip
pip install -r requirements.txt -r requirements-dev.txt

# 3. テスト実行
pytest -q --maxfail=1 --disable-warnings --cov=src --cov-report=term-missing

# 4. 結果
echo "✅ Local CI passed"
