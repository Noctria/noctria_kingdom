# test_meta_ai_rl.py
import numpy as np
from core.meta_ai import MetaAI

def main():
    print("✅ MetaAI強化学習サイクルテストを開始します")

    # MetaAIのインスタンス生成
    meta_ai = MetaAI()

    # 簡易テスト：エピソード数
    num_episodes = 100

    for episode in range(num_episodes):
        # --- ダミー市場データ（例: 価格変動・ボラティリティなど） ---
        market_data = {
            "observation": np.random.rand(12),
            "historical_prices": np.random.rand(100, 5),
            "price_change": np.random.normal()
        }

        # MetaAIで戦略決定
        decision = meta_ai.decide_final_action(market_data)

        # --- ダミー報酬を生成（例: ±10pips程度の損益相当） ---
        profit = np.random.uniform(-10, 10)
        reward = profit  # シンプルに「損益 = 報酬」

        # --- 次状態（仮） ---
        next_state = np.random.rand(12)

        # --- 強化学習ループに投入 ---
        meta_ai.learn(
            state=market_data["observation"],
            action=decision["action"],
            reward=reward,
            next_state=next_state,
            done=False  # 今回は継続扱い
        )

        # --- ログ出力 ---
        print(f"Episode {episode + 1}/{num_episodes} | action={decision['action']} | reward={reward:.2f}")

    print("✅ テスト完了！MetaAIの学習サイクルは正常に動作しています")

if __name__ == "__main__":
    main()
