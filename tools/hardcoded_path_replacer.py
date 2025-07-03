import os
import re
import difflib
import argparse
from pathlib import Path

# 🔁 ハードコードされたパスを path_config 定数へ置換するルール
REPLACEMENT_RULES = {
    r'["\']?/noctria_kingdom/airflow_docker/dags["\']?': "DAGS_DIR",
    r'["\']?/noctria_kingdom/airflow_docker/logs["\']?': "LOGS_DIR",
    r'["\']?/noctria_kingdom/airflow_docker/plugins["\']?': "PLUGINS_DIR",
    r'["\']?/noctria_kingdom/scripts["\']?': "SCRIPTS_DIR",
    r'["\']?/noctria_kingdom/core["\']?': "CORE_DIR",
    r'["\']?/noctria_kingdom/strategies["\']?': "STRATEGIES_DIR",
    r'["\']?/noctria_kingdom/data["\']?': "DATA_DIR",
    r'["\']?/noctria_kingdom/models["\']?': "MODELS_DIR",
    r'["\']?/noctria_kingdom/institutions["\']?': "INSTITUTIONS_DIR",
    r'["\']?/noctria_kingdom/veritas["\']?': "VERITAS_DIR",
    r'["\']?/noctria_kingdom/tools["\']?': "TOOLS_DIR",
    r'["\']?/noctria_kingdom/tests["\']?': "TESTS_DIR",
}

# 🔍 すべての定数を収集（import挿入用）
ALL_CONSTANTS = sorted(list(REPLACEMENT_RULES.values()))

def show_diff(original: str, modified: str, file_path: Path):
    """差分表示"""
    diff = difflib.unified_diff(
        original.splitlines(), modified.splitlines(),
        fromfile=str(file_path),
        tofile=f"{file_path} (modified)",
        lineterm=""
    )
    print("\n".join(diff))


def insert_import(content: str) -> str:
    """path_config からの import を先頭に追加（重複防止）"""
    import_line = f"from core.path_config import {', '.join(ALL_CONSTANTS)}"

    if import_line in content:
        return content

    lines = content.splitlines()
    insert_at = 0
    for i, line in enumerate(lines):
        if line.startswith("#!") or line.startswith("# -*-"):
            insert_at = i + 1
        elif line.strip() == "":
            continue
        else:
            break

    lines.insert(insert_at, import_line)
    return "\n".join(lines)


def replace_paths(file_path: Path, dry_run: bool = False, show_diff_flag: bool = False):
    """パス置換処理の実行"""
    with open(file_path, "r", encoding="utf-8") as f:
        original_content = f.read()

    modified_content = original_content
    replaced = False

    for pattern, const in REPLACEMENT_RULES.items():
        if re.search(pattern, modified_content):
            modified_content = re.sub(pattern, const, modified_content)
            replaced = True

    if replaced:
        modified_content = insert_import(modified_content)

        if dry_run:
            print(f"🟡 [DRY-RUN] {file_path}")
            if show_diff_flag:
                show_diff(original_content, modified_content, file_path)
        else:
            print(f"✅ [UPDATED] {file_path}")
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(modified_content)


def scan_target(path: Path):
    """指定パス以下を再帰探索（.pyのみ）"""
    if path.is_file():
        yield path
    elif path.is_dir():
        for py_file in path.rglob("*.py"):
            yield py_file


def main():
    parser = argparse.ArgumentParser(description="🛠 ハードコードされたパスを path_config 定数に置換")
    parser.add_argument("--path", type=str, required=True, help="対象ファイルまたはディレクトリ")
    parser.add_argument("--dry-run", action="store_true", help="実際には書き換えずに変更内容を表示")
    parser.add_argument("--show-diff", action="store_true", help="差分を表示（dry-run時のみ）")
    parser.add_argument("--apply", action="store_true", help="変更を適用")
    args = parser.parse_args()

    target_path = Path(args.path).resolve()

    for file_path in scan_target(target_path):
        replace_paths(file_path, dry_run=not args.apply, show_diff_flag=args.show_diff)


if __name__ == "__main__":
    main()
