#!/usr/bin/env python3
# coding: utf-8

"""
🎯 Aurus Singularis (標準feature_order準拠)
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from src.core.path_config import VERITAS_MODELS_DIR
from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

class AurusSingularis:
    def __init__(self, model_path: Optional[Path] = None, feature_order: Optional[List[str]] = None):
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER
        self.model_path = model_path or (VERITAS_MODELS_DIR / "aurus_singularis_v3.keras")
        self.model = self._load_or_build_model(input_dim=len(self.feature_order))

    def _load_or_build_model(self, input_dim: int) -> tf.keras.Model:
        if self.model_path.exists():
            logger.info(f"書庫より知性を読み込んでおります: {self.model_path}")
            try:
                return tf.keras.models.load_model(self.model_path)
            except Exception as e:
                logger.error(f"知性の読み込み失敗: {e}")
        logger.info(f"新モデル構築(input_dim={input_dim})")
        model = tf.keras.Sequential([
            tf.keras.layers.Input(shape=(input_dim,)),
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
            logger.info(f"知性保存: {self.model_path}")
        except Exception as e:
            logger.error(f"モデル保存失敗: {e}")

    def _preprocess_data(self, feature_dict: Dict[str, Any]) -> np.ndarray:
        feature_vec = [feature_dict.get(key, 0.0) for key in self.feature_order]
        return np.array(feature_vec).reshape(1, -1)

    def train(self, feat_df: pd.DataFrame, label_col: str = "label", epochs: int = 10, batch_size: int = 32):
        self.feature_order = [c for c in feat_df.columns if c != label_col]
        X_train = feat_df[self.feature_order].values
        y_train = feat_df[label_col].values
        self.model = self._load_or_build_model(input_dim=len(self.feature_order))
        self.model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=1)
        self.save_model()

    def propose(
        self,
        feature_dict: Dict[str, Any],
        decision_id: Optional[str] = None,
        caller: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            processed_data = self._preprocess_data(feature_dict)
            prediction = self.model.predict(processed_data)[0]
        except Exception as e:
            logger.error(f"推論時エラー: {e}")
            return {"name": "AurusSingularis", "type": "comprehensive_analysis_report", "signal": "HOLD", "confidence": 0.0, "priority": "medium", "error": str(e), "decision_id": decision_id, "caller": caller, "reason": reason}
        signal_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
        signal_index = int(np.argmax(prediction))
        signal = signal_map.get(signal_index, "HOLD")
        confidence_score = float(prediction[signal_index])
        return {
            "name": "AurusSingularis",
            "type": "comprehensive_analysis_report",
            "signal": signal,
            "confidence": round(confidence_score, 4),
            "priority": "high" if confidence_score > 0.7 else "medium",
            "decision_id": decision_id,
            "caller": caller,
            "reason": reason
        }
