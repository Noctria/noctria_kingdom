#!/usr/bin/env python3
# coding: utf-8

"""
👑 King Noctria (v2.0)
- Noctria王国の中枢。統治AIの全ての意思決定を司る。
- 5人の臣下AIからの進言と報告を統合し、最終的な王命を下す。
"""
import logging
import json
import pandas as pd
import numpy as np

# --- 王国の臣下AIをインポート ---
# ⚠️ 注意: veritas_machina.pyへのリネームを反映
from src.veritas.veritas_machina import VeritasStrategist
from src.strategies.prometheus_oracle import PrometheusOracle
from src.strategies.aurus_singularis import AurusSingularis
from src.strategies.levia_tempest import LeviaTempest
from src.strategies.noctus_sentinella import NoctusSentinella

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - 👑 KingNoctria: %(message)s')


class KingNoctria:
    """
    五臣会議を主宰し、王国の最終判断を下す統治AI。
    """

    def __init__(self):
        """
        コンストラクタ。各分野を専門とする臣下AIを招集する。
        """
        logging.info("王の評議会を構成するため、五臣を招集します。")
        self.veritas = VeritasStrategist()          # 戦略立案官
        self.prometheus = PrometheusOracle()        # 未来予測官
        self.aurus = AurusSingularis()              # 総合市場分析官
        self.levia = LeviaTempest()                 # 高速スキャルピングAI
        self.noctus = NoctusSentinella()            # リスク管理官
        logging.info("五臣の招集が完了しました。")

    def hold_council(self, market_data: dict) -> dict:
        """
        御前会議を開催し、市場データに基づき最終的な王命を下す。
        """
        logging.info("--------------------")
        logging.info("📣 御前会議を開催します…")

        # 1. 情報収集フェーズ: 各臣下からの報告を収集
        logging.info("各臣下からの報告を収集中…")
        aurus_proposal = self.aurus.propose(market_data)
        levia_proposal = self.levia.propose(market_data)
        # ⚠️ PrometheusとVeritasは現時点では文脈情報として扱い、直接の判断には使用しない
        # prometheus_forecast = self.prometheus.predict_with_confidence() 
        # veritas_proposal = self.veritas.propose()

        # 2. 行動決定フェーズ: 誰の進言を主軸とするか決定
        # Aurus(総合分析官)の判断を優先し、彼が静観を推奨する場合のみLevia(スキャルピング)の判断を考慮する
        primary_action = aurus_proposal['signal']
        if primary_action == "HOLD":
            logging.info("Aurusは静観を推奨。Leviaの短期的な見解を求めます。")
            primary_action = levia_proposal['signal']
        
        logging.info(f"主たる進言は『{primary_action}』と決定しました。")

        # 3. リスク評価フェーズ: Noctusによる最終リスク評価
        # Noctus(リスク管理官)に、決定された行動のリスクを評価させる
        noctus_assessment = self.noctus.assess(market_data, primary_action)
        
        # 4. 最終判断フェーズ: 王の決断
        final_decision = primary_action
        if noctus_assessment['decision'] == 'VETO':
            logging.warning(f"Noctusが拒否権を発動！理由: {noctus_assessment['reason']}")
            logging.warning("安全を最優先し、最終判断を『HOLD』に変更します。")
            final_decision = "HOLD"
        else:
            logging.info("Noctusは行動を承認。進言通りに最終判断を下します。")
            
        logging.info(f"👑 下される王命: 『{final_decision}』")
        logging.info("--------------------")

        # 会議の結果を一つの報告書にまとめる
        council_report = {
            "final_decision": final_decision,
            "assessments": {
                "aurus_proposal": aurus_proposal,
                "levia_proposal": levia_proposal,
                "noctus_assessment": noctus_assessment,
                # "prometheus_forecast": prometheus_forecast, # 将来的に追加
                # "veritas_proposal": veritas_proposal,     # 将来的に追加
            }
        }
        return council_report

# ========================================
# ✅ 単体テスト＆実行ブロック
# ========================================
if __name__ == "__main__":
    logging.info("--- 王の中枢機能、単独試練の儀を開始 ---")
    
    # 王のインスタンスを作成
    king = KingNoctria()
    
    # テスト用のダミー市場データを作成
    # Noctusのリスク評価に必要なヒストリカルデータも用意
    dummy_hist_data = pd.DataFrame({
        'Close': np.random.normal(loc=150, scale=2, size=100)
    })
    dummy_hist_data['returns'] = dummy_hist_data['Close'].pct_change().dropna()

    mock_market = {
        # テクニカル指標
        "price": 1.2530, "previous_price": 1.2510, "volume": 160, "volatility": 0.18,
        "sma_5_vs_20_diff": 0.001, "macd_signal_diff": 0.0005, "trend_strength": 0.6, "trend_prediction": "bullish",
        "rsi_14": 60.0, "stoch_k": 70.0, "momentum": 0.8,
        "bollinger_upper_dist": -0.001, "bollinger_lower_dist": 0.009,
        "sentiment": 0.7, "order_block": 0.4, "liquidity_ratio": 1.1, "symbol": "USDJPY",
        # ファンダメンタルズ指標
        "interest_rate_diff": 0.05, "cpi_change_rate": 0.03, "news_sentiment_score": 0.75,
        # リスク評価用データ
        "spread": 0.012, "historical_data": dummy_hist_data
    }
    
    # 御前会議を開催
    result = king.hold_council(mock_market)
    
    print("\n" + "="*50)
    print("📜 御前会議 最終報告書")
    print("="*50)
    # 結果を読みやすいようにJSON形式で表示
    print(json.dumps(result, indent=4, ensure_ascii=False))
    print("="*50)
    
    logging.info("\n--- 王の中枢機能、単独試練の儀を完了 ---")
