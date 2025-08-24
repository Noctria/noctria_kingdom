#!/usr/bin/env bash
set -euo pipefail

SQL_FILE="${1:-migrations/20250824_add_idempo_ledger.sql}"
CONTAINER="${POSTGRES_CONTAINER:-noctria_postgres}"

if [[ ! -f "$SQL_FILE" ]]; then
  echo "❌ ERR: SQL file not found: $SQL_FILE" >&2
  exit 1
fi

# コンテナ内の環境変数を確認
PGUSER=$(docker exec "$CONTAINER" bash -lc 'printf "%s" "${POSTGRES_USER:-postgres}"')
PGDB=$(docker exec "$CONTAINER"   bash -lc 'printf "%s" "${POSTGRES_DB:-postgres}"')
PGPASS=$(docker exec "$CONTAINER" bash -lc 'printf "%s" "${POSTGRES_PASSWORD:-}"')

echo "== Apply migration =="
echo "Container: $CONTAINER"
echo "Database : $PGDB"
echo "User     : $PGUSER"

if [[ -n "$PGPASS" ]]; then
  echo "(Using password from container env)"
  PGPASS_OPT=(-e "PGPASSWORD=$PGPASS")
else
  echo "(No password env; peer/trust auth may be used)"
  PGPASS_OPT=()
fi

# SQL を流し込み
cat "$SQL_FILE" | docker exec -i "${PGPASS_OPT[@]}" "$CONTAINER" \
  psql -v ON_ERROR_STOP=1 -U "$PGUSER" -d "$PGDB" -f -

# 結果確認
docker exec "${PGPASS_OPT[@]}" "$CONTAINER" \
  psql -U "$PGUSER" -d "$PGDB" -c "\dt+ idempo_ledger" || true
