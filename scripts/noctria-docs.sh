#!/usr/bin/env bash
set -Eeuo pipefail
set +H
IFS=$'\n\t'

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT"

command -v rg >/dev/null || { echo "ripgrep (rg) が必要です"; exit 1; }

note_order_v11='> NOTE: この文書で言う **OrderRequest** は **v1.1（idempotency_key 追加）** を前提とします。詳細は `docs/architecture/contracts/OrderRequest.md` を参照。'

insert_note_after_first_h1() {
  local f="$1" note="$2"
  rg -qF "$note" "$f" && return 0
  awk -v note="$note" '
    BEGIN{ins=0}
    NR==1 {print; next}
    ins==0 && $0 ~ /^# / {print; print ""; print note; print ""; ins=1; next}
    {print}
    END{ if(ins==0){ print ""; print note; print "" } }
  ' "$f" > /tmp/ins.$$ && mv /tmp/ins.$$ "$f"
  echo "PATCHED: inserted NOTE into $f"
}

check() {
  echo "== Noctria docs CHECK =="

  echo "--- Check: files mentioning OrderRequest but missing idempotency_key (excluding contracts/OrderRequest.md)"
  local files missing=0
  files=$(rg -l 'OrderRequest' docs | rg -v 'docs/architecture/contracts/OrderRequest\.md' || true)
  for f in $files; do
    if ! rg -q 'idempotency_key' "$f"; then
      echo "MISSING: $f"
      missing=1
    fi
  done
  [[ $missing -eq 0 ]] && echo "OK: all files mention idempotency_key where OrderRequest appears"

  echo "--- Grep: idempotency_key hits (first 200)"
  rg -n "idempotency_key" docs | sed -n '1,200p' || true

  echo "--- Grep: trace_id hits (first 200)"
  rg -n "trace_id" docs | sed -n '1,200p' || true

  echo "--- Check: 'Error rendering embedded code'"
  rg -n 'Error rendering embedded code' docs || echo "OK: not found"

  echo "--- Check: Mermaid fence balance per file"
  local unbalanced=0
  while IFS= read -r -d '' f; do
    delta=$(awk '
      BEGIN{inm=0}
      /^```mermaid[[:space:]]*$/ {inm++; next}
      /^```[[:space:]]*$/        { if (inm>0) inm--; }
      END{print inm}
    ' "$f")
    if [[ "$delta" -ne 0 ]]; then
      echo "UNBALANCED: $f (delta=$delta)"
      unbalanced=1
    fi
  done < <(find docs -type f \( -name '*.md' -o -name '*.mmd' \) -print0)
  [[ $unbalanced -eq 0 ]] && echo "OK: mermaid fences look balanced"

  echo "--- Check: Architecture-Overview -> PDCA-Spec crosslink"
  if [[ -f docs/architecture/Architecture-Overview.md ]]; then
    if rg -q 'PDCA-Spec\.md' docs/architecture/Architecture-Overview.md; then
      echo "OK: PDCA-Spec crosslink found in Architecture-Overview.md"
    else
      echo "WARN: PDCA-Spec crosslink NOT found in Architecture-Overview.md"
    fi
  fi

  echo "--- Headings count (Architecture-Overview.md)"
  [[ -f docs/architecture/Architecture-Overview.md ]] && \
    awk '/^##[[:space:]]/{c++} END{printf("H2 count: %d\n", (c?c:0))}' docs/architecture/Architecture-Overview.md || true

  echo "== done =="
}

fix() {
  echo "== Noctria docs FIX =="

  # A) Close unbalanced mermaid fences by appending missing ``` at EOF
  while IFS= read -r -d '' f; do
    delta=$(awk '
      BEGIN{inm=0}
      /^```mermaid[[:space:]]*$/ {inm++; next}
      /^```[[:space:]]*$/        { if (inm>0) inm--; }
      END{print inm}
    ' "$f")
    if [[ "$delta" -gt 0 ]]; then
      yes '```' | head -n "$delta" >> "$f"
      echo "FIXED: closed $delta mermaid fence(s) in $f"
    fi
  done < <(find docs -type f \( -name '*.md' -o -name '*.mmd' \) -print0)

  # B) Insert NOTE about OrderRequest v1.1 where idempotency_key is missing
  local files
  files=$(rg -l 'OrderRequest' docs | rg -v 'docs/architecture/contracts/OrderRequest\.md' || true)
  for f in $files; do
    if ! rg -q 'idempotency_key' "$f"; then
      insert_note_after_first_h1 "$f" "$note_order_v11"
    fi
  done

  # C) Add crosslink from Architecture-Overview.md to PDCA-Spec.md if missing
  if [[ -f docs/architecture/Architecture-Overview.md ]]; then
    if ! rg -q 'PDCA-Spec\.md' docs/architecture/Architecture-Overview.md; then
      {
        echo ""
        echo "---"
        echo "**関連:** より詳細な契約・実装方針は [PDCA-Spec.md](./PDCA-Spec.md) を参照。"
      } >> docs/architecture/Architecture-Overview.md
      echo "PATCHED: added PDCA-Spec crosslink to Architecture-Overview.md"
    fi
  fi

  echo "== fix done =="
}

usage(){ echo "Usage: $0 {check|fix}"; }

case "${1:-}" in
  check) check ;;
  fix)   fix && check ;;
  *)     usage; exit 1 ;;
esac
