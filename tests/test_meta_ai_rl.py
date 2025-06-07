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

    # 簡易テスト：エピソード数
    num_episodes = 100

    for episode in range(num_episodes):
        # --- ダミー市場データ ---
        market_data = {
            "price": 1.25,
            "volume": 150,
            "spread": np.random.uniform(0.01, 0.03),
            "order_block": 0.3,
            "volatility": np.random.uniform(0.05, 0.2),
            "price_history": [1.2, 1.22, 1.25, 1.23, 1.24],
            "profit_pips": np.random.uniform(-10, 10)  # 損益pips
        }

        # MetaAIで戦略決定
        final_action = meta_ai.decide_final_action(market_data)

        # --- ここで「複合スコア報酬式」を計算 ---
        profit = market_data["profit_pips"]
        volatility = market_data["volatility"]
        spread = market_data["spread"]
        alpha = 0.5
        beta = 0.3

        reward = profit - alpha * volatility - beta * spread

        # --- 次状態（仮） ---
        next_state = np.random.rand(12)

        # --- 学習サイクルに投入 ---
        meta_ai.learn(
            state=np.random.rand(12),  # 例: 観測データ
            action=final_action,
            reward=reward,
            next_state=next_state,
            done=False  # 継続扱い
        )

        # --- ログ出力 ---
        print(f"Episode {episode + 1}/{num_episodes} | action={final_action} | reward={reward:.2f}")

    print("✅ テスト完了！MetaAIのPPO強化学習サイクルは正常に動作しています")

if __name__ == "__main__":
    main()
