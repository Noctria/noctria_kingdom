#!/usr/bin/env bash
set -euo pipefail

cmd="${1:-help}"

# 文字コード（日本語/スペース含むパスでも安定）
export LC_ALL=C.UTF-8 || true
export LANG=C.UTF-8 || true

_has_cmd() { command -v "$1" >/dev/null 2>&1; }

normalize_autodoc_perl() {
  # NULL 区切りで安全に全 .md を処理
  git ls-files -z -- 'docs/**/*.md' 'docs/*.md' | while IFS= read -r -d '' f; do
    perl -0777 -pe 's/(<!--\s*AUTODOC:END\s*-->)(\s*\R(<!--\s*AUTODOC:END\s*-->))+/$1\n/g' -i "$f"
  done
  echo "✅ AUTODOC END normalized. (perl)"
}

normalize_autodoc_python() {
python3 - <<'PY'
import subprocess, re, sys, os
try:
    files = subprocess.check_output(
        ["git","ls-files","-z","--","docs/**/*.md","docs/*.md"]
    ).split(b'\x00')
except subprocess.CalledProcessError as e:
    print("ERR: git ls-files failed", e, file=sys.stderr)
    sys.exit(1)

pattern = re.compile(rb'(<!--\s*AUTODOC:END\s*-->)(?:\s*\r?\n(<!--\s*AUTODOC:END\s*-->))+')
changed = 0
for b in files:
    if not b: 
        continue
    p = b.decode('utf-8', errors='ignore')
    if not os.path.exists(p):
        continue
    with open(p,'rb') as f:
        data = f.read()
    new = pattern.sub(rb'\1\n', data)
    if new != data:
        with open(p,'wb') as f:
            f.write(new)
        changed += 1

print(f"✅ AUTODOC END normalized. (python) files_changed={changed}")
PY
}

normalize_autodoc() {
  if _has_cmd perl; then
    if ! normalize_autodoc_perl; then
      echo "perl 方式で失敗。python フォールバックを試みます"
      normalize_autodoc_python
    fi
  else
    normalize_autodoc_python
  fi
}

_check_each_file() {
  local f="$1"
  # Bash 側での除外（rg の -g に頼らず二重ガード）
  case "$f" in
    */_generated/*|*/_partials/*|*.bak|*~|*.tmp) return 0 ;;  # 無視対象
  esac
  # 参照元そのものは除外
  if [[ "$f" == "docs/architecture/contracts/OrderRequest.md" ]]; then
    return 0
  fi
  if _has_cmd rg; then
    rg -q 'idempotency_key' -- "$f" || echo "WARN: $f mentions OrderRequest but no idempotency_key"
  else
    grep -q "idempotency_key" "$f" || echo "WARN: $f mentions OrderRequest but no idempotency_key"
  fi
}

check_docs() {
  echo "== Noctria docs CHECK =="
  echo "--- Check: files mentioning OrderRequest but missing idempotency_key"

  if _has_cmd rg; then
    # OrderRequest を含むファイルを NULL 区切りで列挙
    rg -Il0 -g 'docs/**' 'OrderRequest' | while IFS= read -r -d '' f; do
      _check_each_file "$f"
    done

    echo "--- Grep: idempotency_key hits (first 200)"
    rg -n "idempotency_key" docs | head -n 200 || true
  else
    # フォールバック：grep -R
    grep -RIl "OrderRequest" docs | while IFS= read -r f; do
      _check_each_file "$f"
    done
    echo "--- Grep: idempotency_key hits (first 200)"
    grep -RIn "idempotency_key" docs | head -n 200 || true
  fi
}

case "$cmd" in
  fix)   normalize_autodoc ;;
  check) check_docs ;;
  *)     echo "Usage: $0 {check|fix}"; exit 2 ;;
esac
