import os
import re

# 検査対象ディレクトリ
TARGET_DIRS = [
    "src/core",
    "src/strategies",
    "src/plan_data"
]

# NGパターン集（検出したいパス操作）
PATTERNS = [
    r"from pathlib import Path",
    r"import os",
    r"os\.path\.",
    r"Path\(__file__\)",            # __file__からのパス計算
    r"Path\([\"']/",                # 絶対パス直書き
    r"os\.path\.join",
    r"os\.path\.dirname",
    r"os\.path\.abspath",
    r"os\.getcwd",
    r"os\.chdir",
    r"open\(.+[\"']/",              # 絶対パスでファイルを開いてる
    r"Path\.home\(",
    r"Path\.parent",                # ただしpath_config経由のものはOK
    # 必要に応じて追加
]

# path_configからimportしているか検出（ホワイトリスト化用）
PATHCONFIG_IMPORT_PATTERN = r"from +src\.core\.path_config +import"

def scan_file(filepath):
    results = []
    pathconfig_imported = False

    with open(filepath, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            if re.search(PATHCONFIG_IMPORT_PATTERN, line):
                pathconfig_imported = True

    with open(filepath, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            for pat in PATTERNS:
                if re.search(pat, line):
                    # path_configからimportしていない場合のみ警告
                    if not pathconfig_imported or "path_config" not in line:
                        results.append((i, line.strip()))
    return results

def main():
    hit = False
    for target in TARGET_DIRS:
        for root, _, files in os.walk(target):
            for file in files:
                if file.endswith(".py"):
                    filepath = os.path.join(root, file)
                    res = scan_file(filepath)
                    if res:
                        hit = True
                        print(f"\n🔎 {filepath}")
                        for lineno, code in res:
                            print(f"  {lineno:4d}: {code}")
    if not hit:
        print("✅ path_config.py 経由以外のPath演算は見つかりませんでした。")

if __name__ == "__main__":
    main()
