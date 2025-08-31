# codex/tools/review_pipeline.py
from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

from codex.tools.json_parse import load_json, build_pytest_result_for_inventor

# 既存ヒューリスティック Inventor/Harmonia を利用
from codex.agents.inventor import propose_fixes, InventorOutput
from codex.agents.harmonia import review, ReviewResult

# 🆕 自動パッチ生成ユーティリティ
from codex.tools.patch_gen import generate_patches, write_index_md, PATCHES_DIR

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "codex_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TMP_JSON = REPORTS_DIR / "tmp.json"
INV_MD = REPORTS_DIR / "inventor_suggestions.md"
HAR_MD = REPORTS_DIR / "harmonia_review.md"


def _md_escape(x: str) -> str:
    return (
        x.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).astimezone().isoformat(timespec="seconds")


def _extract_summary_and_failed_tests(data: Dict[str, Any]) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """
    pytest-json-report の構造から合計/失敗の要約と、失敗テストの明細を抽出。
    - 失敗が無ければ failed_tests は空配列を返す。
    """
    summary = dict(data.get("summary") or {})
    passed = int(summary.get("passed") or 0)
    total = int(summary.get("total") or summary.get("collected") or 0)
    failed = max(0, total - passed)
    summ = {"passed": passed, "failed": failed, "total": total}

    tests = data.get("tests") or []
    failed_tests: List[Dict[str, Any]] = []
    for t in tests:
        if (t.get("outcome") or "").lower() == "failed":
            msg = ""
            for phase in ("setup", "call", "teardown"):
                phase_obj = t.get(phase)
                if isinstance(phase_obj, dict) and (phase_obj.get("outcome") == "failed"):
                    cand = phase_obj.get("longrepr") or phase_obj.get("crash")
                    if cand:
                        msg = str(cand)
                        break
            failed_tests.append(
                {
                    "nodeid": t.get("nodeid", ""),
                    "lineno": t.get("lineno"),
                    "message": msg,
                }
            )
    return summ, failed_tests


def write_inventor_markdown(
    out: InventorOutput,
    *,
    header_note: Optional[str] = None,
    pytest_summary: Optional[Dict[str, int]] = None,
) -> None:
    lines: List[str] = []
    lines.append("# Inventor Scriptus — 修正案")
    lines.append("")
    lines.append(f"- Generated at: `{_now_iso()}`")
    if pytest_summary:
        lines.append(
            f"- Pytest Summary: **{pytest_summary.get('passed',0)}/{pytest_summary.get('total',0)} passed**, "
            f"failed={pytest_summary.get('failed',0)}"
        )
    if header_note:
        lines.append(f"- Note: {_md_escape(header_note)}")
    lines.append("")
    lines.append(f"**Summary**: {_md_escape(out.summary)}")
    lines.append("")
    lines.append("## Root Causes")
    if out.root_causes:
        for r in out.root_causes:
            lines.append(f"- {_md_escape(str(r))}")
    else:
        lines.append("- (none)")
    lines.append("")
    lines.append("## Patch Suggestions")
    if out.patch_suggestions:
        for i, p in enumerate(out.patch_suggestions, 1):
            lines.append(f"### {i}. `{p.file}` :: `{p.function}`")
            lines.append("")
            lines.append("**Rationale**")
            lines.append("")
            lines.append(f"- {_md_escape(p.rationale)}")
            lines.append("")
            lines.append("**Pseudo Diff**")
            lines.append("")
            lines.append("```diff")
            lines.append(p.pseudo_diff.strip() if p.pseudo_diff else "(N/A)")
            lines.append("```")
            lines.append("")
    else:
        lines.append("- (no suggestions)")
        lines.append("")
    lines.append("## Follow-up tests")
    if out.followup_tests:
        for t in out.followup_tests:
            lines.append(f"- `{t}`")
    else:
        lines.append("- `pytest -q`")
    lines.append("")

    INV_MD.write_text("\n".join(lines), encoding="utf-8")


def write_harmonia_markdown(
    rv: ReviewResult,
    *,
    header_note: Optional[str] = None,
    pytest_summary: Optional[Dict[str, int]] = None,
) -> None:
    lines: List[str] = []
    lines.append("# Harmonia Ordinis — レビューレポート")
    lines.append("")
    lines.append(f"- Generated at: `{_now_iso()}`")
    if pytest_summary:
        lines.append(
            f"- Pytest Summary: **{pytest_summary.get('passed',0)}/{pytest_summary.get('total',0)} passed**, "
            f"failed={pytest_summary.get('failed',0)}"
        )
    if header_note:
        lines.append(f"- Context: {_md_escape(header_note)}")
    lines.append("")
    lines.append(f"**Verdict**: `{rv.verdict}`")
    lines.append("")
    lines.append("## Comments")
    if rv.comments:
        for c in rv.comments:
            lines.append(f"- {_md_escape(c)}")
    else:
        lines.append("- (no comments)")
    lines.append("")

    HAR_MD.write_text("\n".join(lines), encoding="utf-8")


def _build_outputs_from_json(py_data: Dict[str, Any]) -> Tuple[InventorOutput, ReviewResult]:
    pytest_result_for_inventor = build_pytest_result_for_inventor(py_data)
    inv = propose_fixes(pytest_result_for_inventor)
    rv = review(inv)
    return inv, rv


def main() -> int:
    """
    - codex_reports/tmp.json を読み取り
    - Inventor 修正案 / Harmonia レビューを Markdown で生成
    - さらに自動パッチを生成して patches/ 以下に保存
    """
    header_note = None
    pytest_summary: Optional[Dict[str, int]] = None

    if not TMP_JSON.exists():
        header_note = "No pytest JSON found. Skipped proposing fixes."
        empty_inv = InventorOutput(
            summary="No pytest result available.",
            root_causes=[],
            patch_suggestions=[],
            followup_tests=["pytest -q"],
        )
        rv = review(empty_inv)
        write_inventor_markdown(empty_inv, header_note=header_note, pytest_summary=None)
        write_harmonia_markdown(rv, header_note=header_note, pytest_summary=None)
        # パッチも空 index を出力
        PATCHES_DIR.mkdir(parents=True, exist_ok=True)
        write_index_md(empty_inv, [])
        return 0

    try:
        data = load_json(TMP_JSON)
    except Exception as e:
        header_note = f"Failed to load tmp.json: {e}"
        empty_inv = InventorOutput(
            summary="tmp.json could not be parsed.",
            root_causes=[str(e)],
            patch_suggestions=[],
            followup_tests=["pytest -q"],
        )
        rv = review(empty_inv)
        write_inventor_markdown(empty_inv, header_note=header_note, pytest_summary=None)
        write_harmonia_markdown(rv, header_note=header_note, pytest_summary=None)
        PATCHES_DIR.mkdir(parents=True, exist_ok=True)
        write_index_md(empty_inv, [])
        return 0

    pytest_summary, failed_tests = _extract_summary_and_failed_tests(data)
    if pytest_summary.get("failed", 0) == 0:
        header_note = "All tests passed. Keeping suggestions minimal."

    inv, rv = _build_outputs_from_json(data)

    # Markdown 出力
    write_inventor_markdown(inv, header_note=header_note, pytest_summary=pytest_summary)
    write_harmonia_markdown(rv, header_note=header_note, pytest_summary=pytest_summary)

    # 🆕 パッチ生成
    PATCHES_DIR.mkdir(parents=True, exist_ok=True)
    generated = generate_patches(inv)
    write_index_md(inv, generated)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
