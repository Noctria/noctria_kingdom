import os
import re

FOLDER = "./generated_code"

for fname in os.listdir(FOLDER):
    if fname.endswith(".py"):
        path = os.path.join(FOLDER, fname)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        # 日本語説明文・全角文字・句読点で始まる/含む行を除去
        code = re.sub(
            r"^(?:(?:[\u3000-\u303F\u3040-\u30FF\u4E00-\u9FFFぁ-んァ-ヶー。、．,.：].*)|(?:.*[。、「」]+.*))$",
            "",
            code,
            flags=re.MULTILINE
        )
        # 連続空行1つに
        code = re.sub(r"\n{3,}", "\n\n", code)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code.strip() + "\n")
print("Japanese/comment explanation cleaned from generated_code/*.py")
