#!/usr/bin/env python3
# coding: utf-8

import numpy as np
import pandas as pd
from core.meta_ai import MetaAI
from strategies.Aurus_Singularis import AurusSingularis
from strategies.Levia_Tempest import LeviaTempest
from strategies.Noctus_Sentinella import NoctusSentinella
from strategies.Prometheus_Oracle import PrometheusOracle

def main():
    print("✅ MetaAI実データ学習サイクルテストを開始します")

    # === 1️⃣ 前処理済データ読み込み ===
    df = pd.read_csv("data/preprocessed_usdjpy_1h.csv")
    df["Datetime"] = pd.to_datetime(df["Datetime"])
    df.set_index("Datetime", inplace=True)

    # 特徴量だけ抽出（例: Open, High, Low, Close）
    features = df[["Open", "High", "Low", "Close"]].values
    print(f"読み込み完了: {features.shape}")

    # === 2️⃣ MetaAI初期化（臣下AIも含む） ===
    strategy_agents = {
        "Aurus": AurusSingularis(),
        "Levia": LeviaTempest(),
        "Noctus": NoctusSentinella(),
        "Prometheus": PrometheusOracle()
    }
    meta_ai = MetaAI(strategy_agents=strategy_agents)

    # === 3️⃣ PPO強化学習ループ ===
    total_episodes = 100
    for episode in range(total_episodes):
        # ダミー的にインデックスを循環（例: ランダム化も可）
        idx = episode % (len(features) - 30)

        # 観測・履歴などを生成
        market_data = {
            "observation": features[idx],
            "historical_prices": features[max(0, idx-30):idx+1],
            "price_change": features[idx][3] - features[idx][0]
        }

        # === 3️⃣ MetaAIによる戦略決定 ===
        action = meta_ai.decide_final_action(market_data)

        # === 4️⃣ シンプルな報酬計算（例: Close-Openの利益） ===
        profit = market_data["price_change"]
        reward = profit

        # === 5️⃣ 次状態を準備（次の足） ===
        next_idx = idx + 1 if idx + 1 < len(features) else idx
        next_state = features[next_idx]

        # === 6️⃣ MetaAIに学習サイクル投入 ===
        meta_ai.ppo_agent.learn(total_timesteps=2048)

        # === ログ出力 ===
        print(f"Episode {episode + 1}/{total_episodes} | action={action} | reward={reward:.3f}")

    print("✅ MetaAI統合PPO強化学習テスト（実データ）完了！")

if __name__ == "__main__":
    main()
