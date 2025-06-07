# tests/test_meta_ai_rl_real_data.py

import numpy as np
from core.meta_ai import MetaAI
from strategies.Aurus_Singularis import AurusSingularis
from strategies.Levia_Tempest import LeviaTempest
from strategies.Noctus_Sentinella import NoctusSentinella
from strategies.Prometheus_Oracle import PrometheusOracle

def main():
    print("✅ MetaAI統合PPO強化学習テスト（実データ・複合報酬式）を開始します")

    # 各戦略AIのインスタンスを生成
    strategy_agents = {
        "Aurus": AurusSingularis(),
        "Levia": LeviaTempest(),
        "Noctus": NoctusSentinella(),
        "Prometheus": PrometheusOracle()
    }

    # MetaAIに戦略AI群を渡して初期化
    meta_ai = MetaAI(strategy_agents=strategy_agents)

    # PPOによる強化学習ループを実行（例: 1万ステップ）
    meta_ai.learn(total_timesteps=10000)

    print("✅ MetaAI統合PPO強化学習テスト（実データ・複合報酬式）完了！")

if __name__ == "__main__":
    main()
