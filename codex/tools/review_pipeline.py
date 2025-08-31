# codex/tools/review_pipeline.py
from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List

from codex.tools.json_parse import load_json, build_pytest_result_for_inventor

# 既存ヒューリスティックInventor/Harmoniaを利用
from codex.agents.inventor import propose_fixes, InventorOutput, PatchSuggestion
from codex.agents.harmonia import review, ReviewResult

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "codex_reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

TMP_JSON = REPORTS_DIR / "tmp.json"
INV_MD = REPORTS_DIR / "inventor_suggestions.md"
HAR_MD = REPORTS_DIR / "harmonia_review.md"

def _md_escape(x: str) -> str:
    return x.replace("<", "&lt;").replace(">", "&gt;")

def write_inventor_markdown(out: InventorOutput) -> None:
    lines: List[str] = []
    lines.append("# Inventor Scriptus — 修正案\n")
    lines.append(f"**Summary**: {out.summary}\n")
    lines.append("## Root Causes\n")
    for r in out.root_causes or []:
        lines.append(f"- {_md_escape(str(r))}")
    lines.append("\n## Patch Suggestions\n")
    if out.patch_suggestions:
        for i, p in enumerate(out.patch_suggestions, 1):
            lines.append(f"### {i}. `{p.file}` :: `{p.function}`")
            lines.append("")
            lines.append("**Rationale**")
            lines.append("")
            lines.append(f"- {_md_escape(p.rationale)}\n")
            lines.append("**Pseudo Diff**")
            lines.append("")
            lines.append("```diff")
            lines.append(p.pseudo_diff.strip() if p.pseudo_diff else "(N/A)")
            lines.append("```\n")
    else:
        lines.append("- (no suggestions)\n")
    lines.append("## Follow-up tests\n")
    for t in out.followup_tests or []:
        lines.append(f"- `{t}`")
    INV_MD.write_text("\n".join(lines), encoding="utf-8")

def write_harmonia_markdown(rv: ReviewResult) -> None:
    lines: List[str] = []
    lines.append("# Harmonia Ordinis — レビューレポート\n")
    lines.append(f"**Verdict**: `{rv.verdict}`\n")
    lines.append("## Comments\n")
    if rv.comments:
        for c in rv.comments:
            lines.append(f"- {_md_escape(c)}")
    else:
        lines.append("- (no comments)")
    HAR_MD.write_text("\n".join(lines), encoding="utf-8")

def main() -> int:
    if not TMP_JSON.exists():
        # 失敗が無い/まだ実行されていない場合でも空レポートを生成
        empty_inv = InventorOutput(
            summary="No pytest JSON found. Skipped proposing fixes.",
            root_causes=[],
            patch_suggestions=[],
            followup_tests=["pytest -q"],
        )
        write_inventor_markdown(empty_inv)
        write_harmonia_markdown(review(empty_inv))
        return 0

    data = load_json(TMP_JSON)
    pytest_result = build_pytest_result_for_inventor(data)

    inv = propose_fixes(pytest_result)
    rv = review(inv)

    write_inventor_markdown(inv)
    write_harmonia_markdown(rv)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
