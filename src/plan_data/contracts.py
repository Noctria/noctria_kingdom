from __future__ import annotations
from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field, confloat, validator
from datetime import datetime, timezone

Intent = Literal["LONG", "SHORT", "FLAT"]
OrderType = Literal["MARKET", "LIMIT"]

class FeatureContext(BaseModel):
    symbol: str
    timeframe: str  # e.g., "1m", "5m", "1h"
    tz: str = "UTC"
    as_of: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    data_lag_min: int = 0
    missing_ratio: confloat(ge=0, le=1) = 0.0
    meta: Dict[str, Any] = Field(default_factory=dict)

class FeatureBundle(BaseModel):
    """Plan層→AIへ渡す共通入力。dfは任意（None可）。"""
    features: Dict[str, Any]  # 軽量にdict化（必要ならdfのパスやshapeだけ）
    context: FeatureContext
    trace_id: str

class StrategyProposal(BaseModel):
    """AIからの提案を統一。返せない場合は intent=FLAT で返す。"""
    strategy: str
    intent: Intent
    qty_raw: float = 0.0
    price_hint: Optional[float] = None
    confidence: confloat(ge=0, le=1) = 0.0
    risk_score: confloat(ge=0, le=1) = 0.5  # 低いほど安全
    reasons: List[str] = Field(default_factory=list)
    latency_ms: int = 0
    trace_id: str

    @validator("qty_raw")
    def non_negative_qty(cls, v, values):
        if values.get("intent") in ("LONG", "SHORT") and v <= 0:
            raise ValueError("qty_raw must be > 0 for non-FLAT intents")
        return v

class OrderRequest(BaseModel):
    """DecisionEngineの出力。Do層に引き渡す最小単位。"""
    symbol: str
    intent: Intent
    qty: float
    order_type: OrderType = "MARKET"
    limit_price: Optional[float] = None
    sl_tp: Optional[Dict[str, float]] = None
    sources: List[StrategyProposal] = Field(default_factory=list)
    trace_id: str
    # idempotency_key はDo層で付与（ここではオプション）
    idempotency_key: Optional[str] = None
