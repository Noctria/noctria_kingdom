# scripts/codex_cycle_first_spec.sh
# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

log() { echo -e "$@" >&2; }

log "[env] ROOT=$ROOT"
log "[env] python=$(command -v python || true)"
log "[env] pytest=$(command -v pytest || true)"

# --------------------------------------------
# 1) Env + 観測テーブル ensure（常に実行）
# --------------------------------------------
log "[1/5] Ensure env & obs schema"
PYTHONPATH="$ROOT" python - <<'PY'
from src.core.path_config import ensure_import_path
ensure_import_path()  # 集中管理に従って import 経路を安定化
from src.core.envload import load_noctria_env
from src.plan_data.observability_migrate import main as migrate_main
load_noctria_env(); migrate_main()
PY

# --------------------------------------------
# ユーティリティ: 指定ファイル名をリポジトリ内から探索
#   優先: scripts/ → src/ → repo 全体（venv_* 配下は除外）
# --------------------------------------------
find_file() {
  local name="$1"
  if [ -f "$ROOT/scripts/$name" ]; then
    printf '%s\n' "$ROOT/scripts/$name"; return 0
  fi
  local f
  f="$(find "$ROOT/src" -type f -name "$name" 2>/dev/null | head -n1 || true)"
  if [ -n "${f:-}" ]; then printf '%s\n' "$f"; return 0; fi
  f="$(find "$ROOT" -type f -name "$name" ! -path "*/venv_*/*" 2>/dev/null | head -n1 || true)"
  if [ -n "${f:-}" ]; then printf '%s\n' "$f"; return 0; fi
  return 1
}

# --------------------------------------------
# 2) Task discovery → JSONL
#    - 既存 codex_reports/tasks_discovered.jsonl があれば再利用
#    - task_discovery.py が見つかれば実行して生成
#    - 環境変数 CODEX_FORCE_REUSE=1 で常にスキップ可能
# --------------------------------------------
log "[2/5] Task discovery → JSONL（無ければ作成、あれば再利用）"
TASKS_JSONL="$ROOT/codex_reports/tasks_discovered.jsonl"
TASK_DISCOVERY="$(find_file task_discovery.py || true)"
mkdir -p "$ROOT/codex_reports"

if [ "${CODEX_FORCE_REUSE:-0}" != "0" ]; then
  log "  - CODEX_FORCE_REUSE=1 → discovery をスキップします"
elif [ -f "$TASKS_JSONL" ]; then
  log "  - found: $TASKS_JSONL → reuse"
else
  if [ -n "${TASK_DISCOVERY:-}" ]; then
    log "  - run: $TASK_DISCOVERY (制限付き)"
    # 重いフルスキャンを避けるため、引数がある実装なら制限を渡す
    PYTHONPATH="$ROOT" python "$TASK_DISCOVERY" \
      --in "$ROOT" \
      --out "$TASKS_JSONL" \
      --save-db \
      --max-files "${CODEX_MAX_FILES:-3000}" \
      --exclude "${CODEX_EXCLUDES:-.git|venv_|node_modules|_graveyard|airflow_docker/.+cache}" \
      || true
    if [ -f "$TASKS_JSONL" ]; then
      log "  - produced: $TASKS_JSONL"
    else
      log "  ! task discovery did not produce $TASKS_JSONL (続行可能)"
    fi
  else
    log "  ! task_discovery.py not found, and $TASKS_JSONL missing → skip discovery"
  fi
fi

# --------------------------------------------
# 3) Spec/Test 生成（limit=1：最初の1本に集中）
#    - spec_writer.py が見つかり、かつ JSONL があれば生成
#    - どちらか無ければ既存 Spec を使って続行
# --------------------------------------------
log "[3/5] Spec/Test 生成（limit=1：最初の1本に集中）"
SPEC_WRITER="$(find_file spec_writer.py || true)"
SPEC_DIR="$ROOT/docs/specs"
TEST_GEN_DIR="$ROOT/tests/generated"
mkdir -p "$SPEC_DIR" "$TEST_GEN_DIR"

if [ -n "${SPEC_WRITER:-}" ] && [ -f "$TASKS_JSONL" ]; then
  log "  - run: $SPEC_WRITER"
  PYTHONPATH="$ROOT" python "$SPEC_WRITER" \
    --in "$TASKS_JSONL" \
    --limit "${CODEX_SPEC_LIMIT:-1}" \
    --out-spec-dir "$SPEC_DIR" \
    --out-test-dir "$TEST_GEN_DIR" || true
else
  [ -z "${SPEC_WRITER:-}" ] && log "  ! spec_writer.py not found → skip generation"
  [ ! -f "$TASKS_JSONL" ] && log "  ! $TASKS_JSONL not found → cannot generate new spec/test"
fi

# --------------------------------------------
# 4) 対象Spec抽出（最新の codex_task_*.md）
# --------------------------------------------
log "[4/5] 対象Specを抽出"
LATEST_SPEC="$(ls -1t "$SPEC_DIR"/codex_task_*.md 2>/dev/null | head -n1 || true)"
if [ -z "${LATEST_SPEC:-}" ]; then
  log "  ! no specs found in $SPEC_DIR (codex_task_*.md)."
  log "    - 既存のSpecが無い場合は generator の配置/実行を確認してください。"
  exit 3
fi
log "  - SPEC: $LATEST_SPEC"
log "  - TARGET FILE hinted in SPEC, e.g., noctria_gui/main.py"

# タイムスタンプ抽出（YYYYmmddThhMMss だけ抜き出し）
STAMP="$(basename "$LATEST_SPEC" | sed -E 's/.*(20[0-9]{2}[01][0-9][0-3][0-9]T[0-2][0-9][0-5][0-9][0-5][0-9]).*/\1/')"
if [ -z "$STAMP" ]; then
  log "  ! failed to extract timestamp from spec name."; exit 4
fi
log "  - STAMP: $STAMP"

# --------------------------------------------
# 5) 対象だけ pytest 実行
# --------------------------------------------
log "[5/5] 該当Specだけ pytest 実行（-k $STAMP）"
pytest -q -k "$STAMP" --maxfail=1 -rA || true

echo
echo "=== Next ==="
echo "1) SPECを開いて対象ファイル（例: noctria_gui/main.py）を実装"
echo "2) 再度: pytest -q -k \"$STAMP\""
