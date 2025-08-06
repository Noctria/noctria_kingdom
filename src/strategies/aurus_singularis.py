#!/usr/bin/env python3
# coding: utf-8

"""
🎯 Aurus Singularis (v3.0 - feature拡張対応)
- Plan層の多様な特徴量(DataFrame/dict)を完全活用
- 特徴量順序(feature_order)を明示的に渡せる
- 総合市場分析AI (CPUベース／必要に応じGPU可)
"""

import numpy as np
import pandas as pd
import tensorflow as tf
from typing import Optional, Dict, Any, List
from pathlib import Path
import logging

from src.core.path_config import VERITAS_MODELS_DIR

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)

class AurusSingularis:
    def __init__(self, model_path: Optional[Path] = None, feature_order: Optional[List[str]] = None):
        self.model_path = model_path or (VERITAS_MODELS_DIR / "aurus_singularis_v3.keras")
        self.feature_order = feature_order  # Plan層から渡されたカラムリスト
        self.model = self._load_or_build_model()

    def _load_or_build_model(self) -> tf.keras.Model:
        # 入力shapeは特徴量数に依存
        input_dim = len(self.feature_order) if self.feature_order else 19  # fallback
        if self.model_path.exists():
            logger.info(f"書庫より分析官の知性を読み込んでおります: {self.model_path}")
            try:
                return tf.keras.models.load_model(self.model_path)
            except Exception as e:
                logger.error(f"知性の読み込みに失敗: {e}")
        logger.info(f"新たな分析モデルを構築します。（input_dim={input_dim}）")
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
            logger.info(f"知性を保存しました: {self.model_path}")
        except Exception as e:
            logger.error(f"モデル保存失敗: {e}")

    def _preprocess_data(self, feature_dict: Dict[str, Any]) -> np.ndarray:
        """
        feature_orderに従いinputベクトルを自動生成
        - Plan層で生成した特徴量dictをそのまま渡せる
        """
        if not self.feature_order:
            raise ValueError("feature_orderが未設定です。Plan層で特徴量順を必ず指定してください。")
        feature_vec = [feature_dict.get(key, 0.0) for key in self.feature_order]
        return np.array(feature_vec).reshape(1, -1)

    def train(self, feat_df: pd.DataFrame, label_col: str = "label", epochs: int = 10, batch_size: int = 32):
        """
        feat_df: Plan層で作成した特徴量DataFrame（特徴量カラム＋labelカラム）
        label_col: ラベル列名
        """
        logger.info("Aurus訓練開始…")
        # feature_order自動同期
        self.feature_order = [c for c in feat_df.columns if c != label_col]
        X_train = feat_df[self.feature_order].values
        y_train = feat_df[label_col].values
        self.model = self._load_or_build_model()  # input shape再構築
        self.model.fit(X_train, y_train, epochs=epochs, batch_size=batch_size, verbose=1)
        logger.info("Aurus訓練完了。知性を保存。")
        self.save_model()

    def propose(
        self,
        feature_dict: Dict[str, Any],
        decision_id: Optional[str] = None,
        caller: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Plan層で生成した特徴量（dict）をそのまま受けてAI推論
        """
        logger.info("Aurus総合市場分析を実行…")
        try:
            processed_data = self._preprocess_data(feature_dict)
            prediction = self.model.predict(processed_data)[0]
        except Exception as e:
            logger.error(f"推論時エラー: {e}")
            return {
                "name": "AurusSingularis",
                "type": "comprehensive_analysis_report",
                "signal": "HOLD",
                "confidence": 0.0,
                "priority": "medium",
                "error": str(e),
                "decision_id": decision_id,
                "caller": caller,
                "reason": reason
            }
        signal_map = {0: "SELL", 1: "HOLD", 2: "BUY"}
        signal_index = int(np.argmax(prediction))
        signal = signal_map.get(signal_index, "HOLD")
        confidence_score = float(prediction[signal_index])

        logger.info(f"Aurus分析結果: {signal} (確信度: {confidence_score:.2f})")

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


if __name__ == "__main__":
    logger.info("--- Aurus Singularis: feature拡張テスト ---")
    # 仮の特徴量DataFrame作成（label=0:SELL, 1:HOLD, 2:BUY）
    feature_cols = [f"feat{i}" for i in range(1, 25)]
    np.random.seed(42)
    train_df = pd.DataFrame(np.random.rand(100, len(feature_cols)), columns=feature_cols)
    train_df["label"] = np.random.randint(0, 3, 100)

    aurus_ai = AurusSingularis(feature_order=feature_cols)
    aurus_ai.train(train_df, label_col="label", epochs=2)

    # 推論テスト
    test_feat = {col: np.random.rand() for col in feature_cols}
    proposal = aurus_ai.propose(test_feat, decision_id="TEST-DECID", caller="__main__", reason="テスト用")
    print("\n👑 王への進言:")
    print(pd.Series(proposal))
    logger.info("--- Aurus Singularis: feature拡張テスト完了 ---")
