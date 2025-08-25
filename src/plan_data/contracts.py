# src/plan_data/contracts.py
from __future__ import annotations

from typing import Literal, Optional, List, Dict, Any
from datetime import datetime, timezone

# --- Pydantic v1/v2 互換レイヤ -------------------------------------------------
try:
    # Pydantic v2+
    from pydantic import (
        BaseModel,
        Field,
        ConfigDict,
        field_validator,
        model_validator,
        confloat,
    )  # type: ignore
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


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# --- BaseModel 設定（extra 禁止 + 共通I/F） -----------------------------------
class _StrictModel(BaseModel):
    if _PYDANTIC_V2:
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

    # 便宜: 明示validate（pydanticはinitで検証するが、呼び出し側が明示したい時用）
    def validate_self(self) -> "._StrictModel":
        return self


# ==============================
# v1 スキーマ（明示バージョン付き）
# ==============================

class FeatureContextV1(_StrictModel):
    """特徴量のメタ情報（Plan 層での生成文脈）。"""
    symbol: str
    timeframe: str  # e.g., "1m", "5m", "1h"
    tz: str = "UTC"
    as_of: datetime = Field(default_factory=_utcnow)
    data_lag_min: int = 0
    missing_ratio: confloat(ge=0, le=1) = 0.0  # type: ignore[type-arg]
    meta: Dict[str, Any] = Field(default_factory=dict)

    # 文字列必須チェック
    if _PYDANTIC_V2:
        @field_validator("symbol", "timeframe")
        @classmethod
        def _non_empty(cls, v: str) -> str:
            if not v or not str(v).strip():
                raise ValueError("must be non-empty string")
            return v
    else:
        @validator("symbol", "timeframe")  # type: ignore[misc]
        def _non_empty_v1(cls, v):  # type: ignore[no-untyped-def]
            if not v or not str(v).strip():
                raise ValueError("must be non-empty string")
            return v


class FeatureBundleV1(_StrictModel):
    """Plan層→AI へ渡す共通入力。"""
    schema_version: Literal["1.0"] = "1.0"
    features: Dict[str, Any]              # 必要であれば df のパスや shape などを含める
    context: FeatureContextV1
    trace_id: str
    ts: datetime = Field(default_factory=_utcnow)

    # trace_id の非空
    if _PYDANTIC_V2:
        @field_validator("trace_id")
        @classmethod
        def _trace_non_empty(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("trace_id must be non-empty")
            return v
    else:
        @validator("trace_id")  # type: ignore[misc]
        def _trace_non_empty_v1(cls, v):  # type: ignore[no-untyped-def]
            if not v or not v.strip():
                raise ValueError("trace_id must be non-empty")
            return v


class StrategyProposalV1(_StrictModel):
    """
    AI からの提案の標準形。
    返せない/見送り時は intent=FLAT で返す想定。
    """
    schema_version: Literal["1.0"] = "1.0"
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
    ts: datetime = Field(default_factory=_utcnow)

    # strategy / trace_id 非空
    if _PYDANTIC_V2:
        @field_validator("strategy", "trace_id")
        @classmethod
        def _non_empty(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("must be non-empty string")
            return v
    else:
        @validator("strategy", "trace_id")  # type: ignore[misc]
        def _non_empty_v1(cls, v):  # type: ignore[no-untyped-def]
            if not v or not v.strip():
                raise ValueError("must be non-empty string")
            return v

    # qty の条件付き検証
    if _PYDANTIC_V2:
        @model_validator(mode="after")  # type: ignore[misc]
        def _validate_qty_raw(cls, values: "StrategyProposalV1") -> "StrategyProposalV1":
            if values.intent in ("LONG", "SHORT") and (values.qty_raw is None or values.qty_raw <= 0):
                raise ValueError("qty_raw must be > 0 for non-FLAT intents")
            if values.intent == "FLAT" and values.qty_raw < 0:
                raise ValueError("qty_raw must be >= 0 for FLAT intent")
            return values
    else:
        @validator("qty_raw")  # type: ignore[misc]
        def _validate_qty_raw_v1(cls, v, values):  # type: ignore[no-untyped-def]
            intent = values.get("intent")
            if intent in ("LONG", "SHORT") and (v is None or v <= 0):
                raise ValueError("qty_raw must be > 0 for non-FLAT intents")
            if intent == "FLAT" and v < 0:
                raise ValueError("qty_raw must be >= 0 for FLAT intent")
            return v


class OrderRequestV1(_StrictModel):
    """
    DecisionEngine → Do 層に引き渡す最小単位（注文リクエスト）。
    - idempotency_key は Do 層（Outbox）で付与想定のため任意。
    - sources はどの提案が寄与したかのトレースに使う（任意）。
    """
    schema_version: Literal["1.1"] = "1.1"   # Do層のv1.1（idempotency_key追加）前提
    symbol: str
    intent: Intent
    qty: float
    order_type: OrderType = "MARKET"
    limit_price: Optional[float] = None
    sl_tp: Optional[Dict[str, float]] = None  # 例: {"sl": 0.3, "tp": 0.5}
    sources: List[StrategyProposalV1] = Field(default_factory=list)
    trace_id: str
    idempotency_key: Optional[str] = None
    ts: datetime = Field(default_factory=_utcnow)

    # 非空チェック & qty>0（FLATを許容するが qty は 0 以上）
    if _PYDANTIC_V2:
        @field_validator("symbol", "trace_id")
        @classmethod
        def _non_empty(cls, v: str) -> str:
            if not v or not v.strip():
                raise ValueError("must be non-empty string")
            return v
    else:
        @validator("symbol", "trace_id")  # type: ignore[misc]
        def _non_empty_v1(cls, v):  # type: ignore[no-untyped-def]
            if not v or not v.strip():
                raise ValueError("must be non-empty string")
            return v

    if _PYDANTIC_V2:
        @model_validator(mode="after")  # type: ignore[misc]
        def _validate_qty(cls, values: "OrderRequestV1") -> "OrderRequestV1":
            if values.intent in ("LONG", "SHORT") and (values.qty is None or values.qty <= 0):
                raise ValueError("qty must be > 0 for non-FLAT intents")
            if values.intent == "FLAT" and values.qty < 0:
                raise ValueError("qty must be >= 0 for FLAT intent")
            return values
    else:
        @validator("qty")  # type: ignore[misc]
        def _validate_qty_v1(cls, v, values):  # type: ignore[no-untyped-def]
            intent = values.get("intent")
            if intent in ("LONG", "SHORT") and (v is None or v <= 0):
                raise ValueError("qty must be > 0 for non-FLAT intents")
            if intent == "FLAT" and v < 0:
                raise ValueError("qty must be >= 0 for FLAT intent")
            return v

    # 便宜: side 変換（BUY/SELL/FLAT）
    @property
    def side(self) -> str:
        it = (self.intent or "FLAT").upper()
        if it == "LONG":
            return "BUY"
        if it == "SHORT":
            return "SELL"
        return "FLAT"


# ==============================
# 旧→新 薄アダプタ（辞書ベース）
# ==============================

def adapt_proposal_dict_v1(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    旧キー → 新キーのゆるい変換（存在すれば上書き）
      - qty / quantity       -> qty_raw
      - confidence_score     -> confidence
      - risk                 -> risk_score
      - reason(s) 正規化     -> reasons(list)
    """
    out = dict(d)
    if "qty_raw" not in out:
        if "qty" in out:
            out["qty_raw"] = out.get("qty")
        elif "quantity" in out:
            out["qty_raw"] = out.get("quantity")
    if "confidence" not in out and "confidence_score" in out:
        out["confidence"] = out.get("confidence_score")
    if "risk_score" not in out and "risk" in out:
        out["risk_score"] = out.get("risk")
    if "reasons" not in out and "reason" in out:
        r = out.get("reason")
        out["reasons"] = [r] if isinstance(r, str) else (r or [])
    return out


def adapt_order_dict_v1(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    旧キー → 新キーのゆるい変換（存在すれば上書き）
      - asset -> symbol
      - side(BUY/SELL/FLAT) -> intent(LONG/SHORT/FLAT)
    """
    out = dict(d)
    if "symbol" not in out and "asset" in out:
        out["symbol"] = out.get("asset")
    if "intent" not in out and "side" in out:
        side = str(out.get("side", "")).upper()
        if side == "BUY":
            out["intent"] = "LONG"
        elif side == "SELL":
            out["intent"] = "SHORT"
        else:
            out["intent"] = "FLAT"
    return out


# ==============================
# 後方互換のためのエイリアス
# ==============================

# 既存コードが FeatureContext / FeatureBundle / StrategyProposal / OrderRequest を
# 直接 import していても、そのまま動くように v1 を割り当てる
FeatureContext = FeatureContextV1
FeatureBundle = FeatureBundleV1
StrategyProposal = StrategyProposalV1
OrderRequest = OrderRequestV1


__all__ = [
    # enums
    "Intent",
    "OrderType",
    # v1 明示名
    "FeatureContextV1",
    "FeatureBundleV1",
    "StrategyProposalV1",
    "OrderRequestV1",
    # 旧名エイリアス
    "FeatureContext",
    "FeatureBundle",
    "StrategyProposal",
    "OrderRequest",
    # 辞書アダプタ
    "adapt_proposal_dict_v1",
    "adapt_order_dict_v1",
]
