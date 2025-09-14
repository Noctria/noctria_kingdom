# src/codex/agents/harmonia.py
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Iterable, Sequence
import textwrap
import logging
import os
import json
import math

from .inventor import InventorOutput, PatchSuggestion

# =============================================================================
# Logger（Airflow タスクロガーに寄せつつ、ローカル単体実行でも動作）
# =============================================================================
LOGGER = logging.getLogger("airflow.task")
if not LOGGER.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

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

# =============================================================================
# モード・重み設定
# =============================================================================
def _env_mode() -> str:
    """
    NOCTRIA_HARMONIA_MODE = "offline" | "api" | "auto"  (default: offline)
    - offline: 既存の構造化ローカル審査のみ
    - api    : LLM APIでの要約/補足コメント（失敗時は自動でofflineへフォールバック）
    - auto   : apiを試して失敗ならoffline
    """
    mode = os.getenv("NOCTRIA_HARMONIA_MODE", "offline").strip().lower()
    return mode if mode in {"offline", "api", "auto"} else "offline"


_DEFAULT_WEIGHTS = {
    # “weighted” リランク時の係数（大きいほど寄与）
    "quality": 1.00,      # 提案品質: 高いほど良い (+)
    "risk_adj": 0.90,     # リスク調整リターン: 高いほど良い (+)
    "risk": 0.60,         # リスク: 低いほど良い  (-)
    "size": 0.25,         # 取引サイズ: 過大は減点 (-, 非線形)
}

def _load_weights() -> Dict[str, float]:
    raw = os.getenv("HARMONIA_WEIGHTS", "").strip()
    if not raw:
        return dict(_DEFAULT_WEIGHTS)
    try:
        data = json.loads(raw)
        w = dict(_DEFAULT_WEIGHTS)
        for k, v in (data or {}).items():
            if isinstance(v, (int, float)) and k in w:
                w[k] = float(v)
        return w
    except Exception:
        LOGGER.warning("HARMONIA_WEIGHTS のJSON解釈に失敗。デフォルトを使用します。")
        return dict(_DEFAULT_WEIGHTS)


# =============================================================================
# 型
# =============================================================================
@dataclass
class ReviewResult:
    verdict: str  # "APPROVE" | "REVISE"
    comments: List[str]


# =============================================================================
# 本体
# =============================================================================
class HarmoniaOrdinis:
    """
    Harmonia レビュー実装（Lv1ベース → 強化）
      - review_structured(): InventorOutput を受けて構造化レビュー（オフラインの基盤）
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

        if not getattr(inventor_out, "patch_suggestions", None):
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
        if not getattr(inventor_out, "followup_tests", None):
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


# =============================================================================
# 既存互換 API（壊さないために残す・強化版）
# - review(): オフライン審査に加え、モードが api/auto の場合はLLMで補足コメントを付与（失敗時はoffline）。
# =============================================================================
def _api_review(inventor_out: InventorOutput) -> Optional[ReviewResult]:
    """
    軽量APIレビュー。無ければ None（呼び出し側でofflineを使う）。
    verdict は "APPROVE"/"REVISE" に丸める。
    """
    try:
        import openai  # type: ignore
    except Exception:
        LOGGER.warning("openai 未導入のため APIレビューはスキップします。")
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY_NOCTRIA")
    if not api_key:
        LOGGER.warning("OPENAI_API_KEY が未設定のため APIレビューはスキップします。")
        return None

    # openai-python のレガシー互換（v1/v4で書き分け不要の最低限）
    try:
        # 対象の要約（サイズ抑制）
        payload = {
            "patch_count": len(getattr(inventor_out, "patch_suggestions", []) or []),
            "followup_tests": bool(getattr(inventor_out, "followup_tests", None)),
            "files": [getattr(ps, "file", "") for ps in (getattr(inventor_out, "patch_suggestions", []) or [])][:10],
        }
        # v1スタイル（chat.completions）
        resp = openai.chat.completions.create(  # type: ignore[attr-defined]
            model=model,
            messages=[
                {"role": "system", "content": HARMONIA_SYSTEM_PROMPT},
                {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
            ],
            temperature=0.2,
            max_tokens=400,
        )
        text = (resp.choices[0].message.content or "").strip()
    except Exception as e:
        LOGGER.exception("APIレビューに失敗: %s", e)
        return None

    lower = text.lower()
    if "approve" in lower:
        verdict = "APPROVE"
    else:
        # "reject" 相当は運用上 REVISE に丸める
        verdict = "REVISE"

    # 最初の20行程度をコメントへ
    comments = [c for c in text.split("\n") if c.strip()][:20]
    return ReviewResult(verdict=verdict, comments=comments)


def review(inventor_out: InventorOutput) -> ReviewResult:
    """
    既存互換の関数。内部で HarmoniaOrdinis を用いて審査を行う。
    - mode=offline: 構造化ローカル審査のみ
    - mode=api/auto: 可能ならAPIコメントを付与（失敗時はofflineへフォールバック）
    """
    harmonia = HarmoniaOrdinis()
    base = harmonia.review_structured(inventor_out)

    mode = _env_mode()
    if mode == "offline":
        return base

    api_res = _api_review(inventor_out)
    if api_res is None:
        # auto/api でもAPI失敗時はoffline結果
        return base

    # マージ：厳しめに判定（どちらかがREVISEならREVISE）
    verdict = "REVISE" if (base.verdict != "APPROVE" or api_res.verdict != "APPROVE") else "APPROVE"
    comments = []
    comments.extend(base.comments)
    # 同じ内容をだぶつかせない程度に付与
    for c in api_res.comments:
        if c not in comments:
            comments.append(c)
        if len(comments) >= 40:
            break
    return ReviewResult(verdict=verdict, comments=comments)


# =============================================================================
# Harmonia リランク
#   - 従来の「risk_scoreベースの簡易調整」をデフォルト（後方互換）
#   - HARMONIA_RERANK=weighted で “重み付きスコア” に切替可能
# =============================================================================
def _safe_get(obj: Any, key: str, default: Any = None) -> Any:
    if hasattr(obj, key):
        try:
            return getattr(obj, key)
        except Exception:
            pass
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def _intent_for_bonus(obj: Any) -> str:
    """
    ロング判定のための意図値取得：
      - 'intent' が 'LONG' / 'SHORT' / 'FLAT' の場合を優先
      - それ以外に 'BUY' / 'SELL' を許容（Inventor 側ビュー互換）
    """
    raw = (_safe_get(obj, "intent", "") or "").upper()
    if raw in {"LONG", "SHORT", "FLAT"}:
        return raw
    if raw == "BUY":
        return "LONG"
    if raw == "SELL":
        return "SHORT"
    return "FLAT"


def _get_num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        if isinstance(x, (int, float)):
            return float(x)
        if isinstance(x, str) and x.strip() != "":
            return float(x)
        return default
    except Exception:
        return default


def _peek(proposal: Any, *names: str, default: float = 0.0) -> float:
    """dictでもobjでもOKな数値取得"""
    for n in names:
        if isinstance(proposal, dict) and n in proposal:
            return _get_num(proposal.get(n), default)
        if hasattr(proposal, n):
            return _get_num(getattr(proposal, n), default)
    return default


def _score_weighted(p: Any, w: Dict[str, float]) -> float:
    """
    “weighted” スコア:
      S = + w_q * quality
          + w_ra * risk_adjusted
          - w_r * risk_score
          - w_s * size_penalty   (size ペナルティは log1p)
    属性が無い場合は0として扱う（堅牢性優先）。
    """
    q = _peek(p, "quality", "score_quality", default=0.0)
    ra = _peek(p, "risk_adjusted", "risk_adj", default=0.0)
    r = _peek(p, "risk_score", "risk", default=0.0)  # 小さいほど良い
    sz = _peek(p, "qty_raw", "size", default=0.0)

    size_penalty = math.log1p(max(0.0, sz))
    s = (w["quality"] * q) + (w["risk_adj"] * ra) - (w["risk"] * r) - (w["size"] * size_penalty)
    return float(s)


def rerank_candidates(
    candidates: List[Any] | Iterable[Any],
    context: Optional[Dict[str, Any]] = None,
    quality: Optional[Dict[str, Any]] = None,
) -> List[Any]:
    """
    候補のリランク（pydantic model / dict 両対応）。
    デフォルト（後方互換）: risk_score をベースに、欠損/ラグの減点・LONGボーナスを加えた簡易調整。
    環境変数 HARMONIA_RERANK=weighted で “重み付き” 評価へ切替可能。
    戻り値はスコア降順の **新しいリスト**（元リストは破壊しない）。
    """
    mode = os.getenv("HARMONIA_RERANK", "simple").strip().lower()
    ctx = context or {}
    q = quality or {}

    # ==========================
    # simple（従来ロジック）
    # ==========================
    if mode != "weighted":
        # --- ペナルティ係数の算出 ---
        try:
            missing = float(_safe_get(q, "missing_ratio", 0.0) or 0.0)
        except Exception:
            missing = 0.0
        try:
            lag = float(_safe_get(ctx, "data_lag_min", _safe_get(q, "data_lag_min", 0.0)) or 0.0)
        except Exception:
            lag = 0.0

        scored: List[Tuple[float, Any]] = []
        base_list = list(candidates or [])
        for c in base_list:
            base = _safe_get(c, "risk_score", 0.5)
            try:
                base = float(base if base is not None else 0.5)
            except Exception:
                base = 0.5

            intent_std = _intent_for_bonus(c)
            side_bonus = 0.01 if intent_std == "LONG" else 0.0
            # 欠損が多いほど、ラグが大きいほど減点（0.8〜1.0 の係数イメージ）
            penalty = max(0.0, 1.0 - missing * 2.0) * (1.0 if lag <= 5.0 else 0.8)
            adj = base * penalty + side_bonus

            # 可能なら派生スコアを書き戻し（失敗しても無視）
            try:
                setattr(c, "risk_score", base)
                setattr(c, "risk_adjusted", adj)
            except Exception:
                if isinstance(c, dict):
                    c["risk_score"] = base
                    c["risk_adjusted"] = adj

            scored.append((adj, c))

        scored.sort(key=lambda t: t[0], reverse=True)
        ranked = [c for _, c in scored]

        # 観測ログ
        try:
            top_intent = _safe_get(ranked[0], "intent", None) if ranked else None
            std_top = _intent_for_bonus(ranked[0]) if ranked else None
            LOGGER.info(
                "[Harmonia] reranked(simple) %s -> %s top=%s(std=%s) symbol=%s tf=%s trace=%s",
                len(base_list), len(ranked), top_intent, std_top,
                ctx.get("symbol"), ctx.get("timeframe"), ctx.get("trace_id"),
            )
        except Exception:
            pass

        return ranked

    # ==========================
    # weighted（新ロジック）
    # ==========================
    w = _load_weights()
    scored_w: List[Tuple[float, Any]] = []
    base_list = list(candidates or [])
    for p in base_list:
        s = _score_weighted(p, w)
        # マーク（後段のデバッグ用）
        try:
            if isinstance(p, dict):
                p["__harmonia_score"] = s
            else:
                setattr(p, "__harmonia_score", s)
        except Exception:
            pass
        scored_w.append((s, p))

    def _tie_key(item: Tuple[float, Any]) -> Tuple[float, str, str]:
        s, p = item
        sym = ""
        trace = ""
        for n in ("symbol", "sym"):
            if isinstance(p, dict) and n in p:
                sym = str(p[n]); break
            if hasattr(p, n):
                sym = str(getattr(p, n)); break
        for n in ("trace", "id", "name"):
            if isinstance(p, dict) and n in p:
                trace = str(p[n]); break
            if hasattr(p, n):
                trace = str(getattr(p, n)); break
        return (s, sym, trace)

    ranked_w = [p for _, p in sorted(scored_w, key=_tie_key, reverse=True)]
    try:
        top3 = []
        for i, p in enumerate(ranked_w[:3], 1):
            s = getattr(p, "__harmonia_score", None)
            if s is None and isinstance(p, dict):
                s = p.get("__harmonia_score")
            top3.append(f"#{i} score={s}")
        LOGGER.info("[Harmonia] reranked(weighted) %d -> %d top=%s", len(base_list), len(ranked_w), ", ".join(top3))
    except Exception:
        pass

    return ranked_w
