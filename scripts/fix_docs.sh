#!/usr/bin/env bash
set -euo pipefail

echo "== 0) 前提: jq/rg が無くても動くように純bash/sed/perlのみで実装 =="

# 1) .bak を追跡から外す（スペース対応）
if ! grep -qE '^\*\.bak$' .gitignore 2>/dev/null; then
  echo '*.bak' >> .gitignore
fi
git ls-files -z '*.bak' | xargs -0 -r git rm --cached

# 2) AUTODOC マーカーの連続重複を正規化（連続 END/BEGIN を 1 個に圧縮）
#   - END の3連打などを1つに圧縮
#   - BEGIN も同様（無害な正規化）
echo "== 2) AUTODOC マーカーの重複圧縮 =="
find docs -type f -name '*.md' -print0 | xargs -0 -I{} \
  perl -0777 -pe '
    s/(<!--\s*AUTODOC:END\s*-->\s*){2,}/<!-- AUTODOC:END -->\n/g;
    s/(<!--\s*AUTODOC:BEGIN\b[^>]*-->\s*){2,}/$1/g;
  ' -i {}

# 3) 本文に紛れた diff パッチ断片を除去
#    以下の見出しから始まる「パッチ行」を落とす。
#    - ^diff --git
#    - ^index [0-9a-f]+\.\.
#    - ^@@ -d+,d+ \+d+,d+ @@
#    - ^\+\+\+ | ^---   ← これはパッチヘッダだけに限定
#    注: 先頭が '+' や '-' の通常Markdown箇条書きは消さないように精密マッチ。
echo "== 3) diff パッチ断片の除去 =="
while IFS= read -r -d '' f; do
  awk '
    # パッチのヘッダ/ハンク記法の行だけスキップする
    /^[[:space:]]*diff --git / {next}
    /^[[:space:]]*index [0-9a-f]+\.\.[0-9a-f]+/ {next}
    /^@@ -[0-9]+,[0-9]+ \+[0-9]+,[0-9]+ @@/ {next}
    /^[[:space:]]*\+\+\+ / {next}
    /^[[:space:]]*--- / {next}
    {print}
  ' "$f" > "$f.__tmp__" && mv "$f.__tmp__" "$f"
done < <(rg -l '(^diff --git |^index [0-9a-f]{7,}\.\.|^@@ -[0-9]+,[0-9]+ \+[0-9]+,[0-9]+ @@|^\+\+\+ |^--- )' -n docs -0)

# 4) 余計な「 @@ 」が紛れ込んだ mermaid を軽く修復（よくある壊れ方の局所修正）
echo "== 4) mermaid の誤挿入された @@ を緩和（best-effort） =="
find docs -type f -name '*.md' -print0 | xargs -0 -I{} \
  perl -0777 -pe '
    s/(mermaid\s*\n[^\n]*?)\s*@@\s*/$1\n/g;
  ' -i {}

# 5) 仕上げ：再検査（発見のみ）
echo "== 5) 再検査 =="
echo "-- AUTODOC BEGIN/END の重複（残っていれば要手修正） --"
rg -n "AUTODOC:BEGIN|AUTODOC:END" docs | awk -F: '{print $1}' | sort | uniq -c | awk '"'"'$1>50{print "多すぎ?: "$2" ("$1")"}'"'"' || true

echo "-- diff 断片 残存チェック --"
rg -n "(@@ -[0-9]+,[0-9]+ \+[0-9]+,[0-9]+ @@|^diff --git|^index [0-9a-f]{7,}\.\.)" docs || true

echo "== 完了。内容を確認して commit/push してください。 =="
