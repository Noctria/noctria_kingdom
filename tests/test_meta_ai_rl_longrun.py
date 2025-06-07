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
    print("✅ MetaAI長期PPO強化学習テスト（実データ）開始！")

    # 各戦略AIインスタンスを生成
    strategy_agents = {
        "Aurus": AurusSingularis(),
        "Levia": LeviaTempest(),
        "Noctus": NoctusSentinella(),
        "Prometheus": PrometheusOracle()
    }

    # MetaAIに戦略AI群を渡して初期化
    meta_ai = MetaAI(strategy_agents=strategy_agents)

    # 例: 実際のヒストリカルデータファイルから観測データ生成（省略可）
    # ここではランダム観測データを利用
    observation = np.random.rand(12)

    # 環境の初期化
    obs = meta_ai.reset()

    # 例: 50,000ステップの長期学習
    total_timesteps = 50000
    meta_ai.learn(total_timesteps=total_timesteps)

    print("✅ MetaAI長期PPO強化学習テスト完了！")

if __name__ == "__main__":
    main()
