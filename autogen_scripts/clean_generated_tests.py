import os
import re

FOLDER = "./generated_code"  # 必要なら修正

for fname in os.listdir(FOLDER):
    if fname.startswith("test_") and fname.endswith(".py"):
        path = os.path.join(FOLDER, fname)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        # 1. ```python ... ``` のブロック（複数行対応）を全削除
        code = re.sub(r"```python\s*([\s\S]*?)```", "", code, flags=re.MULTILINE)
        # 2. それ以外の ``` ... ``` で囲まれたブロックも削除
        code = re.sub(r"```[\s\S]*?```", "", code, flags=re.MULTILINE)
        # 3. 「```python」や「```」単独行も消す
        code = re.sub(r"^```python\s*$", "", code, flags=re.MULTILINE)
        code = re.sub(r"^```\s*$", "", code, flags=re.MULTILINE)
        # 4. ファイル冒頭や途中の「# で始まる行」「説明文」も全部削除
        code = re.sub(r"^#.*$\n?", "", code, flags=re.MULTILINE)
        code = re.sub(
            r"^(\s*以下に.*$)|(^\s*ファイル名:.*$)|(^\s*目的:.*$)|(^\s*説明責任.*$)|(^\s*テストケース名:.*$)|(^\s*異常系.*$)|(^\s*正常系.*$)|(^\s*期待される結果.*$)|(^\s*また、.*$)|(^\s*import pytest.*$)",
            "", code, flags=re.MULTILINE)
        # 5. 連続する空行を1つにまとめる
        code = re.sub(r"\n{3,}", "\n\n", code)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code.strip() + "\n")

print("All test_*.py files aggressively cleaned (markdown blocks, single lines, and comments).")
