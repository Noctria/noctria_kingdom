# codex/run_codex_cycle.py
from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import List

# --- robust imports: package -> relative -> bare ---
try:
    # preferred when running as a package: python -m codex.run_codex_cycle
    from codex.tools.pytest_runner import run_pytest  # type: ignore
    from codex.tools.patch_notes import make_patch_notes  # type: ignore
except Exception:
    try:
        # relative import fallback (if codex is a package)
        from .tools.pytest_runner import run_pytest  # type: ignore
        from .tools.patch_notes import make_patch_notes  # type: ignore
    except Exception:
        # bare fallback for direct script execution
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
    """環境変数 CODEX_FULL が truthy なら全体、なければ軽量サブセット。"""
    flag = os.environ.get("CODEX_FULL", "").strip().lower()
    if flag in ("1", "true", "yes", "on"):
        return ["tests"]
    return LIGHT_TESTS

def _tail(text: str, n: int = 60) -> str:
    lines = text.strip().splitlines()
    if len(lines) <= n:
        return text.strip()
    return "\n".join(lines[-n:])

def main() -> None:
    # ルートを PYTHONPATH に通しておく（tools などの解決を安定化）
    sys.path.insert(0, str(ROOT))

    targets = _select_targets()

    # pytest 実行（JSON レポートを強制、失敗しても後段で graceful degrade）
    rc, out, err = run_pytest(
        targets,
        json_report=True,
        json_path=JSON_PATH,
    )

    # レポート生成（JSON があれば差分ノート、なければメッセージ）
    if JSON_PATH.exists():
        patch_md = make_patch_notes(JSON_PATH)
    else:
        patch_md = "(no JSON report generated)"

    # latest レポートを上書き
    with open(LATEST, "w", encoding="utf-8") as f:
        f.write("## Codex Cycle Report\n")
        f.write(f"- returncode: {rc}\n\n")
        if rc == 0 and JSON_PATH.exists():
            f.write("✅ All selected tests passed.\n\n")
        elif rc == 0:
            f.write("✅ All selected tests passed (no JSON report).\n\n")
        else:
            f.write(f"{patch_md}\n\n")
            f.write("### Pytest stdout (tail)\n```\n")
            f.write((_tail(out) or "").rstrip() + "\n")
            f.write("```\n\n### Pytest stderr (tail)\n```\n")
            f.write((_tail(err) or "").rstrip() + "\n")
            f.write("```\n")

    print("== Codex cycle complete ==")
    print(f"Report: {LATEST}")

if __name__ == "__main__":
    main()
