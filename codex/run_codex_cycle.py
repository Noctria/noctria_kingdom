# codex/run_codex_cycle.py
from __future__ import annotations

import json
import os
import subprocess
import sys
import xml.etree.ElementTree as ET
import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Tuple

# ===== パス/レポート =====
PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = PROJECT_ROOT / "codex_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

JSON_PATH = REPORTS_DIR / "tmp.json"            # pytest-json-report の出力（またはJunit変換）
JUNIT_PATH = REPORTS_DIR / "tmp.junit.xml"      # json-report が無い場合のフォールバック
LATEST_MD = REPORTS_DIR / "latest_codex_cycle.md"
INVENTOR_MD = REPORTS_DIR / "inventor_suggestions.md"
HARMONIA_MD = REPORTS_DIR / "harmonia_review.md"
MINI_SUMMARY_MD = REPORTS_DIR / "mini_loop_summary.md"

# 🎯 小ループで回す対象（全体pytest.iniを変えずに限定収集）
DEFAULT_MINILOOP_TARGETS = [
    "tests/test_quality_gate_alerts.py",
    "tests/test_noctus_gate_block.py",
]

# ===== 依存（ローカル静的版のエージェント）=====
from codex.agents.inventor import propose_fixes, InventorOutput  # type: ignore
from codex.agents.harmonia import review, ReviewResult            # type: ignore


# ===== 実行系ユーティリティ =====
def _has_pytest_json_report() -> bool:
    """pytest-json-report プラグイン有無を検出"""
    return importlib.util.find_spec("pytest_jsonreport") is not None


def _pytest_env() -> dict:
    """src レイアウト解決（全体pytest.iniに手を入れず両立）"""
    env = os.environ.copy()
    add = f"{PROJECT_ROOT/'src'}:{PROJECT_ROOT}"
    env["PYTHONPATH"] = f"{add}:{env.get('PYTHONPATH','')}".strip(":")
    return env


def _run_pytest(pytest_args: List[str]) -> Tuple[int, str, str, bool]:
    """
    pytest を実行
    return: (rc, stdout, stderr, used_json_plugin)
    """
    used_json = _has_pytest_json_report()
    cmd = [sys.executable, "-m", "pytest", "-q", *pytest_args]
    if used_json:
        cmd += ["--json-report", f"--json-report-file={JSON_PATH}"]
    else:
        cmd += [f"--junitxml={JUNIT_PATH}"]
    proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, env=_pytest_env())
    return proc.returncode, proc.stdout, proc.stderr, used_json


def _load_result(used_json: bool) -> dict:
    """
    pytest-json-report があればそれを、無ければ JUnit を最小JSONに変換して返す。
    統一構造（おおまか）:
      {
        "summary": {...},      # total / passed / failed 等
        "tests": [ { "nodeid":..., "outcome":..., "call": {...}, ... }, ... ]
      }
    """
    if used_json and JSON_PATH.exists():
        # そのまま返す（pytest-json-report の形式）
        return json.loads(JSON_PATH.read_text(encoding="utf-8"))

    # --- フォールバック: JUnit → 簡易 JSON ---
    if not JUNIT_PATH.exists():
        return {"summary": {"total": 0, "passed": 0, "failed": 0, "errors": 0, "skipped": 0}, "tests": []}

    root = ET.parse(JUNIT_PATH).getroot()
    suite = root.find("testsuite") or root
    total = int(suite.attrib.get("tests", 0))
    failures = int(suite.attrib.get("failures", 0))
    errors = int(suite.attrib.get("errors", 0))
    skipped = int(suite.attrib.get("skipped", 0))
    duration_sec = float(suite.attrib.get("time", 0.0))

    tests: List[dict] = []
    for tc in suite.iterfind("testcase"):
        nodeid = f"{tc.attrib.get('classname','')}::{tc.attrib.get('name','')}".strip(":")
        outcome = "passed"
        call = {}
        f_elt, e_elt, s_elt = tc.find("failure"), tc.find("error"), tc.find("skipped")
        if f_elt is not None:
            outcome = "failed"
            call = {"longrepr": (f_elt.text or "").strip()}
        elif e_elt is not None:
            outcome = "error"
            call = {"longrepr": (e_elt.text or "").strip()}
        elif s_elt is not None:
            outcome = "skipped"
        tests.append({"nodeid": nodeid, "outcome": outcome, "call": call})

    passed = total - failures - errors - skipped
    return {
        "summary": {"total": total, "passed": passed, "failed": failures, "errors": errors, "skipped": skipped, "duration": duration_sec},
        "tests": tests,
    }


def _write_latest_md(rc: int, stdout: str, stderr: str, used_json: bool) -> None:
    LATEST_MD.write_text(
        "\n".join(
            [
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
                "",
            ]
        ),
        encoding="utf-8",
    )


# ===== 失敗抽出 & レポート書き出し =====
def _extract_failures(pyjson: dict) -> dict:
    """
    pytest-json-report or JUnit変換済みJSON から失敗/エラーのみ抽出
    return: {"failures": [ {nodeid, message, traceback}, ... ]}
    """
    tests = (pyjson or {}).get("tests", []) or []
    fails = []
    for t in tests:
        if t.get("outcome") in ("failed", "error"):
            call = t.get("call") or {}
            longrepr = call.get("longrepr") or t.get("longrepr") or ""
            fails.append(
                {
                    "nodeid": t.get("nodeid"),
                    "message": str(longrepr)[:2000],
                    "traceback": str(longrepr)[:4000],
                }
            )
    return {"failures": fails}


def _write_inventor_md(inv: InventorOutput) -> None:
    lines: List[str] = [
        "# Inventor Suggestions",
        "",
        f"**summary:** {inv.summary}",
        "",
        "## root_causes",
    ]
    lines += [f"- {x}" for x in (inv.root_causes or [])]
    lines += ["", "## patch_suggestions"]
    for ps in inv.patch_suggestions or []:
        lines += [
            f"### {ps.file} :: {ps.function}",
            "",
            "```diff",
            (ps.pseudo_diff or "").strip(),
            "```",
            "",
            f"_rationale_: {ps.rationale}",
            "",
        ]
    lines += ["## followup_tests"]
    lines += [f"- {t}" for t in (inv.followup_tests or [])]
    lines.append("")
    INVENTOR_MD.write_text("\n".join(lines), encoding="utf-8")


def _write_harmonia_md(res: ReviewResult) -> None:
    lines = ["# Harmonia Review", "", f"**verdict:** {res.verdict}", "", "## comments"]
    lines += [f"- {c}" for c in (res.comments or [])]
    lines.append("")
    HARMONIA_MD.write_text("\n".join(lines), encoding="utf-8")


def _write_mini_summary(pyjson: dict) -> None:
    s = (pyjson or {}).get("summary") or {}
    total = s.get("total", 0)
    passed = s.get("passed", 0)
    MINI_SUMMARY_MD.write_text(
        "\n".join(
            [
                "# Mini-Loop Summary",
                "",
                f"- total: {total}",
                f"- passed: {passed}",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


# ===== 外部エントリ =====
@dataclass
class CycleResult:
    # 互換用フィールド名だが、中身は pytest 結果JSON全体を保持する
    pytest: dict
    git: dict


def run_cycle(
    pytest_args: str | None,
    base_ref: str,
    head_ref: str,
    title: str,
    enable_patch_notes: bool,
) -> tuple[CycleResult, str]:
    # GUI/mini-loop で未指定なら“小ループ対象のみ”実行
    args = pytest_args.split() if (pytest_args and pytest_args.strip()) else list(DEFAULT_MINILOOP_TARGETS)

    rc, out, err, used_json = _run_pytest(args)
    result_dict = _load_result(used_json)

    # ✅ pytest結果のJSONを必ず保存（※mini_loop側で上書きしないこと）
    JSON_PATH.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2), encoding="utf-8")

    # 可読レポート
    _write_latest_md(rc, out or "", err or "", used_json)

    # 失敗→ Inventor / Harmonia、成功→ Summary
    failures_payload = _extract_failures(result_dict)
    if failures_payload["failures"]:
        inv_out = propose_fixes(failures_payload)
        _write_inventor_md(inv_out)

        harm = review(inv_out)
        _write_harmonia_md(harm)
    else:
        _write_mini_summary(result_dict)

    result = CycleResult(pytest=result_dict, git={"branch": "", "commit": "", "is_dirty": False})
    return result, str(LATEST_MD)


if __name__ == "__main__":
    # 手動実行: 小ループ対象で回す
    rc, out, err, used_json = _run_pytest(list(DEFAULT_MINILOOP_TARGETS))
    _write_latest_md(rc, out, err, used_json)
    # JSON も保存
    result_dict = _load_result(used_json)
    JSON_PATH.write_text(json.dumps(result_dict, ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(rc)
