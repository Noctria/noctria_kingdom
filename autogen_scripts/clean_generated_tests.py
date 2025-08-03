import os
import re

FOLDER = "./generated_code"  # ここは必要に応じてパス修正

for fname in os.listdir(FOLDER):
    if fname.startswith("test_") and fname.endswith(".py"):
        path = os.path.join(FOLDER, fname)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        # 1. ```～``` で囲まれた部分を全部削除
        code = re.sub(r"```[\s\S]*?```", "", code)
        # 2. ファイル冒頭や途中の「# で始まる行」「説明文」も全部削除
        code = re.sub(r"^#.*$\n?", "", code, flags=re.MULTILINE)
        code = re.sub(r"^(\s*以下に.*$)|(^\s*ファイル名:.*$)|(^\s*目的:.*$)|(^\s*説明責任.*$)|(^\s*テストケース名:.*$)|(^\s*異常系.*$)|(^\s*正常系.*$)|(^\s*期待される結果.*$)|(^\s*また、.*$)", "", code, flags=re.MULTILINE)
        # 3. 連続する空行を1つにまとめる
        code = re.sub(r"\n{3,}", "\n\n", code)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code.strip() + "\n")

print("All test_*.py files cleaned.")
