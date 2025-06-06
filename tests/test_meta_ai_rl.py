# tests/test_meta_ai_rl.py

import numpy as np
from strategies.Aurus_Singularis import AurusSingularis
from strategies.Levia_Tempest import LeviaTempest
from strategies.Noctus_Sentinella import NoctusSentinella
from strategies.Prometheus_Oracle import PrometheusOracle
from core.meta_ai import MetaAI

def main():
    print("✅ MetaAI PPO学習テストを開始します")

    # 各戦略AIを初期化
    strategy_agents = {
        "Aurus": AurusSingularis(),
        "Levia": LeviaTempest(),
        "Noctus": NoctusSentinella(),
        "Prometheus": PrometheusOracle()
    }

    # MetaAIに戦略群を渡す
    meta_ai = MetaAI(strategy_agents=strategy_agents)

    # PPO学習サイクルを開始
    meta_ai.learn(total_timesteps=1000)

    print("✅ テスト完了！MetaAIのPPO強化学習サイクルは正常に動作しています")

if __name__ == "__main__":
    main()
