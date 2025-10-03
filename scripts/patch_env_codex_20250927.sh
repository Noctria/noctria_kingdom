#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

ts=$(date +%Y%m%d_%H%M%S)
[ -f .env ] && cp -a .env ".env.bak.${ts}"

# 1) .env を既定内容で上書き（上の「マージ後 .env」本文を here-doc で生成）
cat > .env <<'ENVEOF'
# (上記「マージ後 .env」本文をここにそのまま貼り付け)
ENVEOF

# 2) .env.secret を用意（既存を壊さない）
if [ ! -f .env.secret ]; then
  cat > .env.secret <<'SECEOF'
# .env.secret  (git未追跡にすること)
OPENAI_API_KEY=REPLACE_ME
SECEOF
  echo "[init] created .env.secret (remember to put real OPENAI_API_KEY here)"
fi

# 3) .gitignore に .env.secret が無ければ追記
if ! grep -qE '(^|/)\.env\.secret$' .gitignore 2>/dev/null; then
  echo ".env.secret" >> .gitignore
  echo "[fix] appended .env.secret to .gitignore"
fi

echo "[ok] .env updated and .env.secret ensured. Backup: .env.bak.${ts} (if existed)"
