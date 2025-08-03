import os

UNDEF_FILE = "autogen_scripts/undefined_symbols.txt"   # find_undefined_symbols.py の出力
KNOWLEDGE_PATH = "docs/knowledge.md"
PROMPT_OUT = "autogen_scripts/ai_prompt_fix_missing.txt"

# 1. knowledge.mdのロード
with open(KNOWLEDGE_PATH, "r", encoding="utf-8") as f:
    knowledge = f.read()

# 2. 未定義シンボルリストのロード
with open(UNDEF_FILE, "r", encoding="utf-8") as f:
    missing = f.read().strip()

# 3. AI用プロンプト組み立て
prompt = f"""
【Noctria Kingdom自動補完指示】
- 下記の「knowledge.md」（開発ルール）を厳守せよ。
- 現在pytestで「未定義/未実装」となっているクラス・関数・変数リストをすべて定義/実装せよ。
- 各コードは必ず「# ファイル名: xxx.py」ヘッダーをつけ、generated_code/配下に追加・上書きすること。
- 新たな説明文や余計なコメント、Markdown囲みは絶対に書かない。
- すべての定義は型アノテーション・PEP8厳守で書くこと。
- 実装不足・型違反・命名不一致がないかも自動で点検し、確実にpytestを通る水準で補完せよ。

---
【knowledge.md】
{knowledge}

---
【未定義シンボル/未実装クラス・関数・変数リスト】
{missing}
---
"""

with open(PROMPT_OUT, "w", encoding="utf-8") as f:
    f.write(prompt.strip())

print(f"AI用プロンプトを {PROMPT_OUT} に生成しました！")
