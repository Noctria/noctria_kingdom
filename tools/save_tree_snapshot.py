# tools/save_tree_snapshot.py

import os
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_FILE = BASE_DIR / "docs" / "diagnostics" / "tree_snapshot.txt"

def save_tree_snapshot():
    print("🌲 tree -L 3 を取得中...")

    try:
        OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            ["tree", "-L", "3"],
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(result.stdout)

        print(f"✅ 保存完了: {OUTPUT_FILE}")

    except FileNotFoundError:
        print("❌ 'tree' コマンドが見つかりません。以下でインストールできます:")
        print("   sudo apt install tree")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ エラー発生:\n{e.stderr}")

if __name__ == "__main__":
    save_tree_snapshot()
