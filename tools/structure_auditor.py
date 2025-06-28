# structure_auditor.py

import os
import ast
import json
from pathlib import Path

# === 監査ルール設定 ===
CORE_RULES = ["logger", "utils", "NoctriaEnv", "meta_ai_env", "veritas_model"]
STRATEGY_RULES = ["aurus", "levia", "noctus", "prometheus"]

# 除外ディレクトリ
EXCLUDE_DIRS = {".git", "__pycache__", "venv", "logs", "models", "tmp"}

# 対象ルートパス
ROOT_DIR = Path(__file__).resolve().parent.parent / "noctria-kingdom-main"

# ログ出力ファイル
LOG_FILE = ROOT_DIR / "audit_log.json"

def should_exclude(path: Path) -> bool:
    return any(part in EXCLUDE_DIRS for part in path.parts)

def classify_file(path: Path, content: str):
    """中身をもとに分類ルール適用"""
    lowered = path.name.lower()
    for core in CORE_RULES:
        if core in lowered:
            return "core", f"core/{path.name}"
    for strat in STRATEGY_RULES:
        if strat in lowered:
            return "strategy", f"strategies/official/{path.name}"
    if "llm_server" in content or "FastAPI" in content:
        return "llm_server", f"llm_server/{path.name}"
    return "unclassified", None

def scan_files():
    issues = []
    for root, _, files in os.walk(ROOT_DIR):
        for file in files:
            path = Path(root) / file
            if path.suffix != ".py" or should_exclude(path):
                continue
            try:
                content = path.read_text(encoding="utf-8")
                classification, suggested = classify_file(path, content)
                
                # 現在の場所によるチェック
                if classification == "core" and "airflow_docker/core" not in str(path):
                    issues.append({
                        "file": str(path.relative_to(ROOT_DIR)),
                        "issue": "Coreモジュールは airflow_docker/core に集約すべき",
                        "suggested_move": f"airflow_docker/core/{path.name}"
                    })
                elif classification == "strategy" and "strategies/official" not in str(path):
                    issues.append({
                        "file": str(path.relative_to(ROOT_DIR)),
                        "issue": "戦略は strategies/official に配置すべき",
                        "suggested_move": suggested
                    })
                elif classification == "llm_server" and "llm_server" not in str(path):
                    issues.append({
                        "file": str(path.relative_to(ROOT_DIR)),
                        "issue": "LLM系スクリプトは llm_server/ に集約すべき",
                        "suggested_move": suggested
                    })
            except Exception as e:
                issues.append({
                    "file": str(path.relative_to(ROOT_DIR)),
                    "issue": f"解析エラー: {str(e)}",
                    "suggested_move": None
                })
    return issues

def main():
    issues = scan_files()
    with LOG_FILE.open("w", encoding="utf-8") as f:
        json.dump(issues, f, indent=2, ensure_ascii=False)
    print(f"✅ 構成監査ログを出力しました: {LOG_FILE}")

if __name__ == "__main__":
    main()
