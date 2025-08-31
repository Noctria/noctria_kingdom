# codex/run_codex_cycle.py
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List

# 自動生成するレポートのパス
JSON_REPORT = Path("codex_reports/tmp.json")
LATEST_MD = Path("codex_reports/latest_codex_cycle.md")
PATCH_NOTES_MD = Path("codex_reports/patch_notes.md")

# 必要: tools/patch_notes.py（既に追加済みの想定）
try:
    from tools.patch_notes import make_patch_notes  # type: ignore
except Exception:
    # 相対経路でも試す
    sys.path.append(str(Path(__file__).resolve().parent))
    from tools.patch_notes import make_patch_notes  # type: ignore


def _ensure_dirs() -> None:
    JSON_REPORT.parent.mkdir(parents=True, exist_ok=True)
    LATEST_MD.parent.mkdir(parents=True, exist_ok=True)


def _selected_tests() -> List[str]:
    """環境変数 CODEX_FULL=1 でフル、それ以外はライトサブセット"""
    if os.environ.get("CODEX_FULL", "0") == "1":
        # フル: tests ディレクトリ全体
        return ["tests"]
    # ライト: 速い安全な2本
    return ["tests/test_quality_gate_alerts.py", "tests/test_noctus_gate_block.py"]


def _run_pytest_and_json(tests: List[str]) -> int:
    """pytest を JSON レポート付きで実行し、returncode を返す"""
    # pytest の自動プラグイン抑制 + src を PYTHONPATH に追加
    env = os.environ.copy()
    env.setdefault("PYTEST_DISABLE_PLUGIN_AUTOLOAD", "1")
    env.setdefault("PYTHONPATH", str(Path("src").resolve()))

    # 既存 JSON を消す（前回の残骸防止）
    if JSON_REPORT.exists():
        JSON_REPORT.unlink()

    cmd = [
        sys.executable, "-m", "pytest",
        "-q", *tests,
        "--json-report",
        f"--json-report-file={JSON_REPORT.as_posix()}",
    ]
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, env=env)
    return proc.returncode


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _summarize(json_obj: Dict[str, Any]) -> str:
    if not json_obj:
        return "## Codex Cycle Report\n(no JSON report generated)"
    s = json_obj.get("summary", {}) or {}
    total = s.get("total") or len(json_obj.get("tests", []))
    parts = {
        "passed": s.get("passed", 0),
        "failed": s.get("failed", 0),
        "error": s.get("errors", 0) or s.get("error", 0),
        "skipped": s.get("skipped", 0),
        "xfailed": s.get("xfailed", 0),
        "xpassed": s.get("xpassed", 0),
        "duration": s.get("duration", "N/A"),
    }
    lines = [
        "## Codex Cycle Report",
        f"- scope: `{os.environ.get('CODEX_FULL', '0') and 'full' or 'light'}`",
        "",
        "| total | passed | failed | error | skipped | xfailed | xpassed | duration |",
        "|------:|------:|------:|-----:|-------:|-------:|--------:|---------:|",
        f"| {total} | {parts['passed']} | {parts['failed']} | {parts['error']} | "
        f"{parts['skipped']} | {parts['xfailed']} | {parts['xpassed']} | {parts['duration']} |",
        "",
    ]
    # 失敗/エラーの一覧（nodeidのみ簡易）
    tests = json_obj.get("tests", [])
    bad = [t for t in tests if t.get("outcome") in ("failed", "error")]
    if bad:
        lines.append("### Failed/Error tests")
        for t in bad:
            lines.append(f"- {t.get('nodeid', '<unknown>')}")
        lines.append("")
    else:
        lines.append("✅ All selected tests passed.")
    return "\n".join(lines)


def main() -> None:
    _ensure_dirs()
    tests = _selected_tests()
    rc = _run_pytest_and_json(tests)

    # patch_notes 生成（JSON が無くても placeholder を出す）
    make_patch_notes(JSON_REPORT.as_posix(), PATCH_NOTES_MD.as_posix())

    # latest_md 出力
    report_json = _load_json(JSON_REPORT)
    LATEST_MD.write_text(_summarize(report_json), encoding="utf-8")

    # 終了コードはテストの returncode に合わせる（CI 的に便利）
    sys.exit(rc)


if __name__ == "__main__":
    main()
