import os
import re
import argparse
from pathlib import Path

# ==========================================
# 🔧 Noctria Kingdom Path Scanner & Fixer
# ==========================================

# 自動でプロジェクトルートを取得
ROOT = Path(__file__).resolve().parent.parent

# 🔁 置換対象のパス（必要に応じて変更）
OLD_PATH = "/opt/airflow"
NEW_PATH = "/opt/airflow"

# 📂 対象拡張子
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
                    "file": path,
                    "matches": hits
                })
    return report

def apply_fixes(entries):
    for entry in entries:
        path = entry["file"]
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        new_content = content.replace(OLD_PATH, NEW_PATH)
        if new_content != content:
            with open(path, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"✅ 修正: {path.relative_to(ROOT)}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--auto-fix", action="store_true", help="対象ファイルを自動修正")
    args = parser.parse_args()

    results = walk_and_scan(ROOT)

    for entry in results:
        rel_path = entry["file"].relative_to(ROOT)
        print(f"\n📄 {rel_path}")
        for lineno, line in entry["matches"]:
            print(f"  L{lineno}: {line}")
            print(f"  👉 修正候補: {line.replace(OLD_PATH, NEW_PATH)}")

    print(f"\n✅ 検出完了：{len(results)}ファイルに旧パスが含まれています。")

    if args.auto_fix:
        apply_fixes(results)
        print("\n🛠️ すべての対象ファイルを自動修正しました。")
