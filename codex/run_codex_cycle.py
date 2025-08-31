# codex/run_codex_cycle.py
from __future__ import annotations

import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple
import importlib.util
import datetime as dt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "codex_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
JSON_PATH = REPORTS_DIR / "tmp.json"
JUNIT_PATH = REPORTS_DIR / "tmp.junit.xml"
LATEST_MD = REPORTS_DIR / "latest_codex_cycle.md"

# ===== 既存の型/データモデルがあるならそのまま使ってOK。無ければ最低限のdictで返す =====

def _has_pytest_json_report() -> bool:
    return importlib.util.find_spec("pytest_jsonreport") is not None

def _run_pytest(pytest_args: list[str]) -> Tuple[int, str, str, bool]:
    """
    return: (rc, stdout, stderr, used_json_plugin)
    """
    used_json = _has_pytest_json_report()
    cmd = [sys.executable, "-m", "pytest", "-q", *pytest_args]
    if used_json:
        cmd += ["--json-report", f"--json-report-file={JSON_PATH}"]
    else:
        cmd += [f"--junitxml={JUNIT_PATH}"]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr, used_json

def _load_result(used_json: bool) -> dict[str, Any]:
    if used_json and JSON_PATH.exists():
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))

    # フォールバック: JUnit から最小限のJSONを合成
    if not JUNIT_PATH.exists():
        return {}
    root = ET.parse(JUNIT_PATH).getroot()
    # testsuite が直下かもしれないので両対応
    suite = root.find("testsuite") or root
    total = int(suite.attrib.get("tests", 0))
    failures = int(suite.attrib.get("failures", 0))
    errors = int(suite.attrib.get("errors", 0))
    skipped = int(suite.attrib.get("skipped", 0))
    duration_sec = float(suite.attrib.get("time", 0.0))
    cases = []
    for tc in suite.iterfind("testcase"):
        nodeid = f"{tc.attrib.get('classname','')}::{tc.attrib.get('name','')}".strip(":")
        outcome = "passed"
        tb = ""
        f_elt = tc.find("failure")
        e_elt = tc.find("error")
        if f_elt is not None:
            outcome = "failed"
            tb = (f_elt.text or "").strip()
        elif e_elt is not None:
            outcome = "error"
            tb = (e_elt.text or "").strip()
        cases.append({"nodeid": nodeid, "outcome": outcome, "duration": None, "longrepr": tb, "traceback": tb})
    return {
        "pytest": {
            "total": total,
            "failed": failures,
            "errors": errors,
            "skipped": skipped,
            "duration_sec": duration_sec,
            "cases": cases,
        }
    }

def _write_latest_md(rc: int, stdout: str, stderr: str, used_json: bool) -> None:
    ts = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    LATEST_MD.write_text(
        "\n".join([
            "## Codex Cycle Report",
            f"- returncode: {rc}",
            "",
            "(JSON plugin used)" if used_json else "(JUnit fallback used)",
            "",
            "### Pytest stdout (tail)",
            "```",
            "\n".join(stdout.splitlines()[-80:]),
            "```",
            "",
            "### Pytest stderr (tail)",
            "```",
            "\n".join(stderr.splitlines()[-80:]),
            "```",
            ""
        ]),
        encoding="utf-8"
    )

# === 外部から呼ばれるエントリ (mini_loop から利用) ===
@dataclass
class CycleResult:
    pytest: dict
    git: dict  # 既存実装があれば差し替え。最低限空dictでOK。

def run_cycle(pytest_args: str | None, base_ref: str, head_ref: str,
              title: str, enable_patch_notes: bool) -> tuple[CycleResult, str]:
    args = []
    if pytest_args:
        # スペース区切りを素直にsplit（高度なパースが必要ならshlex.splitへ）
        args = pytest_args.split()

    rc, out, err, used_json = _run_pytest(args)
    result_dict = _load_result(used_json)
    # JSON が無くても空で返す（mini_loop 側で失敗抽出ゼロになるだけ）
    if result_dict:
        JSON_PATH.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    _write_latest_md(rc, out or "", err or "", used_json)

    # 既存と互換の返し方に寄せる
    result = CycleResult(pytest=result_dict.get("pytest", {}), git={"branch": "", "commit": "", "is_dirty": False})
    return result, str(LATEST_MD)

if __name__ == "__main__":
    # 手動実行用
    rc, out, err, used_json = _run_pytest([])
    _write_latest_md(rc, out, err, used_json)
    sys.exit(rc)
