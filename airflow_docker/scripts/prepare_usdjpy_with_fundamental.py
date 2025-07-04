#!/usr/bin/env python3
# coding: utf-8

import os
import pandas as pd
from dotenv import load_dotenv

def prepare_data():
    # 🔁 .env 読み込み
    load_dotenv()

    # 📥 入力CSVパスを .env から取得（なければデフォルト）
    input_csv_path = os.getenv(
        "USDJPY_RAW_CSV_PATH",
        "/noctria_kingdom/airflow_docker/data/USDJPY_M1_201501020805_202506161647.csv"
    )
    output_csv_path = "/noctria_kingdom/airflow_docker/data/preprocessed_usdjpy_with_fundamental.csv"

    if not os.path.exists(input_csv_path):
        print(f"❌ 入力ファイルが存在しません: {input_csv_path}")
        return

    try:
        print(f"📥 ヒストリカルデータ読み込み中...: {input_csv_path}")
        df = pd.read_csv(input_csv_path, sep="\t")

        # ✅ ヘッダー変換
        df.columns = [col.strip("<>").lower() for col in df.columns]
        df.rename(columns={
            'date': 'date',
            'time': 'time',
            'open': 'open',
            'high': 'high',
            'low': 'low',
            'close': 'close',
            'tickvol': 'tick_volume',
            'vol': 'volume',
            'spread': 'spread'
        }, inplace=True)

        # ✅ 日付 + 時刻 を datetime に統合
        df['datetime'] = pd.to_datetime(df['date'] + ' ' + df['time'])
        df.drop(columns=['date', 'time'], inplace=True)

        # ✅ ダミーのファンダメンタル列追加（今後APIやDBで更新）
        df['cpi'] = 0.0
        df['interest_diff'] = 0.0
        df['unemployment'] = 0.0

        # ✅ 保存
        df.to_csv(output_csv_path, index=False)
        print(f"✅ 加工完了: {output_csv_path}")

    except Exception as e:
        print(f"🚫 エラー発生: {e}")

def main():
    print("👑 王Noctria: USDJPYデータの前処理を始めよ！")
    prepare_data()
    print("✅ Levia: 前処理完了、王国のデータ戦力は整いました！")

if __name__ == "__main__":
    main()
