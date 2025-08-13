# src/plan_data/contracts.py
from __future__ import annotations

from typing import Literal, Optional, List, Dict, Any
from datetime import datetime, timezone

# --- Pydantic v1/v2 互換レイヤ -------------------------------------------------
try:
    # Pydantic v2+
    from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator, confloat  # type: ignore
    _PYDANTIC_V2 = True
except Exception:  # pragma: no cover
    # Pydantic v1 系
    from pydantic import BaseModel, Field, validator, confloat  # type: ignore
    ConfigDict = None  # sentinel
    field_validator = None  # sentinel
    model_validator = None  # sentinel
    _PYDANTIC_V2 = False


# --- 型定義 --------------------------------------------------------------------
Intent = Literal["LONG", "SHORT", "FLAT"]
OrderType = Literal["MARKET", "LIMIT"]


# --- BaseModel 設定（extra 禁止） ---------------------------------------------
class _StrictModel(BaseModel):
    if _PYDANTIC_V2:
        # v2: ConfigDict
        model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)
    else:  # v1
        class Config:
            extra = "forbid"
            arbitrary_types_allowed = True

    # v1/v2 両対応の dict 取得（既存コード互換）
    def to_dict(self) -> Dict[str, Any]:
        if hasattr(self, "model_dump"):  # v2
            return getattr(self, "model_dump")()  # type: ignore[attr-defined]
        return self.dict()  # v1

    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)


# --- モデル定義 ----------------------------------------------------------------
class FeatureContext(_StrictModel):
    """特徴量のメタ情報（Plan 層での生成文脈）。"""
    symbol: str
    timeframe: str  # e.g., "1m", "5m", "1h"
    tz: str = "UTC"
    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_lag_min: int = 0
    missing_ratio: confloat(ge=0, le=1) = 0.0  # type: ignore[type-arg]
    meta: Dict[str, Any] = Field(default_factory=dict)


class FeatureBundle(_StrictModel):
    """Plan層→AI へ渡す共通入力。df は重いので dict のみに簡素化。"""
    features: Dict[str, Any]  # 必要であれば df のパスや shape などを含める
    context: FeatureContext
    trace_id: str


class StrategyProposal(_StrictModel):
    """
    AI からの提案の標準形。
    返せない/見送り時は intent=FLAT で返す想定。
    """
    strategy: str
    intent: Intent
    qty_raw: float = 0.0
    price_hint: Optional[float] = None
    confidence: confloat(ge=0, le=1) = 0.0  # type: ignore[type-arg]
    # リスクスコアは低いほど安全（0=最安全, 1=最危険）
    risk_score: confloat(ge=0, le=1) = 0.5  # type: ignore[type-arg]
    reasons: List[str] = Field(default_factory=list)
    latency_ms: int = 0
    trace_id: str

    # --- qty_raw の条件付きバリデーション（意図が FLAT 以外なら qty_raw > 0） ---
    if _PYDANTIC_V2:
        @model_validator(mode="after")  # type: ignore[misc]
        def _validate_qty_raw(cls, values: "StrategyProposal") -> "StrategyProposal":
            if values.intent in ("LONG", "SHORT") and (values.qty_raw is None or values.qty_raw <= 0):
                raise ValueError("qty_raw must be > 0 for non-FLAT intents")
            return values
    else:
        @validator("qty_raw")  # type: ignore[misc]
        def _validate_qty_raw_v1(cls, v, values):  # type: ignore[no-untyped-def]
            intent = values.get("intent")
            if intent in ("LONG", "SHORT") and (v is None or v <= 0):
                raise ValueError("qty_raw must be > 0 for non-FLAT intents")
            return v


class OrderRequest(_StrictModel):
    """
    DecisionEngine → Do 層に引き渡す最小単位（注文リクエスト）。
    - idempotency_key は Do 層（Outbox）で付与想定のため任意。
    - sources はどの提案が寄与したかのトレースに使う（任意）。
    """
    symbol: str
    intent: Intent
    qty: float
    order_type: OrderType = "MARKET"
    limit_price: Optional[float] = None
    sl_tp: Optional[Dict[str, float]] = None  # 例: {"sl": 0.3, "tp": 0.5}
    sources: List[StrategyProposal] = Field(default_factory=list)
    trace_id: str
    idempotency_key: Optional[str] = None

    # 便宜: side 変換（BUY/SELL/FLAT）
    @property
    def side(self) -> str:
        it = (self.intent or "FLAT").upper()
        if it == "LONG":
            return "BUY"
        if it == "SHORT":
            return "SELL"
        return "FLAT"


__all__ = [
    "Intent",
    "OrderType",
    "FeatureContext",
    "FeatureBundle",
    "StrategyProposal",
    "OrderRequest",
]
