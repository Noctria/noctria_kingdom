# [NOCTRIA_CORE_REQUIRED]
#!/usr/bin/env python3
# coding: utf-8

"""
⚡ Levia Tempest (標準feature_order準拠)
- Plan層の標準特徴量（feature_dict, feature_order）で即時判定
- 安全設計：欠損/例外時は必ず HOLD にフォールバック
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

# --- import（相対/絶対の両対応） ---
try:
    from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER  # type: ignore
except Exception:
    from plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger("LeviaTempest")


class LeviaTempest:
    """
    即時判定の軽量ストラテジ。
    - 標準の feature_order を前提に、価格変化と基本的な健全性チェックのみで BUY/SELL/HOLD を返す。
    - 例外や閾値未満・データ不足時は必ず HOLD を返す（安全第一）。
    """

    VERSION = "1.1.0"

    def __init__(
        self,
        feature_order: Optional[List[str]] = None,
        *,
        # カラム名は標準スキーマを前提にしつつ、柔軟に上書き可能
        price_col: str = "USDJPY_Close",
        prev_price_col: str = "USDJPY_Close",  # デフォルトは同一（差分0想定）。外部で直前値を入れる運用も可
        volume_col: str = "USDJPY_Volume_MA5",
        spread_col: str = "USDJPY_Volatility_5d",  # 環境によりスプレッド相当をここにマップ
        volatility_col: str = "USDJPY_Volatility_5d",
        # 閾値/ガード
        price_threshold: float = 0.0005,
        min_liquidity: float = 120.0,
        max_spread: float = 0.018,
        max_volatility: float = 0.20,
    ):
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER
        self.price_col = price_col
        self.prev_price_col = prev_price_col
        self.volume_col = volume_col
        self.spread_col = spread_col
        self.volatility_col = volatility_col
        self.price_threshold = float(price_threshold)
        self.min_liquidity = float(min_liquidity)
        self.max_spread = float(max_spread)
        self.max_volatility = float(max_volatility)
        logger.info("LeviaTempest(標準feature_order準拠) 準備OK")

    # ---- 内部ユーティリティ ----
    @staticmethod
    def _num(d: Dict[str, Any], key: str, default: float = 0.0) -> float:
        try:
            v = d.get(key, default)
            if v is None:
                return float(default)
            return float(v)
        except Exception:
            return float(default)

    def _calculate_price_change(self, feature_dict: Dict[str, Any]) -> float:
        price = self._num(feature_dict, self.price_col, 0.0)
        prev_price = self._num(feature_dict, self.prev_price_col, price)
        return price - prev_price

    def _create_proposal(
        self,
        signal: str,
        score: float,
        feature_dict: Dict[str, Any],
        decision_id: Optional[str],
        caller: Optional[str],
        reason: Optional[str],
        *,
        error: Optional[str] = None,
    ) -> Dict[str, Any]:
        trace_id = (
            feature_dict.get("trace_id")
            or feature_dict.get("TRACE_ID")
            or feature_dict.get("traceId")
        )
        return {
            "name": "LeviaTempest",
            "version": self.VERSION,
            "type": "scalping_signal",
            "signal": signal,
            "confidence": round(float(score), 4),
            "symbol": feature_dict.get("symbol", "USDJPY"),
            "priority": "very_high" if signal in ("BUY", "SELL") else "normal",
            "decision_id": decision_id,
            "caller": caller,
            "reason": reason,
            "trace_id": trace_id,
            "meta": {
                "price_col": self.price_col,
                "prev_price_col": self.prev_price_col,
                "volume_col": self.volume_col,
                "spread_col": self.spread_col,
                "volatility_col": self.volatility_col,
                "thresholds": {
                    "price_threshold": self.price_threshold,
                    "min_liquidity": self.min_liquidity,
                    "max_spread": self.max_spread,
                    "max_volatility": self.max_volatility,
                },
                **({"error": error} if error else {}),
            },
        }

    # ---- メインI/F ----
    def propose(
        self,
        feature_dict: Dict[str, Any],
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria",
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        即時提案を返す。失敗やデータ不足時は必ず HOLD を返す。
        """
        try:
            liquidity = self._num(feature_dict, self.volume_col, 0.0)
            spread = self._num(feature_dict, self.spread_col, 0.0)
            volatility = self._num(feature_dict, self.volatility_col, 0.0)
            price_change = self._calculate_price_change(feature_dict)

            # --- 健全性ガード（順序も重要：早期HOLD） ---
            if liquidity < self.min_liquidity:
                logger.warning(f"流動性低下: {liquidity} < {self.min_liquidity}。HOLD")
                return self._create_proposal("HOLD", 0.0, feature_dict, decision_id, caller, reason)
            if spread > self.max_spread:
                logger.warning(f"スプレッド過大: {spread} > {self.max_spread}。HOLD")
                return self._create_proposal("HOLD", 0.0, feature_dict, decision_id, caller, reason)
            if volatility > self.max_volatility:
                logger.warning(f"ボラ過大: {volatility} > {self.max_volatility}。HOLD")
                return self._create_proposal("HOLD", 0.0, feature_dict, decision_id, caller, reason)

            # --- シグナル決定 ---
            threshold = self.price_threshold + 1e-9
            score = min(abs(price_change) / threshold, 1.0)

            if price_change > self.price_threshold:
                signal = "BUY"
            elif price_change < -self.price_threshold:
                signal = "SELL"
            else:
                signal = "HOLD"
                score = 0.0

            return self._create_proposal(signal, score, feature_dict, decision_id, caller, reason)

        except Exception as e:
            # 予期せぬ例外は安全に HOLD へ
            logger.error(f"LeviaTempest propose 例外: {e}", exc_info=True)
            return self._create_proposal(
                "HOLD", 0.0, feature_dict, decision_id, caller, reason, error=str(e)
            )
