import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UNDEF_FILE = os.path.join(BASE_DIR, "undefined_symbols.txt")
KNOWLEDGE_PATH = os.path.join(BASE_DIR, "..", "docs", "knowledge.md")
PROMPT_OUT = os.path.join(BASE_DIR, "ai_prompt_fix_missing.txt")

if not os.path.exists(UNDEF_FILE):
    raise FileNotFoundError(f"{UNDEF_FILE} が見つかりません")
if not os.path.exists(KNOWLEDGE_PATH):
    raise FileNotFoundError(f"{KNOWLEDGE_PATH} が見つかりません")

with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
    knowledge = f.read()

with open(UNDEF_FILE, "r", encoding="utf-8") as f:
    missing = f.read().strip()

if not missing:
    missing = "未定義シンボルはありません。"

timestamp = datetime.now().isoformat()

prompt = f"""
【Noctria Kingdom自動補完指示】【生成日時: {timestamp}】
- 下記「knowledge.md」（開発ルール）を厳守せよ。
- pytestの「未定義/未実装」クラス・関数・変数をすべて定義/実装せよ。
- 各コードは「# ファイル名: xxx.py」ヘッダー必須。
- path_config.pyのみ src/core/path_config.py に、他は generated_code/直下に必ず上書き。
- 生成先ディレクトリは絶対にネスト禁止（generated_code/generated_code等を作らないこと）。
- 新たな説明文や余計なコメント、Markdown囲みは絶対に書かない。
- すべてPEP8/型アノテーション・命名規則厳守。
- テストコードはtest_*.py, 本体コードは*.py、ドキュメントは絶対.py化しない。
- コード定義がpytestで通るまで正確に補完せよ。命名ブレや型違反がないかも点検。
- OSや環境依存の記述は排除すること。

---
【knowledge.md】
{knowledge}

---
【未定義シンボル/未実装クラス・関数・変数リスト】
{missing}
---
"""

with open(PROMPT_OUT, "w", encoding="utf-8") as f:
    f.write(prompt.rstrip())

print(f"AI用プロンプトを {PROMPT_OUT} に生成しました！")
