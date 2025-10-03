#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
PY="${PYTHON:-python3}"

OUT_DIR_DATA="${OUT_DIR_DATA:-${ROOT}/data}"
OUT_DIR_GRAPH="${OUT_DIR_GRAPH:-${ROOT}/codex_reports/graphs}"
ROLES_FILE="${ROLES_FILE:-${ROOT}/tools/workflow_roles.yml}"
MANIFEST_FILE="${MANIFEST_FILE:-${ROOT}/tools/workflow_manifest.yml}"

mkdir -p "${OUT_DIR_DATA}" "${OUT_DIR_GRAPH}"
TS="$(date +%Y%m%d_%H%M%S)"

MMD_RAW="${OUT_DIR_DATA}/repo_dependencies.mmd"
MMD_TAGGED="${OUT_DIR_DATA}/repo_dependencies_tagged.mmd"
SPINE_JSON="${OUT_DIR_DATA}/workflow_spine_top.json"
SPINE_MD="${OUT_DIR_DATA}/workflow_spine_top.md"
SVG_OUT="${OUT_DIR_GRAPH}/repo_dependencies_tagged.svg"

for f in "${MMD_RAW}" "${MMD_TAGGED}" "${SPINE_JSON}" "${SPINE_MD}" "${SVG_OUT}"; do
  [[ -f "$f" ]] && cp -a "$f" "$f.$TS.bak" || true
done

echo "[1/4] generate .mmd"
"${PY}" "${ROOT}/tools/scan_repo_to_mermaid.py" \
  --root "${ROOT}" \
  --output "${MMD_RAW}" \
  --exclude "_graveyard/**" \
  --exclude "venv*/**" \
  --exclude ".git/**" \
  --exclude "node_modules/**" \
  --exclude "__pycache__/**" \
  --exclude ".mypy_cache/**" \
  --exclude ".pytest_cache/**" \
  --exclude "logs/**" \
  --exclude "data/**/cache/**"

echo "[2/4] quick roles overlay (temp) for stage info"
# 一旦、manifest抜きでクラスを付けて解析に使う（ステージ橋渡し判定のため）
TMP_MMD="${MMD_RAW%.mmd}.tmp_for_spine.mmd"
"${PY}" "${ROOT}/tools/overlay_roles_to_mermaid.py" \
  --input "${MMD_RAW}" \
  --roles "${ROLES_FILE}" \
  --output "${TMP_MMD}"

echo "[3/4] analyze spine"
"${PY}" "${ROOT}/tools/analyze_workflow_spine.py" \
  --input "${TMP_MMD}" \
  --json_out "${SPINE_JSON}" \
  --md_out "${SPINE_MD}" \
  --topk 40

echo "[4/4] final overlay (roles + manifest + spine)"
"${PY}" "${ROOT}/tools/overlay_roles_to_mermaid.py" \
  --input "${MMD_RAW}" \
  --roles "${ROLES_FILE}" \
  --manifest "${MANIFEST_FILE}" \
  --spine-json "${SPINE_JSON}" \
  --output "${MMD_TAGGED}"

# SVG（任意）
if command -v mmdc >/dev/null 2>&1; then
  mmdc -i "${MMD_TAGGED}" -o "${SVG_OUT}" -b transparent || echo "warn: mmdc failed"
else
  echo "hint: npm i -g @mermaid-js/mermaid-cli && mmdc -i '${MMD_TAGGED}' -o '${SVG_OUT}'"
fi

echo "done."
echo "  spine list : ${SPINE_MD}"
echo "  MMD tagged : ${MMD_TAGGED}"
[[ -f "${SVG_OUT}" ]] && echo "  SVG        : ${SVG_OUT}" || true
