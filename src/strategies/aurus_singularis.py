#!/usr/bin/env python3
# coding: utf-8

"""
🎯 Aurus Singularis (v2.5 - decision_id伝播対応)
- 総合市場分析AI (CPUベース)
- 主要テクニカル＋ファンダメンタル統合分析
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from typing import Optional, Dict, Any
from pathlib import Path
import logging

from src.core.path_config import VERITAS_MODELS_DIR
# 使用箇所も
self.model_path = model_path or (VERITAS_MODELS_DIR / "aurus_singularis_v2.4.keras")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


class AurusSingularis:
    def __init__(self, model_path: Optional[Path] = None):
        self.model_path = model_path or (MODELS_DIR / "aurus_singularis_v2.4.keras")
        self.model = self._load_or_build_model()

    def _load_or_build_model(self) -> tf.keras.Model:
        if self.model_path.exists():
            logging.info(f"書庫より分析官の知性を読み込んでおります: {self.model_path}")
            try:
                return tf.keras.models.load_model(self.model_path)
            except Exception as e:
                logging.error(f"知性の読み込みに失敗: {e}")
        # モデル構造定義
        logging.info("新たな分析モデルを構築します。")
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(19,)),
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(3, activation='softmax')
        ])
        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        return model

    def save_model(self):
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(self.model_path)
            logging.info(f"知性を保存しました: {self.model_path}")
        except Exception as e:
            logging.error(f"モデル保存失敗: {e}")

    def _preprocess_data(self, market_data: Dict[str, Any]) -> np.ndarray:
        trend_map = {"bullish": 1.0, "neutral": 0.5, "bearish": 0.0}
        trend_score = trend_map.get(market_data.get("trend_prediction", "neutral"), 0.5)

        features = [
            market_data.get("price", 0.0),
            market_data.get("previous_price", market_data.get("price", 0.0)),
            market_data.get("volume", 0.0),
            market_data.get("volatility", 0.0),
            market_data.get("sma_5_vs_20_diff", 0.0),
            market_data.get("macd_signal_diff", 0.0),
            market_data.get("trend_strength", 0.5),
            trend_score,
            market_data.get("rsi_14", 50.0),
            market_data.get("stoch_k", 50.0),
            market_data.get("momentum", 0.5),
            market_data.get("bollinger_upper_dist", 0.0),
            market_data.get("bollinger_lower_dist", 0.0),
            market_data.get("sentiment", 0.5),
            market_data.get("order_block", 0.0),
            market_data.get("liquidity_ratio", 1.0),
            market_data.get("interest_rate_diff", 0.0),
            market_data.get("cpi_change_rate", 0.0),
            market_data.get("news_sentiment_score", 0.5)
        ]
        return np.array(features).reshape(1, -1)

    def train(self, data: Optional[pd.DataFrame] = None, epochs: int = 10, batch_size: int = 32):
        logging.info("Aurus訓練開始…")
        if data is not None and not data.empty:
            X_train = data.iloc[:, :-1].values
            y_train = data.iloc[:, -1].values
        else:
            X_train = np.random.rand(100, 19)
            y_train = np.random.randint(0, 3, 100)
        self.model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=1)
        logging.info("Aurus訓練完了。知性を保存。")
        self.save_model()

    def propose(self, market_data: Dict[str, Any], decision_id: Optional[str] = None, caller: Optional[str] = None, reason: Optional[str] = None) -> Dict[str, Any]:
        logging.info("Aurus総合市場分析を実行…")
        processed_data = self._preprocess_data(market_data)
        try:
            prediction = self.model.predict(processed_data)[0]
        except Exception as e:
            logging.error(f"推論時エラー: {e}")
            return {
                "name": "AurusSingularis",
                "type": "comprehensive_analysis_report",
                "signal": "HOLD",
                "confidence": 0.0,
                "symbol": market_data.get("symbol", "USDJPY"),
                "priority": "medium",
                "error": str(e),
                "decision_id": decision_id,
                "caller": caller,
                "reason": reason
            }
        signal_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
        signal_index = int(np.argmax(prediction))
        signal = signal_map[signal_index]
        confidence_score = float(prediction[signal_index])

        logging.info(f"Aurus分析結果: {signal} (確信度: {confidence_score:.2f})")

        return {
            "name": "AurusSingularis",
            "type": "comprehensive_analysis_report",
            "signal": signal,
            "confidence": round(confidence_score, 4),
            "symbol": market_data.get("symbol", "USDJPY"),
            "priority": "high" if confidence_score > 0.7 else "medium",
            "decision_id": decision_id,
            "caller": caller,
            "reason": reason
        }


if __name__ == "__main__":
    logging.info("--- Aurus Singularis: 単独試練開始 ---")
    aurus_ai = AurusSingularis()
    aurus_ai.train(epochs=3)

    aurus_loaded = AurusSingularis()
    mock_market_data = {
        "price": 1.2345, "previous_price": 1.2340, "volume": 1000, "volatility": 0.15,
        "sma_5_vs_20_diff": 0.001, "macd_signal_diff": 0.0005, "trend_strength": 0.7, "trend_prediction": "bullish",
        "rsi_14": 65.0, "stoch_k": 75.0, "momentum": 0.9,
        "bollinger_upper_dist": -0.002, "bollinger_lower_dist": 0.008,
        "sentiment": 0.8, "order_block": 0.6, "liquidity_ratio": 1.2, "symbol": "USDJPY",
        "interest_rate_diff": 0.05, "cpi_change_rate": 0.03, "news_sentiment_score": 0.75
    }

    proposal = aurus_loaded.propose(mock_market_data, decision_id="TEST-DECID", caller="__main__", reason="テスト用")
    print("\n👑 王への進言:")
    print(pd.Series(proposal))
    logging.info("--- Aurus Singularis: 単独試練完了 ---")
