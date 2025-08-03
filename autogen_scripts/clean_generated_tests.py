import os
import re

FOLDER = "./generated_code"

for fname in os.listdir(FOLDER):
    if fname.endswith(".py"):
        path = os.path.join(FOLDER, fname)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        # マークダウン除去
        code = re.sub(r"```python\s*([\s\S]*?)```", "", code, flags=re.MULTILINE)
        code = re.sub(r"```[\s\S]*?```", "", code, flags=re.MULTILINE)
        code = re.sub(r"^```python\s*$", "", code, flags=re.MULTILINE)
        code = re.sub(r"^```\s*$", "", code, flags=re.MULTILINE)
        # 説明/日本語・不要な文章（「ここでは」「目的」「これらのテスト」など汎用除去）
        code = re.sub(r"^#.*$\n?", "", code, flags=re.MULTILINE)
        code = re.sub(r"^(以下に.*$|ファイル名:.*$|目的:.*$|説明責任.*$|テストケース名:.*$|異常系.*$|正常系.*$|期待される結果.*$|また、.*$|これらの.*$|ここでは.*$)", "", code, flags=re.MULTILINE)
        # 連続空行を1つに
        code = re.sub(r"\n{3,}", "\n\n", code)
        with open(path, "w", encoding="utf-8") as f:
            f.write(code.strip() + "\n")

print("All *.py files in generated_code/ cleaned of markdown, Japanese explanation, and stray comments.")
