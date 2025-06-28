import os
import re
from pathlib import Path

ROOT = Path("/mnt/d/noctria-kingdom")
OLD_PATH = "/mnt/d/"
NEW_PATH = "/mnt/d/"

# 対象ファイル拡張子
target_exts = [".py", ".sh", ".yaml", ".yml", ".env", ".txt", ".md"]

def scan_file(file_path):
    with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    found = []
    for idx, line in enumerate(lines):
        if OLD_PATH in line:
            found.append((idx + 1, line.strip()))
    return found

def walk_and_scan(root_dir):
    report = []
    for path in root_dir.rglob("*"):
        if path.is_file() and path.suffix in target_exts:
            hits = scan_file(path)
            if hits:
                report.append({
                    "file": str(path.relative_to(ROOT)),
                    "matches": hits
                })
    return report

if __name__ == "__main__":
    results = walk_and_scan(ROOT)
    for entry in results:
        print(f"\n📄 {entry['file']}")
        for lineno, line in entry["matches"]:
            print(f"  L{lineno}: {line}")
            print(f"  👉 修正候補: {line.replace(OLD_PATH, NEW_PATH)}")

    print(f"\n✅ 検出完了：{len(results)}ファイルに旧パスが含まれています。")
