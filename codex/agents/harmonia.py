# codex/agents/harmonia.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import textwrap

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
    verdict: str  # "APPROVE" | "REVISE"
    comments: List[str]

class HarmoniaOrdinis:
    """
    Harmonia レビュー実装（Lv1）
      - review_structured(): InventorOutput を受けて構造化レビュー
      - review_markdown(): 失敗配列 + InventorのMarkdown を受けて Markdown レビューを生成（mini_loop 用）
      - to_markdown(): ReviewResult を Markdown へ
    """

    # ===== 低レベルチェック（構造・文字列の両方で使用） =====
    def _check_minimal_change(self, ps: PatchSuggestion) -> Optional[str]:
        # 擬似diffが空、あるいは「大改修を示唆する広域変更」なら注意（簡易）
        if not ps.pseudo_diff or ps.pseudo_diff.strip() in {"(N/A)", "(N/A: まず再現最小化とデバッグログ挿入で原因特定)"}:
            return f"`{ps.file}` の差分が不明瞭。最小差分の擬似diffを提示してください。"
        if "from .* import *" in ps.pseudo_diff:
            return "ワイルドカード import は副作用が読めないため不可。限定 import で。"
        return None

    def _check_backward_compat(self, ps: PatchSuggestion) -> Optional[str]:
        # contracts破壊につながりそうな文言を簡易検出
        risky = any(key in ps.pseudo_diff for key in ["delete", "remove", "rename(", "deprecated"])
        if risky:
            return "後方互換を損ねる可能性がある変更が含まれます。契約(API/スキーマ)の互換を維持してください。"
        return None

    def _check_observability(self, ps: PatchSuggestion) -> Optional[str]:
        # 重要ロジック修正時はログ/メトリクスが必要な場合がある（ガイド）
        if "quality_gate" in ps.file or "risk" in ps.file or "adapter" in ps.file:
            return "重要経路の修正です。`observability.py` 相当のログ/メトリクス追跡を検討してください。"
        return None

    def _check_project_specific(self, ps: PatchSuggestion) -> List[str]:
        notes: List[str] = []
        # pydantic v1/v2 互換（dict/model_dump）
        if "strategy_adapter.py" in ps.file and ("dict()" in ps.pseudo_diff or "model_dump" in ps.pseudo_diff):
            notes.append("pydantic v1 (`.dict()`) / v2 (`.model_dump()`) の両対応メモを備考に追記してください。")
        return notes

    # ===== 構造化レビュー =====
    def review_structured(self, inventor_out: InventorOutput) -> ReviewResult:
        comments: List[str] = []
        verdict = "APPROVE"

        if not inventor_out.patch_suggestions:
            comments.append("パッチ案が空。最低1件は具体差分を提示してください。")
            return ReviewResult(verdict="REVISE", comments=comments)

        for ps in inventor_out.patch_suggestions:
            # 既存ルール: ファイル未特定
            if ps.file.startswith("(検出できず)"):
                comments.append("修正対象の特定が曖昧。具体ファイル・関数・差分を明記して再提案を。")
                verdict = "REVISE"

            # 最小差分性
            msg = self._check_minimal_change(ps)
            if msg:
                comments.append(msg)
                verdict = "REVISE"

            # 後方互換性
            msg = self._check_backward_compat(ps)
            if msg:
                comments.append(msg)
                verdict = "REVISE"

            # 観測性ログ
            msg = self._check_observability(ps)
            if msg:
                comments.append(msg)

            # プロジェクト固有の補足
            comments.extend(self._check_project_specific(ps))

        # 追試の有無（再現性）
        if not inventor_out.followup_tests:
            comments.append("追試案が未提示。`pytest -q -k <nodeid>` などの再現/再実行手順を明記してください。")
            verdict = "REVISE"

        return ReviewResult(verdict=verdict, comments=comments)

    # ===== Markdown レビュー（mini_loop 用） =====
    def review_markdown(
        self,
        failures: List[Dict[str, Any]],
        inventor_suggestions: str,
        principles: List[str],
    ) -> str:
        def _check_completeness() -> str:
            ok = True
            notes = []
            for f in failures:
                nodeid = f.get("nodeid", "")
                if nodeid and (nodeid not in inventor_suggestions):
                    ok = False
                    notes.append(f"- `{nodeid}` への具体提案なし（網羅性不足）")
            if ok:
                return "✅ すべての失敗ケースに対応提案があります。"
            return "⚠️ 網羅性に課題:\n" + "\n".join(notes)

        def _check_side_effects() -> str:
            risky = any(k in inventor_suggestions.lower() for k in ["# pragma: no cover", "pass  # todo", "except:"])
            if risky:
                return "⚠️ テスト無効化/広域 except など、隠蔽的修正の可能性があります。別解を検討してください。"
            return "✅ 副作用が大きそうな提案は含まれていません。"

        def _check_guidelines() -> str:
            lines = ["- " + p for p in principles]
            return "📐 準拠すべき方針:\n" + "\n".join(lines)

        def _check_repro() -> str:
            ok = "pytest -q -k" in inventor_suggestions or "python -m codex.mini_loop" in inventor_suggestions
            return "✅ 再現/再実行手順が記載されています。" if ok else "⚠️ 再現手順の記載が不足しています。"

        header = "# 🧭 Harmonia Ordinis — レビュー（Lv1）\n\n"
        if not failures:
            return header + "✅ 失敗ケースはありません。レビュー対象なし。\n"

        parts = [
            _check_completeness(),
            _check_side_effects(),
            _check_guidelines(),
            _check_repro(),
        ]
        tail = textwrap.dedent("""
        ---
        #### 次のアクション（推奨）
        1. 影響範囲の小さい修正を優先（テストを落とさず挙動を改善）
        2. 可能なら該当箇所に **失敗再現の最小テスト** を追加
        3. 変更後は `pytest -q --maxfail=20 --durations=10` で全体再実行
        """)
        return header + "\n\n".join(parts) + "\n" + tail

    # ===== 構造化結果 → Markdown 変換 =====
    def to_markdown(self, result: ReviewResult) -> str:
        lines = ["# 🧭 Harmonia Ordinis — レビュー（Lv1）", ""]
        lines.append(f"- Verdict: **{result.verdict}**\n")
        if result.comments:
            lines.append("## Comments")
            for c in result.comments:
                lines.append(f"- {c}")
            lines.append("")
        return "\n".join(lines)

# =========================================
# 既存互換 API（壊さないために残す・強化版）
# =========================================
def review(inventor_out: InventorOutput) -> ReviewResult:
    """
    既存互換の関数。内部で HarmoniaOrdinis を用いて審査を行う。
    - 既存ロジック（file 未特定・pydantic 注意）を包含しつつ、追加の最小差分/後方互換/追試チェックを実施。
    """
    harmonia = HarmoniaOrdinis()
    return harmonia.review_structured(inventor_out)
