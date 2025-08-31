# codex/run_codex_cycle.py
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Any

# 相対/絶対どちらでも import できるように
try:
    from tools.pytest_runner import run_pytest  # type: ignore
    from tools.patch_notes import make_patch_notes  # type: ignore
except Exception:
    sys.path.append(str(Path(__file__).resolve().parent))
    from tools.pytest_runner import run_pytest  # type: ignore
    from tools.patch_notes import make_patch_notes  # type: ignore


ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "codex_reports"
REPORTS_DIR.mkdir(exist_ok=True, parents=True)
LATEST = REPORTS_DIR / "latest_codex_cycle.md"
JSON_PATH = REPORTS_DIR / "tmp.json"

# 軽量サブセット（Codex ローカル検証用）
LIGHT_TESTS = [
    "tests/test_quality_gate_alerts.py",
    "tests/test_noctus_gate_block.py",
]


def _select_targets() -> List[str]:
    """環境変数でフル/軽量を切り替え。"""
    if os.environ.get("CODEX_FULL") == "1":
        return ["tests"]
    return LIGHT_TESTS


def _tail(text: str, n: int = 60) -> str:
    lines = text.strip().splitlines()
    if len(lines) <= n:
        return text.strip()
    return "\n".join(lines[-n:])


def main() -> None:
    targets = _select_targets()

    # pytest 実行（JSON レポートを強制有効にしてプロット）
    rc, out, err = run_pytest(
        targets,
        json_report=True,
        json_path=JSON_PATH,
    )

    # レポート生成
    if JSON_PATH.exists():
        patch_md = make_patch_notes(JSON_PATH)
    else:
        patch_md = "(no JSON report generated)"

    # latest レポートを上書き
    with open(LATEST, "w", encoding="utf-8") as f:
        f.write("## Codex Cycle Report\n")
        f.write(f"- returncode: {rc}\n\n")
        if rc == 0:
            f.write("✅ All selected tests passed.\n\n")
        else:
            f.write(f"{patch_md}\n\n")
            f.write("### Pytest stdout (tail)\n```\n")
            f.write(_tail(out) + "\n")
            f.write("```\n\n### Pytest stderr (tail)\n```\n")
            f.write(_tail(err) + "\n")
            f.write("```\n")

    print("== Codex cycle complete ==")
    print(f"Report: {LATEST}")


if __name__ == "__main__":
    main()
