#!/usr/bin/env bash
set -euo pipefail

declare -A TAGS
TAGS["tests/test_floor_mod_gpu.py"]="gpu,heavy"
TAGS["tests/test_meta_ai_env_rl.py"]="heavy"
TAGS["tests/test_meta_ai_rl.py"]="heavy"
TAGS["tests/test_meta_ai_rl_longrun.py"]="heavy,slow"
TAGS["tests/test_meta_ai_rl_real_data.py"]="external,heavy"
TAGS["tests/test_mt5_connection.py"]="external,heavy"
TAGS["tests/integration_test_noctria.py"]="heavy"
TAGS["tests/test_trace_and_integration.py"]="heavy"
TAGS["tests/test_trace_decision_e2e.py"]="heavy"
TAGS["tests/execute_order_test.py"]="heavy"
TAGS["tests/backtesting/dqn_backtest.py"]="heavy"

for f in "${!TAGS[@]}"; do
  if [[ -f "$f" ]]; then
    tags="${TAGS[$f]}"
    if grep -q '^pytestmark\s*=' "$f"; then
      echo "skip (already has pytestmark): $f"
      continue
    fi
    tmp="$f.tmp.$$"
    tag_expr="$(echo "$tags" | sed 's/[^,][^,]*/pytest.mark.&/g' | sed 's/, */, /g')"
    {
      echo "import pytest  # added by mark_heavy_tests"
      echo "pytestmark = [$tag_expr]"
      echo
      cat "$f"
    } > "$tmp"
    mv "$tmp" "$f"
    echo "tagged $f -> [$tags]"
  else
    echo "not found: $f"
  fi
done
