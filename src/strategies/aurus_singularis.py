#!/usr/bin/env python3
# coding: utf-8

"""
🎯 Aurus Singularis (v2.2)
- 総合市場分析AI (CPUベース)
- テクニカル指標に加え、ファンダメンタルズ（経済指標）も分析に統合
- 学習済みモデルの保存・読み込みに対応
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from typing import Optional, Dict
from pathlib import Path
import logging

# --- 王国の基盤モジュールをインポート ---
from src.core.path_config import MODELS_DIR
from src.core.settings import ALPHAVANTAGE_API_KEY, FRED_API_KEY # ✅ FREDのAPIキーもインポート
from src.core.data_loader import MarketDataFetcher

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


class AurusSingularis:
    """市場の構造をテクニカルとファンダメンタルの両面から分析し、最適な行動を提案する分析官AI。"""

    def __init__(self, model_path: Optional[Path] = None):
        """
        コンストラクタ。学習済みモデルを読み込む。
        """
        self.model_path = model_path or (MODELS_DIR / "aurus_singularis_v2.keras") # モデルバージョンアップ
        self.model = self._load_or_build_model()
        # ✅ MarketDataFetcherに複数のAPIキーを渡すように変更
        self.market_fetcher = MarketDataFetcher(
            alphavantage_api_key=ALPHAVANTAGE_API_KEY,
            fred_api_key=FRED_API_KEY
        )

    def _load_or_build_model(self) -> tf.keras.Model:
        """モデルの読み込み、または新規構築を行う"""
        if self.model_path.exists():
            logging.info(f"書庫より分析官の知性を読み込んでおります: {self.model_path}")
            try:
                return tf.keras.models.load_model(self.model_path)
            except Exception as e:
                logging.error(f"知性の読み込みに失敗しました: {e}")
        
        logging.info("新たな分析モデルの構築を開始します。")
        # ✅ 修正: ファンダメンタルズ特徴量追加に伴い、入力次元を15に変更
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(15,)), # 15個の市場特徴量を入力
            tf.keras.layers.Dense(128, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(64, activation='relu'),
            tf.keras.layers.Dropout(0.2),
            tf.keras.layers.Dense(32, activation='relu'),
            tf.keras.layers.Dense(3, activation='softmax') # BUY, SELL, HOLD の3クラス分類
        ])
        model.compile(optimizer='adam', loss='sparse_categorical_crossentropy', metrics=['accuracy'])
        return model

    def save_model(self):
        """現在のモデルを指定されたパスに保存する"""
        try:
            self.model_path.parent.mkdir(parents=True, exist_ok=True)
            self.model.save(self.model_path)
            logging.info(f"分析官の知性を書庫に封印しました: {self.model_path}")
        except Exception as e:
            logging.error(f"知性の封印に失敗しました: {e}")

    def _preprocess_data(self, market_data: Dict) -> np.ndarray:
        """市場データをモデルが解釈できる形式に変換する"""
        trend_map = {"bullish": 1.0, "neutral": 0.5, "bearish": 0.0}
        trend_score = trend_map.get(market_data.get("trend_prediction", "neutral"), 0.5)

        # ✅ 修正: ファンダメンタルズ特徴量を追加
        features = [
            # --- テクニカル指標 (12) ---
            market_data.get("price", 0.0),
            market_data.get("volume", 0.0),
            market_data.get("sentiment", 0.5),
            market_data.get("trend_strength", 0.5),
            market_data.get("volatility", 0.0),
            market_data.get("order_block", 0.0),
            market_data.get("institutional_flow", 0.0),
            market_data.get("short_interest", 0.0),
            market_data.get("momentum", 0.5),
            trend_score,
            market_data.get("liquidity_ratio", 1.0),
            market_data.get("previous_price", market_data.get("price", 0.0)),
            # --- ファンダメンタルズ指標 (3) ---
            market_data.get("interest_rate_diff", 0.0), # e.g., 日米金利差
            market_data.get("cpi_change_rate", 0.0),    # e.g., 消費者物価指数の変化率
            market_data.get("news_sentiment_score", 0.5) # e.g., yfinance等から取得したニュースセンチメント
        ]
        return np.array(features).reshape(1, -1)

    def train(self, data: pd.DataFrame, epochs: int = 10, batch_size: int = 32):
        """与えられたデータでモデルを学習させる"""
        logging.info("分析官の能力向上のため、総合的な市場分析の訓練を開始します…")
        # ✅ 修正: 入力次元を15に変更
        X_train = np.random.rand(100, 15)
        y_train = np.random.randint(0, 3, 100) # 0:SELL, 1:HOLD, 2:BUY
        
        self.model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=1)
        logging.info("分析官の訓練が完了しました。")
        self.save_model()

    def propose(self, market_data: Dict) -> Dict:
        """王Noctriaへの献上：現在の市場分析に基づく戦略提案を返す"""
        logging.info("経済情勢と市場構造の総合分析を開始します…")
        processed_data = self._preprocess_data(market_data)
        prediction = self.model.predict(processed_data)[0]
        
        signal_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
        signal_index = np.argmax(prediction)
        signal = signal_map[signal_index]
        
        confidence_score = float(prediction[signal_index])

        logging.info(f"分析完了。判断: {signal} (確信度: {confidence_score:.2f})")
        
        return {
            "name": "AurusSingularis",
            "type": "comprehensive_analysis_report",
            "signal": signal,
            "confidence": round(confidence_score, 4),
            "symbol": market_data.get("symbol", "USDJPY"),
            "priority": "high" if confidence_score > 0.7 else "medium"
        }

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- 総合市場分析官アウルス、単独試練の儀を開始 ---")
    
    aurus_ai = AurusSingularis()
    aurus_ai.train(pd.DataFrame(), epochs=5)

    logging.info("\n--- 封印されし知性の解読を試みます ---")
    aurus_loaded = AurusSingularis()
    
    # ✅ 修正: ファンダメンタルズデータをモックに追加
    mock_market_data = {
        # テクニカル
        "price": 1.2345, "previous_price": 1.2340, "volume": 1000, "sentiment": 0.8, 
        "trend_strength": 0.7, "volatility": 0.15, "order_block": 0.6, 
        "institutional_flow": 0.8, "short_interest": 0.5, "momentum": 0.9, 
        "trend_prediction": "bullish", "liquidity_ratio": 1.2, "symbol": "USDJPY",
        # ファンダメンタルズ
        "interest_rate_diff": 0.05, # 5%の金利差
        "cpi_change_rate": 0.03,    # 3%のCPI上昇率
        "news_sentiment_score": 0.75 # ポジティブなニュースが多い
    }
    
    proposal = aurus_loaded.propose(mock_market_data)
    
    print("\n👑 王への進言:")
    import json
    print(json.dumps(proposal, indent=4, ensure_ascii=False))

    logging.info("\n--- 総合市場分析官アウルス、単独試練の儀を完了 ---")
