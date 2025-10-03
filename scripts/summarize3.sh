#!/usr/bin/env bash
set -euo pipefail

# ========== オプション解析（--format=json） ==========
FORMAT="text"
if [[ "${1-}" == "--format=json" ]]; then
  FORMAT="json"
  shift
fi

# ========== 設定 ==========
API=${API:-http://127.0.0.1:8005/v1/chat/completions}
MODELS=${MODELS:-"qwen2.5:3b-instruct-q4_K_M,phi3:mini"}

# system プロンプト（制約）
SYS="あなたは日本語のみで回答する。前置きや説明は禁止。各行は五十字以内、全角句点「。」で終える。三行ちょうど出力。体言止め可。英字・半角記号は使わない。"

# user プロンプト（役割を明示）
PROMPT_PREFIX=$'次の本文を三行で要約せよ。厳守: 三行のみ、各行五十字以内、全角句点で終える。英単語や半角記号は禁止。各行の役割は次のとおり。\n1行目: ノクトリアのキングオプスの目的（運用ガバナンス自動化）。\n2行目: 意思決定の履歴化・ＫＰＩレビュー・変更管理の標準化とばらつき低減。\n3行目: ＳＬＯ監視と監査ログ連携、問題の早期検知と説明責任の両立。\n本文:\n---\n'
PROMPT_SUFFIX=$'\n---\n出力フォーマット:\n1) \n2) \n3) '

# 入力本文
body_file="${1:-/dev/stdin}"
BODY=$(cat "$body_file")

# メトリクス出力先
mkdir -p runs

# 一時ファイル
tmp=$(mktemp)

# ========== モデルを順番に試行 ==========
for model in ${MODELS//,/ }; do
  # リクエスト生成
  jq -n \
    --arg sys "$SYS" \
    --arg body "$BODY" \
    --arg pre "$PROMPT_PREFIX" \
    --arg suf "$PROMPT_SUFFIX" \
    --arg model "$model" \
    '{
      model: $model,
      messages: [
        {role:"system", content:$sys},
        {role:"user",   content: ($pre + $body + $suf)}
      ],
      stream: false,
      temperature: 0.0,
      top_p: 1.0
    }' > "$tmp"

  # 推論
  resp=$(curl -sS --fail "$API" -H 'Content-Type: application/json' --data-binary @"$tmp" || true)
  [[ -n "$resp" ]] || continue

  # コンテンツと使用トークン
  content=$(echo "$resp" | jq -r '.choices[0].message.content // empty')
  usage=$(echo "$resp"   | jq -c '{prompt:.usage.prompt_tokens, completion:.usage.completion_tokens, total:.usage.total_tokens}')
  [[ -n "$content" ]] || continue

  # ========== 出力の検証・整形・全角化 ==========
  fixed=$(
python3 - "$content" <<'PY'
import sys, re
txt = sys.argv[1].strip()

# 行抽出（空行は除外）
lines = [l for l in txt.splitlines() if l.strip()]

# 行数が3でなければ不合格（空文字を返してシェル側で次モデルへ）
if len(lines) != 3:
    print("", end=""); sys.exit(2)

# 各行: 末尾全角句点を保証、50字制約に収める
def ensure_period_and_limit(s: str, limit: int = 50) -> str:
    s = s.rstrip()
    if not s.endswith("。"):
        s = s + "。"
    if len(s) > limit:
        s = s[:limit-1] + "。"
    return s

lines = [ensure_period_and_limit(l) for l in lines]

# ASCII 混入があれば全角化（半角空白も全角に）
def to_zenkaku(t: str) -> str:
    out = []
    for ch in t:
        o = ord(ch)
        if ch == ' ':
            out.append('　')
        elif 0x21 <= o <= 0x7E:
            out.append(chr(o + 0xFEE0))
        else:
            out.append(ch)
    return ''.join(out)

if any(re.search(r'[\x00-\x7F]', l) for l in lines):
    lines = [to_zenkaku(l) for l in lines]

print('\n'.join(lines))
PY
  )

  # 合格（非空）なら出力
  if [[ -n "$fixed" ]]; then
    if [[ "$FORMAT" == "json" ]]; then
      # JSON配列で返したい場合は、行頭の番号（１）など）を除去して JSON 化
      python3 - <<'PY' "$fixed"
import sys, re, json
txt = sys.argv[1]
lines = [l for l in txt.splitlines() if l.strip()]

# 先頭の番号・記号（全角／半角）と全角スペースを除去
clean = [re.sub(r'^[ 　]*([0-9１２３]+)[\)\]）］】．｡:]?[ 　]*', '', l).strip() for l in lines]

print(json.dumps(clean, ensure_ascii=False))
PY
    else
      # テキスト（従来形式）
      echo "$fixed"
    fi

    # メトリクス記録
    ts=$(date -Iseconds)
    echo "$ts,$model,$usage" >> runs/metrics.csv

    rm -f "$tmp"
    exit 0
  fi
done

# すべて不合格
rm -f "$tmp"
echo "要約に失敗しました（全モデル不合格）" >&2
exit 1

