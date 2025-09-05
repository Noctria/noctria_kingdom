# tools/reorganize_docs.py

import os
import shutil

DOCS_DIR = "docs"
os.makedirs(DOCS_DIR, exist_ok=True)

TARGET_KEYWORDS = ["README", "起動", "セットアップ", "構築", "方法", "pip", "Docker", "API", "引継ぎ"]

def should_move(file_name):
    return any(kw in file_name for kw in TARGET_KEYWORDS)

for file in os.listdir("."):
    if os.path.isfile(file) and file.endswith((".md", ".txt")) and should_move(file):
        dest = os.path.join(DOCS_DIR, file)
        print(f"📁 移動: {file} → {dest}")
        shutil.move(file, dest)

print("✅ docs/ への分類完了")
