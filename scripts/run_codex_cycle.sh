#!/usr/bin/env bash
set -euo pipefail

echo "== Run Codex Cycle =="

if [ -z "${VIRTUAL_ENV:-}" ]; then
  echo "You are not inside venv_codex. Run: source venv_codex/bin/activate"
  exit 1
fi

export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
export PYTHONPATH=$(realpath ./src)

python -m codex.run_codex_cycle
