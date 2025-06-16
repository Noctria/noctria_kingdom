#!/usr/bin/env python3
# coding: utf-8

import pandas as pd
import numpy as np
import os

def main():
    input_file = "/mnt/e/noctria-kingdom-main/airflow_docker/logs/USDJPY_M1_201501020805_202506161647.csv"
    output_file = "/mnt/e/noctria-kingdom-main/airflow_docker/data/preprocessed_usdjpy_with_fundamental.csv"

    if not os.path.exists(input_file):
        print(f"❌ 入力ファイルが存在しません: {input_file}")
        return

    print("📥 ヒストリカルデータ読み込み中...")
    df = pd.read_csv(input_file, sep="\t")

    # ヘッダー変換
    df.columns = ["date", "time", "open", "high", "low", "close", "tickvol", "vol", "spread"]

    # ファンダメンタルデータを追加（仮のダミー）
    np.random.seed(42)
    df["interest_rate_diff"] = 1.5  # 固定値
    df["cpi"] = 3.2 + np.random.normal(0, 0.1, len(df))
    df["unemployment_rate"] = 4.1 + np.random.normal(0, 0.2, len(df))

    # 保存
    df.to_csv(output_file, index=False)
    print(f"✅ 加工完了: {output_file}")

if __name__ == "__main__":
    main()
