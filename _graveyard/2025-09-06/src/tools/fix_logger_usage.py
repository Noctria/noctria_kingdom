import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_EXTS = [".py"]
TARGET_DIRS = [
    PROJECT_ROOT / "airflow_docker",
    PROJECT_ROOT / "core",
    PROJECT_ROOT / "strategies",
    PROJECT_ROOT / "scripts",
    PROJECT_ROOT / "veritas",
    PROJECT_ROOT / "execution",
    PROJECT_ROOT / "experts",
]

# 旧形式: setup_logger("Name", "/path/to/logfile") を削除
OLD_SETUP_LOGGER_REGEX = re.compile(
    r'setup_logger\(\s*["\']([\w\-]+)["\']\s*,\s*["\'].*?\.log["\']\s*\)'
)

# 新形式: setup_logger("Name") に統一
def fix_setup_logger_usage(code: str) -> str:
    return OLD_SETUP_LOGGER_REGEX.sub(r'setup_logger("\1")', code)

# 検索と修正処理
def fix_all_files():
    for target_dir in TARGET_DIRS:
        for path in target_dir.rglob("*"):
            if path.suffix in TARGET_EXTS and path.is_file():
                original = path.read_text(encoding="utf-8")
                updated = fix_setup_logger_usage(original)
                if original != updated:
                    print(f"🛠 修正中: {path.relative_to(PROJECT_ROOT)}")
                    path.write_text(updated, encoding="utf-8")

if __name__ == "__main__":
    print("🔍 setup_logger の形式統一を開始します...")
    fix_all_files()
    print("✅ 完了しました。すべての setup_logger 呼び出しが統一されました。")
