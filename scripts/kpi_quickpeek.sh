#!/usr/bin/env bash
set -euo pipefail
: "${NOCTRIA_OBS_PG_DSN:?set NOCTRIA_OBS_PG_DSN}"

psql "$NOCTRIA_OBS_PG_DSN" -c "
WITH latest_run AS (
  SELECT meta->>'run_id' AS run_id
  FROM obs_codex_kpi
  WHERE agent='Prometheus' AND meta ? 'run_id'
  ORDER BY created_at DESC
  LIMIT 1
)
SELECT
  k.metric,
  round(k.value::numeric,4) AS v,
  k.meta->'calibration'->>'objective'   AS obj,
  k.meta->'calibration'->>'temperature' AS T,
  k.meta->'calibration'->>'bins'        AS bins,
  k.created_at
FROM obs_codex_kpi k
JOIN latest_run r ON r.run_id = k.meta->>'run_id'
WHERE k.agent='Prometheus'
ORDER BY k.metric;
"
