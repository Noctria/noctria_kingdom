# tools/structure_refactor.py

import sys
import os
from pathlib import Path

# === パス設定 ===
CURRENT_FILE = Path(__file__).resolve()
ROOT_DIR = CURRENT_FILE.parent.parent
sys.path.append(str(ROOT_DIR))  # v3.0: パスの動的追加（絶対パス対応）

from tools.hardcoded_path_replacer import replace_paths
from tools.structure_auditor import main as audit_main

# === 対象ディレクトリ一覧（v3.0準拠）
TARGETS = [
    ROOT_DIR / "airflow_docker" / "dags",
    ROOT_DIR / "airflow_docker" / "plugins",
    ROOT_DIR / "airflow_docker" / "scripts",
    ROOT_DIR / "core",
    ROOT_DIR / "strategies",
    ROOT_DIR / "veritas",
    ROOT_DIR / "tools",
    ROOT_DIR / "tests",
    ROOT_DIR / "llm_server",
    ROOT_DIR / "execution",
    ROOT_DIR / "experts",
]

def refactor_all():
    print("🚀 Noctria Kingdom v3.0構成への再編を開始します")
    print(f"📁 ルート: {ROOT_DIR}")

    for target in TARGETS:
        if target.exists():
            print(f"🔧 Replacing paths in: {target}")
            for root, _, files in os.walk(target):
                for file in files:
                    if file.endswith(".py"):
                        path = Path(root) / file
                        try:
                            replace_paths(path)
                        except Exception as e:
                            print(f"❌ Error processing {path}: {e}")
        else:
            print(f"⚠️ Not found: {target}")

    print("✅ 全ファイルのパス変換が完了しました。構成監査を実行します...")
    audit_main()

if __name__ == "__main__":
    refactor_all()
