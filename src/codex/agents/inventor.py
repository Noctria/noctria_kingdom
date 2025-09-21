# src/codex/agents/inventor.py
from __future__ import annotations

import datetime as dt
import json
import re
import textwrap
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

# =========================
# 既存: システムプロンプト
# =========================
INVENTOR_SYSTEM_PROMPT = """\
あなたは Noctria 王国の開発者AI『Inventor Scriptus』です。
役割: 失敗したテストに対し、原因仮説→修正方針→具体的な変更点を提案します。
制約:
- いきなり大改修せず、最小差分でテストを通す方針を優先
- 王国のコーディング規約（contractsの後方互換、observability統一）を尊重
- 変更は「パッチ候補（擬似diff）」「対象ファイル」「対象関数」を明記して提示
出力形式:
- "summary": 要約
- "root_causes": 箇条書き
- "patch_suggestions": [{file, function, pseudo_diff, rationale}]
- "followup_tests": 追試案
"""


# =========================
# 既存: データモデル (+最小強化)
# =========================
@dataclass
class PatchSuggestion:
    file: str
    function: str
    pseudo_diff: str
    rationale: str


@dataclass
class InventorOutput:
    summary: str
    root_causes: List[str]
    patch_suggestions: List[PatchSuggestion]
    followup_tests: List[str]

    # ★ 最小強化: 生成時刻とトレースID（観測性）
    generated_at: str
    trace_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        # asdict で十分（PatchSuggestion も展開される）
        return asdict(self)

    def to_markdown(self) -> str:
        lines: List[str] = []
        lines.append("# 🛠️ Inventor Scriptus — 修正案（Lv1）")

        # 既定は JST
        lines.append(f"\n- Generated: `{self.generated_at}`\n")
        if self.trace_id:
            lines.append(f"- Trace ID: `{self.trace_id}`\n")

        if self.summary:
            lines.append(f"**Summary**: {self.summary}\n")
        if self.root_causes:
            lines.append("## Root Causes\n")
            for rc in self.root_causes:
                lines.append(f"- {rc}")
            lines.append("")
        if self.patch_suggestions:
            lines.append("## Patch Suggestions\n")
            for i, p in enumerate(self.patch_suggestions, 1):
                lines.append(f"### {i}. `{p.file}` :: `{p.function}`")
                lines.append("\n**Rationale**\n")
                lines.append(f"- {p.rationale}\n")
                if p.pseudo_diff.strip():
                    lines.append("<details><summary>Pseudo Diff</summary>\n")
                    lines.append("```diff")
                    lines.append(p.pseudo_diff.strip())
                    lines.append("```")
                    lines.append("</details>\n")
        if self.followup_tests:
            lines.append("## Follow-up Tests\n")
            for t in self.followup_tests:
                lines.append(f"- {t}")
        lines.append("\n---\n")
        lines.append("1. 最小差分で修正 → 2. `pytest -q -k <nodeid>` → 3. 全体再実行")
        return "\n".join(lines)


# =====================================
# 新規: ヒューリスティック & 互換クラス
# =====================================
@dataclass
class _FailureCase:
    nodeid: str
    outcome: str
    duration: Optional[float]
    traceback: str


class InventorScriptus:
    """
    - Lv1 ヒューリスティック提案器
    - 互換API:
        * propose_fixes_structured(pytest_result) -> InventorOutput  （既存の構造化呼び出し向け）
        * propose_fixes(failures, context) -> str                      （mini_loop の Markdown 出力向け）
    - 追加API（ruff連携・最小実装）:
        * load_ruff_report(report_path) -> None
        * summarize_ruff() -> str
        * next_action_from_ruff() -> str
    """

    # ====== ruff runner 連携（追加） ======
    def __init__(self) -> None:
        # ruff レポートを読み込んだ結果を保持（任意）
        self._ruff_report: Dict[str, Any] = {}

    def load_ruff_report(self, report_path: str | Path) -> None:
        """
        ruff_runner.py が保存した JSON レポートを読み込む。
        期待フォーマット（簡約）:
        {
          "fix_mode": bool,
          "returncode": int,
          "patch_path": "codex_reports/patches/xxxx.patch" | null,
          "result": {"highlights": ["...","..."], ...}
        }
        """
        p = Path(report_path)
        if not p.exists():
            raise FileNotFoundError(f"Ruff report not found: {p}")
        self._ruff_report = json.loads(p.read_text(encoding="utf-8"))

    def summarize_ruff(self) -> str:
        """Ruff 実行結果の短い要約を返す。"""
        if not self._ruff_report:
            return "No ruff report loaded."
        res = self._ruff_report.get("result", {}) or {}
        highlights = "\n".join(res.get("highlights", []))
        return (
            "Inventor Summary (Ruff):\n"
            f"- Fix mode: {self._ruff_report.get('fix_mode')}\n"
            f"- Return code: {self._ruff_report.get('returncode')}\n"
            f"- Patch: {self._ruff_report.get('patch_path')}\n"
            f"--- Highlights ---\n{highlights}"
        )

    def next_action_from_ruff(self) -> str:
        """
        Ruff の returncode / patch 有無から単純な次アクションを提案。
        """
        if not self._ruff_report:
            return "No ruff report loaded."
        rc = self._ruff_report.get("returncode")
        if rc == 0:
            return "✅ Ruff: No issues detected. No action needed."
        patch = self._ruff_report.get("patch_path")
        if self._ruff_report.get("fix_mode") and patch:
            return f"📝 Ruff patch generated: {patch}（commit → PR を推奨）"
        return "⚠️ Ruff: Issues remain. `--fix` か手修正を検討してください。"

    # ====== 低レベル: パターン検出 ======
    def _detect_patterns(self, tb: str) -> List[str]:
        pats: List[str] = []
        if "ModuleNotFoundError:" in tb:
            pats.append("ModuleNotFoundError")
        if "ImportError:" in tb:
            pats.append("ImportError")
        if "AttributeError:" in tb:
            pats.append("AttributeError")
        if re.search(r"AssertionError[:\n ]", tb):
            pats.append("AssertionError")
        if re.search(r"TypeError[:\n ]", tb):
            pats.append("TypeError")
        return pats or ["GenericFailure"]

    # ====== 個別テンプレ（要点は最小差分・規約順守） ======
    def _suggest_for_modulenotfound(self, tb: str) -> PatchSuggestion:
        m = re.search(r"ModuleNotFoundError:\s*No module named '([^']+)'", tb)
        missing = m.group(1) if m else "unknown_module"
        return PatchSuggestion(
            file="requirements.txt",
            function="(dependency)",
            pseudo_diff=f"+ {missing}\n",
            rationale="依存追加。Airflow 等の import timeout 回避のため、重依存は遅延 import（関数内）も検討。",
        )

    def _suggest_for_importerror(self, tb: str) -> PatchSuggestion:
        m = re.search(r"cannot import name '([^']+)' from ([^\s]+)", tb)
        sym = m.group(1) if m else "Symbol"
        frm = m.group(2) if m else "module"
        return PatchSuggestion(
            file=f"{frm}",
            function=f"(export {sym})",
            pseudo_diff=textwrap.dedent(
                f"""\
                --- a/{frm}
                +++ b/{frm}
                @@
                + # {sym} を __all__ に追加、もしくは実装ファイルから再エクスポート
                """
            ),
            rationale="シンボル未公開/循環参照/破壊的変更のいずれか。最小差分で公開または呼び出し側を最新APIに合わせる。",
        )

    def _suggest_for_attributeerror(self, tb: str) -> PatchSuggestion:
        m = re.search(r"AttributeError: '([^']+)' object has no attribute '([^']+)'", tb)
        obj = m.group(1) if m else "Obj"
        attr = m.group(2) if m else "attr"
        return PatchSuggestion(
            file=f"(class {obj})",
            function=f"(ensure {attr})",
            pseudo_diff=textwrap.dedent(
                f"""\
                @@ class {obj}:
                -    # missing: {attr}
                +    def __init__(...):
                +        self.{attr} = ...
                """
            ),
            rationale="属性未設定/IF不一致。`__init__` での代入漏れや名称乖離を最小差分で補正。",
        )

    def _suggest_for_assertionerror(self, tb: str) -> PatchSuggestion:
        return PatchSuggestion(
            file="(target module)",
            function="(guard or logic)",
            pseudo_diff="(境界条件/期待値に合わせた最小ロジック修正)",
            rationale="テストが前提とする仕様/境界条件に合わせ、off-by-one や None/空などを最小修正。",
        )

    def _suggest_for_typeerror(self, tb: str) -> PatchSuggestion:
        return PatchSuggestion(
            file="(target function)",
            function="(signature/typing)",
            pseudo_diff="(引数名/数を実装に合わせるか *args/**kwargs 経由の互換層を暫定追加)",
            rationale="シグネチャ不一致/型ミスマッチ。まず互換層で最小修正→後続で整理。",
        )

    def _generic_suggestion(self, tb: str) -> PatchSuggestion:
        return PatchSuggestion(
            file="(target module)",
            function="(minimal fix)",
            pseudo_diff="(N/A: まず再現最小化とデバッグログ挿入で原因特定)",
            rationale="`pytest -q -k <nodeid>` で特定、ログ追加、最小差分での修正を優先。",
        )

    # ====== 既存の具体例ルール（プロジェクト固有） ======
    def _project_specific_rule(self, name: str, tb: str) -> Optional[PatchSuggestion]:
        # 例: Noctus/FeatureContext パターン
        if "test_noctus_gate_block" in name and "AttributeError" in tb and "context.get" in tb:
            return PatchSuggestion(
                file="src/plan_data/strategy_adapter.py",
                function="_bundle_to_dict_and_order",
                pseudo_diff=textwrap.dedent(
                    """\
                    --- a/src/plan_data/strategy_adapter.py
                    +++ b/src/plan_data/strategy_adapter.py
                    @@
                    -    ctx = features.context or {}
                    -    for k, v in ctx.items():
                    +    ctx = getattr(features, "context", None)
                    +    if ctx:
                    +        ctx_dict = ctx.dict() if hasattr(ctx, "dict") else dict(ctx)
                    +        for k, v in ctx_dict.items():
                             key = f"ctx_{k}" if k not in base else k
                             if key not in base:
                                 base[key] = v
                    """
                ),
                rationale="FeatureContext が pydantic モデルでも安全に動くよう .dict() に対応（最小差分）。",
            )
        if "QUALITY" in tb and "emit_alert" in tb:
            return PatchSuggestion(
                file="src/plan_data/quality_gate.py",
                function="emit_quality_alert",
                pseudo_diff="(必要に応じて kind を 'QUALITY.*' 形式へ正規化 — 期待に合わせ最小変更)",
                rationale="アラート種別の命名規則をテスト期待に合わせて軽微に整形。",
            )
        return None

    # ====== 構造化出力（既存互換 + 最小強化） ======
    def propose_fixes_structured(self, pytest_result: Dict[str, Any]) -> InventorOutput:
        """
        pytest_result 例（柔軟に対応）:
          {
            "failures": [{"nodeid": "...", "traceback": "...", "message": "..."}],
            "trace_id": "...",  # 任意
            ...
          }
        """
        failures_in = pytest_result.get("failures") or pytest_result.get("cases") or []
        suggestions: List[PatchSuggestion] = []
        root_causes: List[str] = []

        for f in failures_in[:10]:
            name = f.get("nodeid", "") or f.get("name", "")
            tb = f.get("traceback", "") or f.get("longrepr", "")
            msg = f.get("message", "") or f.get("outcome", "failure")
            root_causes.append(msg or "不明")

            # プロジェクト固有則を先に
            specific = self._project_specific_rule(name, tb)
            if specific:
                suggestions.append(specific)
                continue

            # 一般則
            pats = self._detect_patterns(tb)
            if "ModuleNotFoundError" in pats:
                suggestions.append(self._suggest_for_modulenotfound(tb))
            elif "ImportError" in pats:
                suggestions.append(self._suggest_for_importerror(tb))
            elif "AttributeError" in pats:
                suggestions.append(self._suggest_for_attributeerror(tb))
            elif "AssertionError" in pats:
                suggestions.append(self._suggest_for_assertionerror(tb))
            elif "TypeError" in pats:
                suggestions.append(self._suggest_for_typeerror(tb))
            else:
                suggestions.append(self._generic_suggestion(tb))

        # 生成時刻（JST）
        jst = dt.timezone(dt.timedelta(hours=9))
        generated_at = dt.datetime.now(tz=jst).isoformat(timespec="seconds")
        trace_id = pytest_result.get("trace_id")

        if not failures_in:
            # 失敗なしでも観測情報は付けて返す
            return InventorOutput(
                summary="失敗なし。修正提案は不要です。",
                root_causes=[],
                patch_suggestions=[],
                followup_tests=[],
                generated_at=generated_at,
                trace_id=trace_id,
            )

        # ★ 最小強化: followup_tests を必ず最低1件は入れる
        followups: List[str] = [
            "pytest -q -k <failing-nodeid>",
            "pytest -q tests/test_quality_gate_alerts.py tests/test_noctus_gate_block.py",
        ]

        return InventorOutput(
            summary="失敗テストに対する最小修正案の下書き",
            root_causes=root_causes,
            patch_suggestions=(suggestions if suggestions else [self._generic_suggestion("")]),
            followup_tests=followups,  # ← 空にならない
            generated_at=generated_at,
            trace_id=trace_id,
        )

    # ====== Markdown 出力（mini_loop 用の互換API） ======
    def propose_fixes(self, failures: List[Dict[str, Any]], context: Dict[str, Any]) -> str:
        """
        mini_loop 互換: 失敗配列 + サマリコンテキストを受け取り、Markdown を返す
        failures: [{nodeid, outcome, duration, traceback}, ...]
        """
        fs = [
            _FailureCase(
                nodeid=f.get("nodeid", ""),
                outcome=f.get("outcome", "failed"),
                duration=f.get("duration"),
                traceback=f.get("traceback", ""),
            )
            for f in failures
        ]

        header = (
            "# 🛠️ Inventor Scriptus — 修正案（Lv1）\n\n"
            f"- Generated: `{context.get('generated_at', '')}`\n"
            f"- Pytest: total={context.get('pytest_summary', {}).get('total', 0)}, "
            f"failed={context.get('pytest_summary', {}).get('failed', 0)}, "
            f"errors={context.get('pytest_summary', {}).get('errors', 0)}\n"
        )
        if context.get("trace_id"):
            header += f"- Trace ID: `{context.get('trace_id')}`\n"

        if not fs:
            return header + "\n✅ 失敗はありません。提案は不要です。\n"

        blocks: List[str] = []
        for f in fs:
            # プロジェクト固有 → 一般パターン
            ps = self._project_specific_rule(f.nodeid, f.traceback)
            if not ps:
                pats = self._detect_patterns(f.traceback)
                if "ModuleNotFoundError" in pats:
                    ps = self._suggest_for_modulenotfound(f.traceback)
                elif "ImportError" in pats:
                    ps = self._suggest_for_importerror(f.traceback)
                elif "AttributeError" in pats:
                    ps = self._suggest_for_attributeerror(f.traceback)
                elif "AssertionError" in pats:
                    ps = self._suggest_for_assertionerror(f.traceback)
                elif "TypeError" in pats:
                    ps = self._suggest_for_typeerror(f.traceback)
                else:
                    ps = self._generic_suggestion(f.traceback)

            tb_tail = "\n".join(f.traceback.splitlines()[-30:])
            block = (
                f"### `{f.nodeid}` — {f.outcome}\n\n"
                f"**修正方針（候補）**\n\n"
                f"- 対象: `{ps.file}` / `{ps.function}`\n"
                f"- 根拠: {ps.rationale}\n\n"
                + (
                    "<details><summary>Pseudo Diff</summary>\n\n```diff\n"
                    f"{ps.pseudo_diff.strip()}\n```\n</details>\n\n"
                    if ps.pseudo_diff.strip()
                    else ""
                )
                + "<details><summary>Traceback (tail)</summary>\n\n```text\n"
                f"{tb_tail}\n```\n</details>\n"
            )
            blocks.append(block)

        tail = (
            "\n---\n"
            "#### 次のアクション（人手 or 後続AI）\n"
            "1. 上記の候補から **最小修正**を選び、該当ファイルを更新\n"
            "2. `pytest -q -k <nodeid>` で単体再実行\n"
            "3. 全体を `python -m codex.mini_loop` または CI で再検証\n"
        )
        return header + "\n".join(blocks) + tail


# ======================================================
# 既存互換: モジュールレベル関数（壊さないために残す）
# ======================================================
def propose_fixes(pytest_result: Dict[str, Any]) -> InventorOutput:
    """
    既存呼び出し互換の関数。内部で InventorScriptus を使って構造化結果を返す。
    """
    return InventorScriptus().propose_fixes_structured(pytest_result)
