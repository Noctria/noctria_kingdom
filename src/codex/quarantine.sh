cat > codex_reports/dead_code/quarantine.sh <<'SH'
#!/usr/bin/env bash
set -euo pipefail

GRAVEYARD="${1:-_graveyard/$(date +%F)}"
echo "[info] graveyard dir = ${GRAVEYARD}"
mkdir -p "${GRAVEYARD}"

CSV="codex_reports/dead_code/report.csv"
if [[ ! -f "${CSV}" ]]; then
  echo "[error] ${CSV} not found"; exit 1
fi

header=$(head -n1 "${CSV}")
col_path=$(awk -F, '{
  for(i=1;i<=NF;i++){ if($i=="path"){print i; exit} }
}' <<< "${header}")
if [[ -z "${col_path}" ]]; then echo "[error] path column not found"; exit 1; fi

tail -n +2 "${CSV}" | while IFS= read -r line; do
  categories=$(awk -F, '{print $1}' <<< "${line}")
  if ! grep -Eq '(orphaned|unreferenced|unused_template)' <<< "${categories}"; then
    continue
  fi
  path=$(awk -F, -v idx="${col_path}" '{print $idx}' <<< "${line}")
  path=${path//\"/}

  has_cov=$(awk -F, '{print $(NF-3)}' <<< "${line}")
  runtime_seen=$(awk -F, '{print $(NF-1)}' <<< "${line}")
  if [[ "${has_cov}" == "1" || "${runtime_seen}" == "1" ]]; then
    echo "[skip] ${path} (coverage or runtime_seen)"; continue
  fi

  # __init__.py は “親ディレクトリごと隔離”以外は原則スキップ（誤爆防止）
  if [[ "$(basename "${path}")" == "__init__.py" ]]; then
    echo "[skip] ${path} (__init__.py)"; continue
  fi

  dest="${GRAVEYARD}/${path}"
  mkdir -p "$(dirname "${dest}")"

  if git ls-files --error-unmatch -- "${path}" >/dev/null 2>&1; then
    git mv -f -- "${path}" "${dest}" || {
      mv -f -- "${path}" "${dest}"
      git add -A -- "${dest}"
      git rm -f --cached -- "${path}" 2>/dev/null || true
    }
    echo "[moved:git] ${path} -> ${dest}"
  else
    if [[ -e "${path}" ]]; then
      mv -f -- "${path}" "${dest}"
      git add -A -- "${dest}" || true
      echo "[moved:fs ] ${path} -> ${dest}"
    else
      echo "[miss] ${path}"
    fi
  fi
done

echo "[done] Quarantine completed into ${GRAVEYARD}"
SH
chmod +x codex_reports/dead_code/quarantine.sh
