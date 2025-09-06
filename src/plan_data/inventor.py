# src/plan_data/inventor.py
from __future__ import annotations

from typing import Any, Dict, List


def _import_strategy_proposal():
    """
    StrategyProposal (pydantic v2) のインポート互換。
    配置差異に備えて contracts 優先・fallback を持つ。
    """
    try:
        from src.plan_data.contracts import StrategyProposal  # 推奨: alias of StrategyProposalV1
        return StrategyProposal
    except Exception:
        # プロジェクト差異のフォールバック（必要に応じて調整）
        from src.plan_data.strategy_proposal import StrategyProposal  # type: ignore
        return StrategyProposal


def _side_from_features(features: Dict[str, Any]) -> str:
    """
    超簡易な方向推定。必要なら本実装に差し替え。
    正のバイアスなら BUY、負なら SELL、ゼロは HOLD 相当で BUY に丸める。
    """
    bias = float(features.get("bias", 0.0))
    return "BUY" if bias >= 0 else "SELL"


def generate_proposals(bundle: Any) -> List[Dict[str, Any] | Any]:
    """
    Inventor: FeatureBundle から最小セットの戦略提案を生成。

    StrategyProposalV1 の必須は:
      - strategy: { name: str, params: dict }（想定）
      - intent: str（例: "OPEN"）
      - trace_id: str

    トップレベルへ name/lot/score/symbol を置くと extra=forbid に当たるため、
    それらは strategy.params などの下位へ格納する。
    """
    StrategyProposal = _import_strategy_proposal()

    # FeatureBundle は pydantic モデル想定（model_dump を備えることが多い）
    # ただし属性アクセスでも動くよう防御的に扱う
    ctx = getattr(bundle, "context", {}) or {}
    feats = getattr(bundle, "features", {}) or {}
    trace_id = getattr(bundle, "trace_id", None) or "N/A"

    symbol = ctx.get("symbol", "USDJPY")
    timeframe = ctx.get("timeframe", "M15")
    side = _side_from_features(feats)

    # ---- 最小提案（例）----
    # “inventor/buy_simple or sell_simple” のような名前をつけ、
    # intent は OPEN、lot/score/symbol/timeframe などは strategy.params へ格納
    name = f"inventor/{'buy' if side == 'BUY' else 'sell'}_simple"

    params: Dict[str, Any] = {
        "lot": 0.5,
        "side": side,
        "symbol": symbol,
        "timeframe": timeframe,
        "generator": "inventor_v1",
        # スコアなどの補助値もトップではなく params へ
        "score": float(feats.get("missing_ratio", 0.0)) * 0.5 + 0.5,  # 適当なダミー例
    }

    # StrategyProposalV1 に適合する形でモデル生成
    proposal = StrategyProposal(
        strategy={"name": name, "params": params},
        intent="OPEN",
        trace_id=trace_id,
    )

    # 返却は pydantic モデルのままでも良いが、XCom 軽量化を考えるなら dict 化も可
    # ここでは呼び出し側(run_inventor_and_decide)に任せる
    return [proposal]
