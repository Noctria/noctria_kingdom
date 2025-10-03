#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Codex Agent Progress Diagnostic Script
======================================

Codex Noctria のエージェント開発進捗を診断するスクリプト。
Lv1〜Lv3 までの進捗を、リポジトリ内のファイルやディレクトリの有無から判定する。

Usage:
    python scripts/codex_progress_check.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check_file(path: Path) -> bool:
    return path.exists() and path.is_file()


def check_dir(path: Path) -> bool:
    return path.exists() and path.is_dir()


def main() -> None:
    report = {
        "Lv1": {
            "pytest_runner": check_file(ROOT / "src/codex/tools/pytest_runner.py"),
            "inventor_suggestions": check_file(ROOT / "src/codex_reports/inventor_suggestions.md"),
            "pytest_log": check_file(ROOT / "src/codex_reports/proxy_pytest_last.log"),
        },
        "Lv2": {
            "patch_notes": check_file(ROOT / "src/codex/tools/patch_notes.py"),
            "review_pipeline": check_file(ROOT / "src/codex/tools/review_pipeline.py"),
            "patches_dir": check_dir(ROOT / "src/codex_reports/patches"),
            "patch_file_sample": any(
                p.suffix == ".patch" for p in (ROOT / "src/codex_reports/patches").glob("*.patch")
            )
            if check_dir(ROOT / "src/codex_reports/patches")
            else False,
            "apply_patch_script": check_file(ROOT / "scripts/apply_codex_patch.sh"),
        },
        "Lv3": {
            "pdca_agent": check_file(ROOT / "scripts/pdca_agent.py"),
            "inventor_pipeline_dag": check_file(
                ROOT / "airflow_docker/dags/inventor_pipeline_dag.py"
            ),
            "decision_registry": check_file(ROOT / "codex_reports/decision_registry.jsonl"),
        },
        "GUI": {
            "codex_html": check_file(ROOT / "noctria_gui/templates/codex.html"),
            "codex_route": check_file(ROOT / "noctria_gui/routes/codex.py"),
        },
    }

    # 判定ロジック
    level = "Lv0 (未着手)"
    if report["Lv1"]["pytest_runner"] and report["Lv1"]["inventor_suggestions"]:
        level = "Lv1"
    if report["Lv2"]["patch_notes"] and report["Lv2"]["patch_file_sample"]:
        level = "Lv2"
    if report["Lv3"]["pdca_agent"] and report["Lv3"]["inventor_pipeline_dag"]:
        level = "Lv3"

    result = {"detected_level": level, "details": report}

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2, ensure_ascii=False))
        sys.exit(1)
