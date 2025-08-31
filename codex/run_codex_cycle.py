# codex/run_codex_cycle.py
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# --- ルート/出力ディレクトリの解決 ---
THIS_DIR = Path(__file__).resolve().parent
REPO_ROOT = THIS_DIR.parent
SRC_DIR = REPO_ROOT / "src"
TESTS_DIR = REPO_ROOT / "tests"
REPORT_DIR = REPO_ROOT / "codex_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)
JSON_REPORT_PATH = REPORT_DIR / "tmp.json"
LATEST_MD_PATH = REPORT_DIR / "latest_codex_cycle.md"
PATCH_NOTES_PATH = REPORT_DIR / "patch_notes.md"

# --- patch_notes を安全に import ---
try:
    from codex.tools.patch_notes import make_patch_notes  # type: ignore
except Exception:
    # 実行方法の違いに備えてパスを調整
    if str(REPO_ROOT) not in sys.path:
        sys.path.append(str(REPO_ROOT))
    from codex.tools.patch_notes import make_patch_notes  # type: ignore


def _select_tests() -> List[str]:
    """
    CODEX_FULL=1 のときは全テスト、そうでなければ軽量サブセット。
    """
    if os.environ.get("CODEX_FULL") == "1":
        print("📦 Running FULL test suite (CODEX_FULL=1)")
        return [str(TESTS_DIR)]

    # 軽量サブセット（品質ゲート＋ノクタスゲート）
    print("🧪 Running LIGHT test subset for Codex:")
    subset = [
        TESTS_DIR / "test_quality_gate_alerts.py",
        TESTS_DIR / "test_noctus_gate_block.py",
    ]
    for p in subset:
        print(f"  - {p.relative_to(REPO_ROOT)}")
    return [str(p) for p in subset]


def _run_pytest_and_json_report(test_paths: List[str]) -> subprocess.CompletedProcess:
    """
    pytest を JSON レポート付きで実行。プロセスは常に完了させる（失敗してもレポート生成を試みる）。
    """
    # 環境変数：プラグイン自動ロード抑制＆PYTHONPATH設定（src を優先）
    env = os.environ.copy()
    env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
    # 既存 PYTHONPATH を活かしつつ src を先頭に追加
    py_path = str(SRC_DIR)
    if env.get("PYTHONPATH"):
        env["PYTHONPATH"] = f"{py_path}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = py_path

    # 既存の JSON を一旦消す（前回の残骸防止）
    if JSON_REPORT_PATH.exists():
        JSON_REPORT_PATH.unlink()

    cmd = [
        "pytest",
        "-q",
        *test_paths,
        "--json-report",
        f"--json-report-file={JSON_REPORT_PATH}",
    ]
    print("== Running pytest ==")
    proc = subprocess.run(cmd, cwd=str(REPO_ROOT), env=env, text=True, capture_output=True)
    return proc


def _load_json_report(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write_latest_markdown(proc: subprocess.CompletedProcess, report_json: Optional[Dict[str, Any]]) -> None:
    """
    Markdown レポート（latest_codex_cycle.md）を生成。
    """
    lines: List[str] = []
    lines.append("## Codex Cycle Report")

    # return code
    lines.append(f"- returncode: {proc.returncode}")

    if report_json:
        summary = report_json.get("summary", {}) or {}
        total = summary.get("total", "N/A")
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        errors = summary.get("errors", 0)
        skipped = summary.get("skipped", 0)
        xfailed = summary.get("xfailed", 0)
        xpassed = summary.get("xpassed", 0)

        lines.append("")
        lines.append("### Summary")
        lines.append(f"- total: {total}")
        lines.append(f"- passed: {passed}")
        lines.append(f"- failed: {failed}")
        lines.append(f"- errors: {errors}")
        lines.append(f"- skipped: {skipped}")
        lines.append(f"- xfailed: {xfailed}")
        lines.append(f"- xpassed: {xpassed}")

        # 失敗があれば、失敗テストを列挙（短く）
        if failed or errors:
            lines.append("")
            lines.append("### Failed/Errored tests (short)")
            tests = report_json.get("tests", []) or []
            count = 0
            for t in tests:
                outc = (t.get("outcome") or "").lower()
                if outc in ("failed", "error"):
                    nodeid = t.get("nodeid", "<?>")
                    lines.append(f"- {outc.upper()}: {nodeid}")
                    count += 1
                    if count >= 20:
                        lines.append("- ... (truncated)")
                        break
    else:
        lines.append("")
        lines.append("(no JSON report generated)")

    # 末尾に stdout/stderr の要約（長すぎるときは末尾だけ）
    def _tail(text: str, limit: int = 1200) -> str:
        if len(text) <= limit:
            return text
        return text[-limit:]

    lines.append("")
    lines.append("### Pytest stdout (tail)")
    lines.append("```")
    lines.append(_tail(proc.stdout or "", 2000))
    lines.append("```")

    if proc.returncode != 0:
        lines.append("")
        lines.append("### Pytest stderr (tail)")
        lines.append("```")
        lines.append(_tail(proc.stderr or "", 2000))
        lines.append("```")

    LATEST_MD_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    test_paths = _select_tests()
    proc = _run_pytest_and_json_report(test_paths)
    report_json = _load_json_report(JSON_REPORT_PATH)

    # patch_notes.md を生成（JSON が無い/壊れている場合は空で）
    try:
        patch_md = make_patch_notes(report_json or {})
        PATCH_NOTES_PATH.write_text(patch_md, encoding="utf-8")
    except Exception as e:
        # 生成失敗時は空のプレースホルダを置く
        PATCH_NOTES_PATH.write_text(f"# Patch Notes\n\n(Generation error: {e})\n", encoding="utf-8")

    # latest_codex_cycle.md を更新
    _write_latest_markdown(proc, report_json)

    print("== Codex cycle complete ==")
    print(f"Report: {LATEST_MD_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
