# tools/diagnose_dependencies.py

import os
import ast

TARGET_DIRS = ["veritas", "execution", "tests"]
results = []

def scan_imports(path):
    with open(path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read())
            return [node.module for node in ast.walk(tree) if isinstance(node, ast.Import)] + \
                   [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module]
        except Exception:
            return []

for dir in TARGET_DIRS:
    for root, _, files in os.walk(dir):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                imports = scan_imports(full_path)
                results.append({"file": full_path, "imports": imports})

with open("logs/dependency_report.json", "w") as f:
    import json
    json.dump(results, f, indent=2, ensure_ascii=False)

print("📊 依存関係診断結果: logs/dependency_report.json")
