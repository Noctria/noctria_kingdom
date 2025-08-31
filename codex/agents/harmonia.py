from __future__ import annotations
from dataclasses import dataclass
from typing import List
from .inventor import InventorOutput, PatchSuggestion

HARMONIA_SYSTEM_PROMPT = """\
あなたは Noctria 王国のレビュワーAI『Harmonia Ordinis』です。
役割: 提案パッチの妥当性・後方互換・王国方針整合を審査し、必要なら修正指示を返す。
審査観点:
- 変更が最小か？副作用は？contractsの破壊はないか？
- テスト分離方針（軽量/重）と整合しているか？
- observability/logging が妥当か？
出力形式:
- "verdict": APPROVE / REVISE
- "comments": 箇条書き
"""

@dataclass
class ReviewResult:
    verdict: str
    comments: List[str]

def review(inventor_out: InventorOutput) -> ReviewResult:
    comments: List[str] = []
    verdict = "APPROVE"

    for ps in inventor_out.patch_suggestions:
        if ps.file.startswith("(検出できず)"):
            comments.append("修正対象の特定が曖昧。具体ファイル・関数・差分を明記して再提案を。")
            verdict = "REVISE"
        if "strategy_adapter.py" in ps.file and "dict()" in ps.pseudo_diff:
            comments.append("pydantic v1/v2 互換の .dict()/model_dump 両対応の備考も追記を。")
    if not inventor_out.patch_suggestions:
        verdict = "REVISE"
        comments.append("パッチ案が空。最低1件は具体差分を提示してください。")

    return ReviewResult(verdict=verdict, comments=comments)
