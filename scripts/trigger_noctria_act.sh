# -------------------------------------------------------------------
# File: scripts/trigger_noctria_act.sh
# -------------------------------------------------------------------
# 手動トリガ用（Airflow Webserverコンテナ内で実行 or docker compose 経由）
# 例:
#   bash scripts/trigger_noctria_act.sh '{"LOOKBACK_DAYS": 30, "WINRATE_MIN_DELTA_PCT": 3, "MAX_DD_MAX_DELTA_PCT": 2, "DRY_RUN": false}'
#!/usr/bin/env bash
set -euo pipefail

CONF_JSON="${1:-{}}"
AIRFLOW_COMPOSE_FILE="airflow_docker/docker-compose.yaml"

docker compose -f "${AIRFLOW_COMPOSE_FILE}" exec airflow-webserver \
  airflow dags trigger noctria_act_pipeline --conf "${CONF_JSON}"
