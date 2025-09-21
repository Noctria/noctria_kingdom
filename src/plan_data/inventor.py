# src/plan_data/inventor.py
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


# =============================================================================
# StrategyProposal の互換インポート
# =============================================================================
def _import_strategy_proposal():
    """
    StrategyProposal (pydantic v2) のインポート互換。
    まず contracts を試し、無ければフォールバックに回す。
    """
    try:
        # 推奨（contracts 直下の正式モデル）
        from src.plan_data.contracts import StrategyProposal  # type: ignore

        return StrategyProposal
    except Exception:
        # プロジェクト差異へのフォールバック
        from src.plan_data.strategy_proposal import StrategyProposal  # type: ignore

        return StrategyProposal


# =============================================================================
# 辞書化ユーティリティ
# =============================================================================
def _to_plain_dict(obj: Any) -> Dict[str, Any]:
    """
    pydantic BaseModel / dataclass / 任意オブジェクトを防御的に dict 化。
    """
    if obj is None:
        return {}
    if isinstance(obj, dict):
        return obj
    if hasattr(obj, "model_dump") and callable(getattr(obj, "model_dump")):
        try:
            return obj.model_dump()  # type: ignore[no-any-return]
        except Exception:
            pass
    try:
        return {
            k: getattr(obj, k)
            for k in dir(obj)
            if not k.startswith("_")
            and not callable(getattr(obj, k))
            and k not in ("__class__", "Config")
        }
    except Exception:
        return {}


def _extract_ctx_feats(arg: Any) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """
    引数が bundle（context, features を持つ）でも、context dict そのものでも受けられるようにする。
    返り値: (context_dict, features_dict, trace_id)
    """
    # bundle 形式
    if isinstance(arg, dict) and ("context" in arg or "features" in arg):
        ctx = _to_plain_dict(arg.get("context"))
        feats = _to_plain_dict(arg.get("features"))
        trace_id = arg.get("trace_id") or ctx.get("trace_id") or "N/A"
        return ctx, feats, trace_id

    # context dict 直渡し
    if isinstance(arg, dict):
        ctx = _to_plain_dict(arg)
        feats = {}
        trace_id = ctx.get("trace_id") or "N/A"
        return ctx, feats, trace_id

    # オブジェクト（bundle 想定）
    ctx = _to_plain_dict(getattr(arg, "context", None))
    feats = _to_plain_dict(getattr(arg, "features", None))
    trace_id = getattr(arg, "trace_id", None) or ctx.get("trace_id") or "N/A"
    return ctx, feats, trace_id


# =============================================================================
# 超軽量ロジック（デモ）
# =============================================================================
def _side_from_features(features: Dict[str, Any]) -> str:
    """
    ごく簡単な方向推定（デモ）。正のバイアスで BUY、負で SELL。
    """
    try:
        bias = float(features.get("bias", 0.0))
    except Exception:
        bias = 0.0
    return "BUY" if bias >= 0 else "SELL"


def _side_to_intent(side: str) -> str:
    """
    StrategyProposal の intent は 'LONG' / 'SHORT' / 'FLAT'
    """
    if side.upper() == "BUY":
        return "LONG"
    if side.upper() == "SELL":
        return "SHORT"
    return "FLAT"


def _toy_signal(symbol: str, timeframe: str, seed: int) -> float:
    """
    デモ用の簡易シグナル。[-1, 1] の範囲。
    """
    random.seed(f"{symbol}:{timeframe}:{seed}")
    return random.uniform(-1.0, 1.0)


# =============================================================================
# Harmonia / Decision 側の属性に“見える”ラッパ
# =============================================================================
@dataclass
class _ProposalView:
    """
    StrategyProposal（pydantic）を包む軽量ビュー。
    - Harmonia が期待する属性（risk_adjusted / quality / risk_score / qty_raw / intent）を提供
    - その他の属性アクセスは StrategyProposal へ委譲
    """

    model: Any
    intent: str
    qty_raw: float
    quality: float
    risk_score: float
    risk_adjusted: float

    def __getattr__(self, name: str) -> Any:  # フォールバック委譲
        return getattr(self.model, name)


# =============================================================================
# メイン：提案生成
# =============================================================================
def generate_proposals(bundle_or_context: Any) -> List[Any]:
    """
    Inventor: FeatureBundle または context dict から最小セットの戦略提案を生成。

    ■ 互換性
      - 旧API: generate_proposals(bundle: FeatureBundle-like)
      - 新API: generate_proposals(context: Dict[str, Any])

    ■ StrategyProposal の最小スキーマに準拠：
      - strategy: str（モデル名）
      - intent  : 'LONG' | 'SHORT' | 'FLAT'
      - trace_id: str
      - qty_raw : float   ← 本件で付与（非FLATでは > 0）

    余計な top-level フィールド（params/score/lot など）は付けない（extra=forbid 回避）。
    ただし Harmonia が参照する属性は _ProposalView で提供する（pydanticモデルに無理に生やさない）。
    """
    StrategyProposal = _import_strategy_proposal()

    # --- 入力正規化 ---
    context_dict, features_dict, trace_id = _extract_ctx_feats(bundle_or_context)
    symbol = context_dict.get("symbol", "USDJPY")
    timeframe = context_dict.get("timeframe", "M15")

    # --- デモ用の候補を複数出す（BUY/SELL混在） ---
    proposals: List[_ProposalView] = []
    for i in range(3):
        # features.bias があればそれを優先、なければ toy_signal
        if "bias" in features_dict:
            side = _side_from_features(features_dict)
        else:
            sig = _toy_signal(symbol, timeframe, i)
            side = "BUY" if sig >= 0 else "SELL"

        intent = _side_to_intent(side)
        # intent に応じた最小数量
        qty = 0.0 if intent == "FLAT" else 1.0

        # Harmonia用の評価値（ダミー）——存在しなくても Harmonia は 0 扱いで動くが、多少の差を入れておく
        # - quality     : [0.5, 1.0)
        # - risk_score  : [0.2, 1.0)
        # - risk_adjusted: quality * (1 - 0.5 * risk_score)
        sig = _toy_signal(symbol, timeframe, i + 100)
        quality = 0.5 + 0.5 * abs(sig)
        risk_score = 0.2 + 0.8 * (1 - abs(sig))
        risk_adjusted = quality * (1.0 - 0.5 * risk_score)

        strategy_name = f"inventor/{'buy' if side == 'BUY' else 'sell'}_simple@{symbol}-{timeframe}"

        # pydantic モデルは“必要最小限”で構築（extra=forbidを尊重）
        base = StrategyProposal(
            strategy=strategy_name,
            intent=intent,
            trace_id=trace_id,
            qty_raw=qty,  # スキーマ側で許容されている想定（既存コードも付与）
        )

        # Harmonia/Decision が参照する追加属性は ビュー で提供
        proposals.append(
            _ProposalView(
                model=base,
                intent=("BUY" if intent == "LONG" else ("SELL" if intent == "SHORT" else "FLAT")),
                qty_raw=qty,
                quality=quality,
                risk_score=risk_score,
                risk_adjusted=risk_adjusted,
            )
        )

    # List[Any] として返す（呼び出し側は getattr で読む実装）
    return proposals
