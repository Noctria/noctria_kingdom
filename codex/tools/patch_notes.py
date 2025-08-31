from __future__ import annotations
from typing import List
from dataclasses import dataclass
from .pytest_runner import run_pytest
from ..agents.inventor import propose_fixes, InventorOutput
from ..agents.harmonia import review, ReviewResult

def make_patch_notes(tests: List[str]) -> str:
    """
    テストを実行 → 発見された失敗から Inventor の修正案 → Harmonia レビュー
    を Markdown ノートとしてまとめる（LV1では提案のみ）
    """
    result = run_pytest(tests)
    md = []
    md.append("## Codex Cycle Report")
    md.append(f"- returncode: {result['returncode']}")
    md.append("")

    if result["returncode"] == 0:
        md.append("✅ All selected tests passed.")
        return "\n".join(md)

    md.append("### Failures (summary)")
    for f in result["failures"][:10]:
        md.append(f"- {f.get('message','(no message)')}")

    inventor_out: InventorOutput = propose_fixes(result)
    md.append("\n### Inventor Scriptus — Patch Suggestions")
    md.append(f"- summary: {inventor_out.summary}")
    md.append("- root_causes:")
    for rc in inventor_out.root_causes:
        md.append(f"  - {rc}")
    for ps in inventor_out.patch_suggestions:
        md.append(f"\n#### File: {ps.file} — {ps.function}")
        md.append("```diff")
        md.append(ps.pseudo_diff.strip() or "(no diff)")
        md.append("```")
        md.append(f"_rationale_: {ps.rationale}")

    review_out: ReviewResult = review(inventor_out)
    md.append("\n### Harmonia Ordinis — Review")
    md.append(f"- verdict: **{review_out.verdict}**")
    if review_out.comments:
        md.append("- comments:")
        for c in review_out.comments:
            md.append(f"  - {c}")

    md.append("\n### Next Steps")
    md.append("- Run follow-up tests:")
    for t in inventor_out.followup_tests:
        md.append(f"  - `{t}`")

    return "\n".join(md)
