# tools/structure_auditor.py

from pathlib import Path
import os
import json
from collections import defaultdict
from core.path_config import BASE_DIR

def audit_structure():
    issues = []

    # === ① トップレベルディレクトリ数チェック ===
    top_level = list(BASE_DIR.glob("*"))
    if len(top_level) > 25:
        issues.append({
            "type": "too_many_directories",
            "path": ".",
            "count": len(top_level)
        })

    # === ② 不要ファイル名チェック ===
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            file_lower = file.lower()
            if file_lower in {"dammy", "dummy", "temp"}:
                issues.append({
                    "type": "unnecessary_file",
                    "path": str(Path(root) / file)
                })

    # === ③ .pyc や __pycache__ チェック ===
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".pyc") or "__pycache__" in Path(root).parts:
                issues.append({
                    "type": "python_cache_file",
                    "path": str(Path(root) / file)
                })

    # === ④ .bak バックアップファイル検出 ===
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            if file.endswith(".bak"):
                issues.append({
                    "type": "backup_file",
                    "path": str(Path(root) / file)
                })

    # === ⑤ 同名ファイル（別パス）の重複検出 ===
    name_to_paths = defaultdict(list)
    for root, _, files in os.walk(BASE_DIR):
        for file in files:
            name_to_paths[file].append(str(Path(root) / file))

    for name, paths in name_to_paths.items():
        if len(paths) > 1:
            issues.append({
                "type": "duplicate_filename",
                "name": name,
                "paths": paths
            })

    # === ⑥ 大文字小文字だけ異なるディレクトリ名（OS差異で混乱） ===
    dir_names = defaultdict(list)
    for path in BASE_DIR.glob("**/"):
        dir_names[path.name.lower()].append(str(path))

    for name, paths in dir_names.items():
        if len(paths) > 1:
            issues.append({
                "type": "duplicate_directory_case",
                "name": name,
                "paths": paths
            })

    # === ⑦ Airflow内の二重ネスト構造検出 ===
    double_nested = BASE_DIR / "airflow_docker" / "airflow_docker"
    if double_nested.exists():
        issues.append({
            "type": "double_nested_airflow",
            "path": str(double_nested)
        })

    # === 結果をJSONに保存 ===
    log_path = BASE_DIR / "logs" / "structure_audit.json"
    os.makedirs(log_path.parent, exist_ok=True)
    with open(log_path, "w") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)

    print(f"✅ 構造監査完了: {log_path} に {len(issues)} 件記録")

if __name__ == "__main__":
    audit_structure()
