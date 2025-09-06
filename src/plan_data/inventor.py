# src/plan_data/inventor.py
from __future__ import annotations

from typing import Any, Dict, List


def _import_strategy_proposal():
    """
    StrategyProposal (pydantic v2) のインポート互換。
    まず contracts を試し、無ければフォールバックに回す。
    """
    try:
        from src.plan_data.contracts import StrategyProposal  # = StrategyProposalV1（推奨）
        return StrategyProposal
    except Exception:
        # 必要に応じてプロジェクト差異のフォールバック
        from src.plan_data.strategy_proposal import StrategyProposal  # type: ignore
        return StrategyProposal


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
    StrategyProposalV1 の intent は 'LONG' / 'SHORT' / 'FLAT'
    """
    if side.upper() == "BUY":
        return "LONG"
    if side.upper() == "SELL":
        return "SHORT"
    return "FLAT"


def generate_proposals(bundle: Any) -> List[Any]:
    """
    Inventor: FeatureBundle から最小セットの戦略提案を生成。

    ★ StrategyProposalV1 の最小スキーマに厳密準拠：
        - strategy: str（モデル名）
        - intent  : 'LONG' | 'SHORT' | 'FLAT'
        - trace_id: str

    余計な top-level フィールド（params/score/lot など）は付けない（extra=forbid 回避）。
    """
    StrategyProposal = _import_strategy_proposal()

    trace_id = getattr(bundle, "trace_id", None) or "N/A"
    context_dict: Dict[str, Any] = _to_plain_dict(getattr(bundle, "context", None))
    features_dict: Dict[str, Any] = _to_plain_dict(getattr(bundle, "features", None))

    symbol = context_dict.get("symbol", "USDJPY")
    timeframe = context_dict.get("timeframe", "M15")

    side = _side_from_features(features_dict)
    intent = _side_to_intent(side)

    # strategy は **str** 必須（dictはNG）
    strategy_name = f"inventor/{'buy' if side == 'BUY' else 'sell'}_simple@{symbol}-{timeframe}"

    # 最小スキーマで提案を1件返す
    proposal = StrategyProposal(
        strategy=strategy_name,
        intent=intent,
        trace_id=trace_id,
    )
    return [proposal]
