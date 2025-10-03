from openai import OpenAI
import os, sys
BASE = os.getenv("OPENAI_BASE_URL", "http://127.0.0.1:8012/v1")
MODEL = os.getenv("OPENAI_MODEL", "noctria-king:latest")
RAW = " ".join(sys.argv[1:]) or "今日の優先タスクを3つ、規定フォーマットで。"

RULES = """出力要件（厳守）:
- 前置き/後書き/説明は一切禁止。以下テンプレだけを出す。
- 見出しは必ず「# 本日の優先タスク（3）」から開始。ちょうど3件。
- 各件はこの順序で項目名を明示する:
  1) <タイトル>（所要: X分｜優先度: High/Med/Low｜依存: ...）
     目的:
     手順:
       - $ <具体コマンド>
     検証:
       - <確認手順/コマンド>
     完了条件:
       - <定量/イベント>
     リスク/代替:
       - <失敗と代替>
- 手順には必ず1つ以上の行頭 $ コマンドを含める。パスは仮でも明記。
- 不明箇所は TODO: として明記して前進可能にする。"""

USER = f"""{RULES}

依頼: {RAW}
"""

client = OpenAI(base_url=BASE, api_key="dummy")
resp = client.chat.completions.create(
    model=MODEL,
    messages=[{"role":"user","content": USER}],
    temperature=0.2,
    max_tokens=1200,
)
print(resp.choices[0].message.content)
