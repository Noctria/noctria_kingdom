from core.path_config import *
#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
from core.meta_ai import MetaAI
from stable_baselines3 import PPO

def load_real_time_data(csv_path):
    """
    CSVファイルからリアルタイムの市場データを読み込む（例: OHLCV + ファンダメンタル指標）
    """
    df = pd.read_csv(csv_path, parse_dates=['datetime'])
    df.set_index('datetime', inplace=True)
    return df

def forward_test():
    print("✅ フォワードテスト開始！")

    # 実際の市場データ（MT5からダウンロードしたデータなど）
    real_time_data_path = str(PROCESSED_DATA_DIR / "preprocessed_usdjpy_with_fundamental.csv")
    real_time_data = load_real_time_data(real_time_data_path)

    # 各戦略AI（実際のモデルで置き換え可）
    strategy_agents = {
        "Aurus": None,
        "Levia": None,
        "Noctus": None,
        "Prometheus": None
    }

    # MetaAI環境の初期化
    env = MetaAI(strategy_agents=strategy_agents)

    # 学習済みのPPOモデルを読み込み（例として再学習する形に）
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1
    )

    # 1ステップずつ市場データを使ってテスト
    for idx, (timestamp, row) in enumerate(real_time_data.iterrows()):
        # ダミーの観測ベクトル（実際は戦略AIが加工する場合あり）
        obs = row.values  # 例: OHLCV + ファンダ指標
        obs = obs[:12]    # 12次元に整形（例）
        
        # モデルからアクションを予測
        action, _states = model.predict(obs, deterministic=True)

        # 環境を進行
        obs, reward, done, _ = env.step(action)

        # ログ出力
        print(f"[{timestamp}] Action: {action}, Reward: {reward:.3f}")

        if done:
            obs = env.reset()

    print("✅ フォワードテスト完了！")

if __name__ == "__main__":
    forward_test()
