# codex/run_codex_cycle.py
from __future__ import annotations
import json, subprocess, sys, xml.etree.ElementTree as ET, importlib.util, os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Tuple, List

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "codex_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
JSON_PATH = REPORTS_DIR / "tmp.json"
JUNIT_PATH = REPORTS_DIR / "tmp.junit.xml"
LATEST_MD = REPORTS_DIR / "latest_codex_cycle.md"

# 🎯 小ループで回す対象（pytest.ini は変更しない）
DEFAULT_MINILOOP_TARGETS = [
    "tests/test_quality_gate_alerts.py",
    "tests/test_noctus_gate_block.py",
]

def _has_pytest_json_report() -> bool:
    return importlib.util.find_spec("pytest_jsonreport") is not None

def _pytest_env() -> dict:
    """src レイアウトを解決。全体テスト用 pytest.ini は触らず両立。"""
    env = os.environ.copy()
    add = f"{PROJECT_ROOT/'src'}:{PROJECT_ROOT}"
    env["PYTHONPATH"] = f"{add}:{env.get('PYTHONPATH','')}".strip(":")
    return env

def _run_pytest(pytest_args: List[str]) -> Tuple[int, str, str, bool]:
    """pytest を実行して (rc, stdout, stderr, used_json_plugin) を返す"""
    used_json = _has_pytest_json_report()
    cmd = [sys.executable, "-m", "pytest", "-q", *pytest_args]
    if used_json:
        cmd += ["--json-report", f"--json-report-file={JSON_PATH}"]
    else:
        cmd += [f"--junitxml={JUNIT_PATH}"]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=_pytest_env())
    return proc.returncode, proc.stdout, proc.stderr, used_json

def _load_result(used_json: bool) -> dict[str, Any]:
    """pytest-json-report か JUnit を統一フォーマットへ"""
    if used_json and JSON_PATH.exists():
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))

    # フォールバック: JUnit → ざっくりJSON化
    if not JUNIT_PATH.exists():
        return {"pytest": {"total": 0, "failed": 0, "errors": 0, "skipped": 0, "duration_sec": 0.0, "cases": []}}

    root = ET.parse(JUNIT_PATH).getroot()
    suite = root.find("testsuite") or root
    total = int(suite.attrib.get("tests", 0))
    failures = int(suite.attrib.get("failures", 0))
    errors = int(suite.attrib.get("errors", 0))
    skipped = int(suite.attrib.get("skipped", 0))
    duration_sec = float(suite.attrib.get("time", 0.0))
    cases = []
    for tc in suite.iterfind("testcase"):
        nodeid = f"{tc.attrib.get('classname','')}::{tc.attrib.get('name','')}".strip(":")
        outcome, tb = "passed", ""
        f_elt, e_elt = tc.find("failure"), tc.find("error")
        if f_elt is not None:
            outcome, tb = "failed", (f_elt.text or "").strip()
        elif e_elt is not None:
            outcome, tb = "error", (e_elt.text or "").strip()
        cases.append({"nodeid": nodeid, "outcome": outcome, "duration": None, "longrepr": tb, "traceback": tb})
    return {"pytest": {"total": total, "failed": failures, "errors": errors, "skipped": skipped,
                       "duration_sec": duration_sec, "cases": cases}}

def _write_latest_md(rc: int, stdout: str, stderr: str, used_json: bool) -> None:
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

@dataclass
class CycleResult:
    pytest: dict
    git: dict

def run_cycle(pytest_args: str | None, base_ref: str, head_ref: str, title: str, enable_patch_notes: bool) -> tuple[CycleResult, str]:
    # GUI/mini-loop で未指定なら小ループ対象のみ実行
    args = pytest_args.split() if (pytest_args and pytest_args.strip()) else list(DEFAULT_MINILOOP_TARGETS)
    rc, out, err, used_json = _run_pytest(args)
    result_dict = _load_result(used_json)

    # ✅ pytestの結果JSONを必ず保存（以前の CycleResult の文字列保存を修正）
    JSON_PATH.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    _write_latest_md(rc, out or "", err or "", used_json)

    result = CycleResult(pytest=result_dict.get("pytest", {}), git={"branch": "", "commit": "", "is_dirty": False})
    return result, str(LATEST_MD)

if __name__ == "__main__":
    rc, out, err, used_json = _run_pytest(list(DEFAULT_MINILOOP_TARGETS))
    _write_latest_md(rc, out, err, used_json)
    # CLI実行時は終了コードだけ返す
    sys.exit(rc)
