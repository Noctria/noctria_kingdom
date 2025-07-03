import os
import sys
import json
from pathlib import Path

# 🔧 モジュールパスを追加（Noctria Kingdom のルートディレクトリを sys.path に含める）
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

# ✅ 必要な関数をimport（tools以下を読み込めるようになる）
from tools.hardcoded_path_replacer import replace_paths

# ログと監査設定
LOGS_DIR = ROOT_DIR / "logs"
AUDIT_LOG = LOGS_DIR / "structure_audit.json"

def remove_path(target: Path):
    if target.is_file():
        print(f"🗑️ Removing file: {target}")
        target.unlink()
    elif target.is_dir():
        print(f"🧹 Removing directory: {target}")
        for sub in target.glob("*"):
            remove_path(sub)
        target.rmdir()

def process_audit_log():
    if not AUDIT_LOG.exists():
        print("❌ structure_audit.json が見つかりません")
        return

    with open(AUDIT_LOG, "r", encoding="utf-8") as f:
        issues = json.load(f)

    for issue in issues:
        path = ROOT_DIR / issue["path"]
        if issue["type"] in {"unnecessary_file", "unnecessary_directory"}:
            remove_path(path)
        elif issue["type"] in {"too_many_files", "too_many_directories"}:
            print(f"⚠️ [構造警告] {issue['type']} @ {issue['path']} → count={issue['count']}")

def apply_path_replacements():
    print("🔄 Import/パス自動変換を適用中...")
    for py_file in ROOT_DIR.rglob("*.py"):
        if "venv" in py_file.parts or ".venv" in py_file.parts:
            continue
        replace_paths(py_file)

def main():
    print("🚀 Noctria Kingdom v2.0構成への再編を開始します")
    process_audit_log()
    apply_path_replacements()
    print("✅ 完了しました。構成はv2.0準拠になりました")

if __name__ == "__main__":
    main()
