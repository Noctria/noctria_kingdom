# src/plan_data/inventor.py
from __future__ import annotations

from typing import Any, Dict, List


def _import_strategy_proposal():
    """
    StrategyProposal (pydantic v2) のインポート互換。
    まず contracts を試し、無ければフォールバックに回す。
    """
    try:
        from src.plan_data.contracts import StrategyProposal  # alias of StrategyProposalV1 (推奨)
        return StrategyProposal
    except Exception:
        # プロジェクト差異のフォールバック（必要に応じて調整）
        from src.plan_data.strategy_proposal import StrategyProposal  # type: ignore
        return StrategyProposal


def _to_plain_dict(obj: Any) -> Dict[str, Any]:
    """
    pydantic v2 BaseModel / dataclass / 任意オブジェクトを防御的に dict 化。
    - model_dump() があればそれを使う
    - __dict__ があれば shallow 取得
    - dict ならそのまま
    - それ以外は空 dict
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
    # 属性列挙（必要最低限）
    try:
        return {k: getattr(obj, k) for k in dir(obj)
                if not k.startswith("_")
                and not callable(getattr(obj, k))
                and k not in ("__class__", "Config")}
    except Exception:
        return {}


def _side_from_features(features: Dict[str, Any]) -> str:
    """
    ごく簡単な方向推定（デモ用）。
    正のバイアスで BUY、負で SELL、ゼロは BUY に丸める。
    """
    try:
        bias = float(features.get("bias", 0.0))
    except Exception:
        bias = 0.0
    return "BUY" if bias >= 0 else "SELL"


def generate_proposals(bundle: Any) -> List[Dict[str, Any] | Any]:
    """
    Inventor: FeatureBundle から最小セットの戦略提案を生成。

    StrategyProposalV1 の必須フィールド:
      - strategy: { name: str, params: dict }
      - intent: str（例: "OPEN"）
      - trace_id: str

    トップレベルに name/lot/score/symbol/timeframe 等を置くと extra=forbid で弾かれるため、
    それらは strategy.params に格納する。
    """
    StrategyProposal = _import_strategy_proposal()

    # FeatureBundle は pydantic モデル想定だが、素直な dict とは限らないため防御的に扱う
    trace_id = getattr(bundle, "trace_id", None) or "N/A"

    # context / features を安全に dict 化（pydantic BaseModel を考慮）
    context_dict: Dict[str, Any] = _to_plain_dict(getattr(bundle, "context", None))
    features_dict: Dict[str, Any] = _to_plain_dict(getattr(bundle, "features", None))

    symbol = context_dict.get("symbol", "USDJPY")
    timeframe = context_dict.get("timeframe", "M15")
    side = _side_from_features(features_dict)

    # ---- シンプルな1件提案（デモ） ----
    name = f"inventor/{'buy' if side == 'BUY' else 'sell'}_simple"

    # params に各種パラメータを集約（トップに置かない！）
    params: Dict[str, Any] = {
        "lot": 0.5,
        "side": side,
        "symbol": symbol,
        "timeframe": timeframe,
        "generator": "inventor_v1",
    }
    # 例：quality用の簡易スコア（ダミー）
    try:
        mr = float(features_dict.get("missing_ratio", 0.0))
    except Exception:
        mr = 0.0
    params["score"] = 0.5 + 0.5 * (1.0 - max(0.0, min(1.0, mr)))  # 欠損が少ないほど高スコア

    proposal = StrategyProposal(
        strategy={"name": name, "params": params},
        intent="OPEN",
        trace_id=trace_id,
    )

    # 呼び出し側（run_inventor_and_decide）で要約して XCom 返却する前提
    return [proposal]
