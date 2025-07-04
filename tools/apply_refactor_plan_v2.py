import os
import json
import shutil
from pathlib import Path

PLAN_PATH = "logs/refactor_plan.json"

def delete_path(path):
    try:
        if os.path.isdir(path):
            shutil.rmtree(path)
        elif os.path.isfile(path):
            os.remove(path)
        print(f"🗑️ 削除: {path}")
    except Exception as e:
        print(f"⚠️ 削除失敗: {path} ({e})")

def apply_refactor_plan():
    print("🔄 リファクタ計画を適用中...")

    if not os.path.exists(PLAN_PATH):
        print(f"❌ リファクタ計画ファイルが見つかりません: {PLAN_PATH}")
        return

    with open(PLAN_PATH, "r") as f:
        plan = json.load(f)

    delete_list = plan.get("delete", []) + plan.get("duplicate", []) + plan.get("other", [])

    for path in delete_list:
        delete_path(path)

    print(f"✅ リファクタ完了: {len(delete_list)} 件削除済み")

if __name__ == "__main__":
    apply_refactor_plan()
