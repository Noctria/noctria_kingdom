#!/usr/bin/env bash
set -euo pipefail

# --- settings / env ---
: "${NOCTRIA_OBS_PG_DSN:?set NOCTRIA_OBS_PG_DSN}"
export PYTHONPATH=.

REPORTS_ROOT="reports/veritas"
EVAL_ARGS=()
LOG_LIMIT=1
PLOT_LIMIT=1
ONLY_LOG_AND_PLOT=0

usage() {
  cat <<USAGE
Usage: $0 [options]
  --only-log-plot            評価をスキップしてログ&図のみ
  --reports DIR              レポート親DIR（デフォ: reports/veritas）
  --limit N                  KPI/Plot の対象 run 数（デフォ: 1）
  --                         以降は evaluate_veritas.py にそのまま渡す
例:
  $0 -- --calibrate-temperature --calib-objective both --calib-bins 12
  $0 --only-log-plot --limit 3
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --only-log-plot) ONLY_LOG_AND_PLOT=1; shift;;
    --reports) REPORTS_ROOT="${2}"; shift 2;;
    --limit) LOG_LIMIT="${2}"; PLOT_LIMIT="${2}"; shift 2;;
    -h|--help) usage; exit 0;;
    --) shift; EVAL_ARGS=("$@"); break;;
    *) EVAL_ARGS+=("$1"); shift;;
  esac
done

# --- 1) evaluate ---
if [[ "${ONLY_LOG_AND_PLOT}" -eq 0 ]]; then
  echo "[pipeline] run evaluator"
  python src/veritas/evaluate_veritas.py "${EVAL_ARGS[@]}"
fi

# --- 2) latest symlink ---
latest_dir="$(ls -dt "${REPORTS_ROOT}"/run_* 2>/dev/null | head -n1 || true)"
if [[ -n "${latest_dir}" ]]; then
  ln -sfn "${latest_dir}" "${REPORTS_ROOT}/latest"
  echo "[pipeline] latest -> ${latest_dir}"
else
  echo "[pipeline] no runs under ${REPORTS_ROOT}; abort."
  exit 1
fi

# --- 3) KPI log ---
echo "[pipeline] log KPIs (limit=${LOG_LIMIT})"
python scripts/log_kpi_from_reports.py --reports "${REPORTS_ROOT}" --limit "${LOG_LIMIT}"

# --- 4) Reliability plots ---
echo "[pipeline] plot reliability (limit=${PLOT_LIMIT})"
python scripts/plot_reliability.py --reports "${REPORTS_ROOT}" --limit "${PLOT_LIMIT}"

# --- 5) Quick peek ---
if [[ -x scripts/kpi_quickpeek.sh ]]; then
  ./scripts/kpi_quickpeek.sh
else
  echo "[pipeline] (hint) create scripts/kpi_quickpeek.sh for SQL summary"
fi

echo "[pipeline] done."
