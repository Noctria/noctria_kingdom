#!/usr/bin/env python3
# coding: utf-8

"""
🦉 Hermes Cognitor (v1.0)
- LLMベースの説明・要約AI（GPT-4o API利用を想定）
- 特徴量や要因ラベルを自然言語サマリーとして生成
- ニュース要約や根拠説明にも拡張しやすい構造
"""

import logging
from typing import Optional, Dict, Any, List

# --- 王国の基盤モジュールをインポート ---
from src.core.path_config import ORACLE_FORECAST_JSON

# ロギング設定（Aurus同等）
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')


class HermesCognitorStrategy:
    """
    Hermes Cognitor - LLM戦略クラス
    役割：分析AIの出力や市場状況を人間向けの自然言語で説明/要約する。
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        LLM API初期化（現状はAPIキー未使用でもダミーサマリー返し可）
        """
        self.api_key = api_key
        self.model = model

    def _build_prompt(self, features: Dict[str, Any], labels: List[str], reason: Optional[str] = None) -> str:
        """
        LLM説明用プロンプト組み立て（プロンプト設計のカスタマイズ拡張も容易）
        """
        prompt = "以下の特徴量と要因ラベルをもとに、市場戦略の根拠を人間向けに自然言語で要約してください。\n"
        if reason:
            prompt += f"【発令理由】{reason}\n"
        prompt += f"【特徴量】{features}\n"
        prompt += f"【要因ラベル】{labels}\n"
        prompt += "説明:"
        return prompt

    def summarize_strategy(self, features: Dict[str, Any], labels: List[str], reason: Optional[str] = None) -> str:
        """
        市場分析AIの特徴量・要因から自然言語サマリーを生成
        - 本番はGPT-4o等API呼び出し、今はダミー返し
        """
        prompt = self._build_prompt(features, labels, reason)
        logging.info("HermesCognitor: プロンプトを組み立てました。")
        # ▼ LLM API呼び出し本実装（サンプル/ダミー返し）
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
        # 今はダミー返し
        summary = "[ダミー要約] " + (labels[0] if labels else "特徴量・要因をもとに戦略の説明文がここに生成されます。")
        return summary

    def summarize_news(self, news_list: List[str], context: Optional[str] = None) -> str:
        """
        ニュースリストを自然言語要約（現状はダミー、将来GPT API連携）
        """
        prompt = f"ニュース一覧: {news_list}\nこの市場に与える影響を要約してください。"
        logging.info("HermesCognitor: ニュース要約プロンプト作成。")
        # LLM API呼び出し箇所はここに
        return "[ダミーニュース要約] " + (news_list[0][:40] + "..." if news_list else "ニュースがありません。")

    def propose(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        LLM大臣として王国に提出する“説明/要約レポート”生成
        - ML系AIの“propose”に相当
        """
        logging.info("HermesCognitor: propose呼び出し。")
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
            "reason": reason
        }

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- Hermes Cognitor: 単独テスト開始 ---")
    hermes_ai = HermesCognitorStrategy()
    features = {"win_rate": 78.9, "risk": "low", "fomc_today": True}
    labels = ["勝率が高いです", "リスクが低いです", "FOMCイベント日です"]
    reason = "PDCA評価の自動説明テスト"

    proposal = hermes_ai.propose({"features": features, "labels": labels, "reason": reason})
    print("\n👑 王への説明進言:")
    for k, v in proposal.items():
        print(f"{k}: {v}")
    logging.info("--- Hermes Cognitor: 単独テスト完了 ---")
