import os
import json

ROOT_DIR = "/noctria_kingdom"
OUTPUT_PATH = os.path.join(ROOT_DIR, "logs", "refactor_plan.json")

# ❗無視するフォルダやファイル
IGNORED_DIRS = {"__pycache__", ".git", ".venv", "venv", ".idea", ".mypy_cache"}
IGNORED_FILES = {".DS_Store", "Thumbs.db", "dummy"}

def should_ignore(name):
    return name in IGNORED_DIRS or name in IGNORED_FILES

def scan_structure(root_dir):
    plan = []

    for dirpath, dirnames, filenames in os.walk(root_dir):
        # 無視対象の除外
        dirnames[:] = [d for d in dirnames if not should_ignore(d)]

        # ファイルごとの処理
        for filename in filenames:
            if should_ignore(filename):
                continue

            file_path = os.path.join(dirpath, filename)
            relative_path = os.path.relpath(file_path, root_dir)

            # 移動対象の候補例（戦略ファイルは veritas_generated へ）
            if "strategies" in relative_path and "veritas" not in relative_path:
                if filename.endswith(".py") and "test" not in filename:
                    suggested_path = os.path.join("strategies", "veritas_generated", filename)
                    plan.append({
                        "src": relative_path,
                        "dst": suggested_path,
                        "reason": "Move to veritas_generated for consolidation",
                    })

            # 絶対パス参照の修正対象なども検出可（今後拡張）

    return plan

def main():
    plan = scan_structure(ROOT_DIR)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(plan, f, indent=2)

    print(f"✅ リファクタリング計画を出力: {OUTPUT_PATH}")
    print(f"🧩 対象ファイル数: {len(plan)} 件")

if __name__ == "__main__":
    main()
