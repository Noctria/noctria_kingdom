import numpy as np
from core.meta_ai import MetaAI
from strategies.Aurus_Singularis import AurusSingularis
from strategies.Levia_Tempest import LeviaTempest
from strategies.Noctus_Sentinella import NoctusSentinella
from strategies.Prometheus_Oracle import PrometheusOracle

def main():
    print("✅ MetaAI強化学習サイクルテストを開始します")

    # 各戦略AIインスタンスを生成
    strategy_agents = {
        "Aurus": AurusSingularis(),
        "Levia": LeviaTempest(),
        "Noctus": NoctusSentinella(),
        "Prometheus": PrometheusOracle()
    }

    # MetaAIに戦略AI群を渡して初期化
    meta_ai = MetaAI(strategy_agents=strategy_agents)

    # ダミー市場データ
    mock_market_data = {
        "price": 1.2345,
        "volume": 150,
        "spread": 0.012,
        "order_block": 0.3,
        "volatility": 0.1,
        "price_history": [1.2, 1.22, 1.25, 1.23, 1.24]
    }

    # 1. 各戦略AIの統合アクションを取得
    final_action = meta_ai.decide_final_action(mock_market_data)
    print("MetaAI決定アクション:", final_action)

    # 2. 学習サイクルのテスト
    state = np.random.rand(12)
    next_state = np.random.rand(12)
    reward = np.random.uniform(-1, 1)
    done = False

    meta_ai.learn(state=state, action="BUY", reward=reward, next_state=next_state, done=done)

    print("✅ テスト完了")

if __name__ == "__main__":
    main()
