#!/usr/bin/env python3
# coding: utf-8

"""
🦉 Hermes Cognitor (理想形・統治AI連携専用)
- LLMベースの説明・要約AI
- 必ずNoctria王経由でのみ呼ばれる運用前提
- 各説明生成結果に「decision_id」「呼び出し元（王/統治ID）」を必ず返す
"""

import logging
from typing import Optional, Dict, Any, List

# --- 王国の基盤モジュールをインポート ---
from src.core.path_config import ORACLE_FORECAST_JSON

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')

class HermesCognitorStrategy:
    """
    Hermes Cognitor - LLM戦略クラス
    - 分析AIやML評価の出力を人間向けに自然言語説明/要約
    - 必ずNoctria王経由でのみ呼び出される
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model

    def _build_prompt(self, features: Dict[str, Any], labels: List[str], reason: Optional[str] = None) -> str:
        prompt = "以下の特徴量と要因ラベルをもとに、市場戦略の根拠を人間向けに自然言語で要約してください。\n"
        if reason:
            prompt += f"【発令理由】{reason}\n"
        prompt += f"【特徴量】{features}\n"
        prompt += f"【要因ラベル】{labels}\n"
        prompt += "説明:"
        return prompt

    def summarize_strategy(self, features: Dict[str, Any], labels: List[str], reason: Optional[str] = None) -> str:
        prompt = self._build_prompt(features, labels, reason)
        logging.info("HermesCognitor: プロンプト組み立て完了")
        # ▼ 本番運用ではLLM APIをここで実行
        # if self.api_key:
        #     import openai
        #     openai.api_key = self.api_key
        #     response = openai.chat.completions.create(
        #         model=self.model,
        #         messages=[{"role": "user", "content": prompt}],
        #     )
        #     return response.choices[0].message.content
        # else:
        #     return "[LLM API未接続] " + prompt
        # -----
        return "[ダミー要約] " + (labels[0] if labels else "特徴量・要因から戦略の説明を生成")

    def summarize_news(self, news_list: List[str], context: Optional[str] = None) -> str:
        prompt = f"ニュース一覧: {news_list}\nこの市場に与える影響を要約してください。"
        logging.info("HermesCognitor: ニュース要約プロンプト組み立て完了")
        # LLM API実装部（省略）
        return "[ダミーニュース要約] " + (news_list[0][:40] + "..." if news_list else "ニュースがありません。")

    def propose(
        self,
        input_data: Dict[str, Any],
        decision_id: Optional[str] = None,
        caller: Optional[str] = "king_noctria"
    ) -> Dict[str, Any]:
        """
        王からの呼び出しを前提とした、説明/要約レポート生成I/F
        - 必ずdecision_idと呼び出し元を記録・返却
        """
        logging.info("HermesCognitor: propose呼び出し")
        features = input_data.get("features", {})
        labels = input_data.get("labels", [])
        reason = input_data.get("reason", "")
        explanation = self.summarize_strategy(features, labels, reason)
        return {
            "name": "HermesCognitor",
            "type": "llm_explanation_report",
            "explanation": explanation,
            "source_features": features,
            "labels": labels,
            "reason": reason,
            "llm_model": self.model,
            "ai_source": "hermes",
            "decision_id": decision_id,
            "caller": caller
        }

# ========================================
# ✅ テストブロック（王Noctria経由テスト例）
# ========================================
if __name__ == "__main__":
    logging.info("--- Hermes Cognitor: 理想形テスト ---")
    hermes_ai = HermesCognitorStrategy()
    features = {"win_rate": 78.9, "risk": "low", "fomc_today": True}
    labels = ["勝率が高いです", "リスクが低いです", "FOMCイベント日です"]
    reason = "PDCA評価の自動説明テスト"
    decision_id = "KC-20250730-TEST"
    proposal = hermes_ai.propose(
        {"features": features, "labels": labels, "reason": reason},
        decision_id=decision_id,
        caller="king_noctria"
    )
    print("\n👑 王への説明進言:")
    for k, v in proposal.items():
        print(f"{k}: {v}")
    logging.info("--- Hermes Cognitor: 理想形テスト完了 ---")
