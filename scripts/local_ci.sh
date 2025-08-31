#!/usr/bin/env bash
set -euo pipefail

echo "== Noctria Local CI =="

REQ_FILE="requirements-codex.txt"

if [ -f "$REQ_FILE" ]; then
  pip install -r "$REQ_FILE"
else
  echo "⚠️ $REQ_FILE が見つかりません"
fi

pytest -q tests/
