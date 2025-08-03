import os
import re

FOLDER = "./generated_code"

# 必要なimportパターン
IMPORT_RULES = [
    {
        "pattern": r"\bpd\.(DataFrame|Series)\b",
        "import": "import pandas as pd"
    },
    {
        "pattern": r"\bTuple\b",
        "import": "from typing import Tuple"
    },
    {
        "pattern": r"\bSequential\b",
        "import": "from keras.models import Sequential"
    },
    # 追加パターンは随時ここに
]

for fname in os.listdir(FOLDER):
    if fname.endswith(".py"):
        path = os.path.join(FOLDER, fname)
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()

        # すでにimportされているものリスト化
        existing_imports = set(re.findall(r"^import (.+)|^from (.+) import", code, flags=re.MULTILINE))
        existing_import_lines = [line.strip() for line in code.splitlines() if line.strip().startswith("import") or line.strip().startswith("from")]
        
        new_imports = []
        for rule in IMPORT_RULES:
            if re.search(rule["pattern"], code) and all(rule["import"] not in l for l in existing_import_lines):
                new_imports.append(rule["import"])

        # 追加がある場合のみ書き換え
        if new_imports:
            # 最初のimport行の前に挿入、なければファイル冒頭に追加
            lines = code.splitlines()
            insert_pos = 0
            for i, line in enumerate(lines):
                if line.strip().startswith("import") or line.strip().startswith("from"):
                    insert_pos = i
                    break
            new_code = lines[:insert_pos] + new_imports + lines[insert_pos:]
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_code) + "\n")
            print(f"[{fname}] fixed imports: {new_imports}")

print("Missing imports check & fix complete!")
