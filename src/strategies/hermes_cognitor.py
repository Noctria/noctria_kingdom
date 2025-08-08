#!/usr/bin/env python3
# coding: utf-8

"""
🦉 Hermes Cognitor (feature_order準拠)
- Plan層の標準dict/feature_order/labelsを自然言語説明
- decision_id/callerも返却
"""

import logging
from typing import Optional, Dict, Any, List

from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class HermesCognitorStrategy:
    def __init__(
        self,
        model: str = "gpt-4o",
        feature_order: Optional[List[str]] = None
    ):
        self.model = model
        self.feature_order = feature_order or STANDARD_FEATURE_ORDER

    def _build_prompt(
        self,
        features: Dict[str, Any],
        labels: List[str],
        feature_order: Optional[List[str]] = None,
        reason: Optional[str] = None
    ) -> str:
        prompt = "以下の標準特徴量・要因ラベルをもとに市場戦略の説明文を生成してください。\n"
        if reason:
            prompt += f"【理由】{reason}\n"
        prompt += f"【特徴量順】{feature_order or self.feature_order}\n"
        prompt += f"【特徴量値】{features}\n"
        prompt += f"【要因ラベル】{labels}\n"
        prompt += "説明:"
        return prompt

    def summarize_strategy(
        self,
        features: Dict[str, Any],
        labels: List[str],
        feature_order: Optional[List[str]] = None,
        reason: Optional[str] = None
    ) -> str:
        prompt = self._build_prompt(features, labels, feature_order, reason)
        logging.info("HermesCognitor: プロンプト組み立て完了")
        # ※本番ではOpenAI API等で要約を生成（省略）
        return "[ダミー要約] " + (labels[0] if labels else "特徴量・要因から戦略説明")

    def propose(
        self,
        input_data: Dict[str, Any],
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria"
    ) -> Dict[str, Any]:
        features = input_data.get("features", {})
        labels = input_data.get("labels", [])
        feature_order = input_data.get("feature_order", self.feature_order)
        reason = input_data.get("reason", "")
        explanation = self.summarize_strategy(features, labels, feature_order, reason)
        return {
            "name": "HermesCognitor",
            "type": "llm_explanation_report",
            "explanation": explanation,
            "feature_order": feature_order,
            "source_features": features,
            "labels": labels,
            "reason": reason,
            "llm_model": self.model,
            "decision_id": decision_id,
            "caller": caller
        }

# テスト例省略
