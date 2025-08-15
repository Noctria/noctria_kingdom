# Noctria Kingdom - Plan層 標準特徴量セット仕様

## 概要
Plan層で生成される市場特徴量DataFrame（feature_df）は、  
以下のカラム構成を基本標準とする。  
これに準拠してAI各臣下・評価系コードが設計される。

---

## 1. 市場系特徴量カラム例（USDJPYベース例）

| カラム名                 | 型       | 説明                        |
|-------------------------|----------|-----------------------------|
| Date                    | date     | 日付                        |
| USDJPY_Close            | float    | 終値                        |
| USDJPY_Return           | float    | 騰落率（日次）              |
| USDJPY_Volatility_5d    | float    | 5日間標準偏差ボラティリティ |
| USDJPY_Volatility_20d   | float    | 20日間標準偏差ボラティリティ|
| USDJPY_RSI_14d          | float    | 14日RSI                     |
| USDJPY_GC_Flag          | int      | ゴールデンクロスフラグ      |
| USDJPY_MA5              | float    | 5日移動平均                 |
| USDJPY_MA25             | float    | 25日移動平均                |
| USDJPY_MA75             | float    | 75日移動平均                |
| USDJPY_PO_UP            | int      | 3本MAパーフェクトオーダー上 |
| USDJPY_PO_DOWN          | int      | 3本MAパーフェクトオーダー下 |

---

## 2. ニュース・センチメント・イベント特徴量

| カラム名             | 型    | 説明                          |
|---------------------|-------|-------------------------------|
| News_Count          | int   | 当日ニュース件数              |
| News_Spike_Flag     | int   | ニュース急増フラグ            |
| News_Positive       | int   | ポジティブニュース件数        |
| News_Negative       | int   | ネガティブニュース件数        |
| News_Positive_Ratio | float | ポジティブ比率                |
| News_Negative_Ratio | float | ネガティブ比率                |
| News_Positive_Lead  | int   | ポジティブ優勢フラグ          |
| News_Negative_Lead  | int   | ネガティブ優勢フラグ          |
| FOMC                | int   | FOMCイベント日（1:あり）       |
| FOMC_Today_Flag     | int   | 本日FOMCフラグ                |
| ...                 | ...   | 他イベントも同様              |

---

## 3. マクロ指標系

| カラム名               | 型    | 説明                        |
|-----------------------|-------|-----------------------------|
| CPIAUCSL_Value        | float | CPI値                        |
| CPIAUCSL_Diff         | float | CPI変化                      |
| CPIAUCSL_Spike_Flag   | int   | CPI急変動フラグ              |
| UNRATE_Value          | float | 失業率                        |
| ...                   | ...   | 他指標も同様                 |

---

## 4. その他/任意拡張

- symbol、strategy、win_rate、max_dd など  
  評価/分析ログ結合時に付加されることもある

---

## サンプルDataFrame例

```python
import pandas as pd
sample = {
    "Date": ["2025-08-07"] * 2,
    "USDJPY_Close": [155.25, 155.80],
    "USDJPY_Return": [0.0012, 0.0035],
    "USDJPY_Volatility_5d": [0.007, 0.006],
    "USDJPY_RSI_14d": [60.2, 62.5],
    "News_Count": [15, 22],
    "News_Spike_Flag": [0, 1],
    "FOMC_Today_Flag": [1, 0],
    "CPIAUCSL_Value": [310.2, 311.1]
}
df = pd.DataFrame(sample)
print(df)
