import os
import re

FOLDER = "./generated_code"

for fname in os.listdir(FOLDER):
    if fname.endswith(".py"):
        path = os.path.join(FOLDER, fname)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        # Markdown箇条書きや見出し行などを除去
        code = re.sub(r"^(\s*- .+|#+ .+|> .+|[*_]{2,}.+|---.*|`{3,}.*)$", "", code, flags=re.MULTILINE)
        # 全角記号や日本語で始まる説明行も除去（前スクリプト強化）
        code = re.sub(r"^[\u3000-\u303F\u3040-\u30FF\u4E00-\u9FFFぁ-んァ-ヶー。、．,.：#>【】]+.*$", "", code, flags=re.MULTILINE)
        # 連続空行1つに
        code = re.sub(r"\n{3,}", "\n\n", code)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code.strip() + "\n")
print("Markdown/explanation cleaned from generated_code/*.py")
