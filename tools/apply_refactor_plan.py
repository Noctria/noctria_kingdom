# tools/apply_refactor_plan.py

import os
import json
from pathlib import Path
from core.path_config import BASE_DIR

def apply_plan():
    plan_path = BASE_DIR / "logs" / "refactor_plan.json"
    if not plan_path.exists():
        print(f"❌ refactor_plan.json が見つかりません: {plan_path}")
        return

    with open(plan_path, "r") as f:
        plan = json.load(f)

    total = 0

    print("⚠️ 実行前に確認してください：このスクリプトは以下を削除します")
    print("------------------------------------------------------------")

    for category in ["delete", "duplicate", "git_internal"]:
        items = plan.get(category, [])
        print(f"🗂 {category} ({len(items)} 件):")
        for p in items:
            print(f"  - {p}")
        total += len(items)

    print("------------------------------------------------------------")
    confirm = input(f"❓ {total} 件を削除してもよろしいですか？ (yes/no): ").strip().lower()
    if confirm != "yes":
        print("⏹ キャンセルされました")
        return

    deleted = 0
    for category in ["delete", "duplicate", "git_internal"]:
        for p in plan.get(category, []):
            path = Path(p)
            try:
                if path.is_dir():
                    os.system(f"rm -rf \"{path}\"")
                elif path.is_file():
                    path.unlink()
                deleted += 1
            except Exception as e:
                print(f"❌ 削除失敗: {p} ({e})")

    print(f"✅ リファクタ完了: {deleted} 件削除済み")

if __name__ == "__main__":
    apply_plan()
