# src/plan_data/feature_spec.py
# -*- coding: utf-8 -*-

"""
Noctria Kingdom - Plan層 標準特徴量セット・スキーマ & ユーティリティ
-------------------------------------------------------------------
- Plan（計画・戦略立案）フェーズで扱う“標準DataFrame”の仕様を定義
- src/plan_data/ 以下の collector / features / analyzer / statistics 等が準拠
- ここを更新するときは、下流の並び順や補完ロジックにも影響する点に注意

本モジュールが提供するもの
- PLAN_FEATURE_COLUMNS : 代表的な列カタログ（仕様カタログ）
- STANDARD_FEATURE_ORDER: “標準8列”の並び（下流が想定する基本観測ベクトル）
- FEATURE_SPEC         : align_to_feature_spec のデフォルト（互換用）
- align_to_feature_spec(df, required=..., fill_value=0.0)
- select_standard_8(df)
- get_plan_feature_order(obs_dim)
- align_to_plan_features(df, required_features=None, fill_value=0.0)

変更点（2025-08）
- 外部依存の FRED を段階的に縮小。列は前方互換のため残すが、値は NaN 可。
- GNews を主要ニュース特徴として明示（news_count / positive / negative）。
- import パスを `src.` で始めない形に是正（パッケージとして正しい相対）。
"""

from __future__ import annotations

from typing import Iterable, Optional, List, Sequence

import numpy as np
import pandas as pd


# =====================================================================
# 仕様カタログ（Plan が出力・整形後に“あり得る”代表列の一覧）
# すべてを毎回埋める必要はない。collector が持っていない列は欠損(NaN)で良い。
# =====================================================================
PLAN_FEATURE_COLUMNS: List[str] = [
    # タイムキー / メタ
    "date", "tag", "strategy",

    # ===== USDJPY（基本パネル）=====
    "usdjpy_close", "usdjpy_volume", "usdjpy_return",
    "usdjpy_volatility_5d", "usdjpy_volatility_20d", "usdjpy_rsi_14d",
    "usdjpy_gc_flag", "usdjpy_po_up", "usdjpy_po_down",

    # ===== 市場関連の代表指標 =====
    "sp500_close",
    "vix_close",

    # ===== ニュース（GNews を主とする）=====
    "news_count", "news_positive", "news_negative",
    "news_positive_ratio", "news_negative_ratio", "news_spike_flag",

    # ===== マクロ（FRED互換カラム：値は NaN 可）=====
    "cpiaucsl_value", "cpiaucsl_diff", "cpiaucsl_spike_flag",
    "fedfunds_value", "fedfunds_diff", "fedfunds_spike_flag",
    "unrate_value",

    # ===== 経済イベント（日次フラグ；CSV由来。無ければ欠損でOK）=====
    "fomc", "cpi", "nfp", "ecb", "boj", "gdp",

    # ===== 検証系（統計/評価ログ）=====
    "win_rate", "max_dd", "num_trades",
]


# =====================================================================
# “標準8列”: 下流の観測ベクトルの最小構成（順序固定）
# - まずは USDJPY の価格・リスク系 + 市場の温度感（SP500/VIX）
# - collector/feature の最小互換を意識
# =====================================================================
STANDARD_FEATURE_ORDER: List[str] = [
    "usdjpy_close",
    "usdjpy_volume",
    "usdjpy_return",
    "usdjpy_volatility_5d",
    "usdjpy_volatility_20d",
    "usdjpy_rsi_14d",
    "sp500_close",
    "vix_close",
]

# 互換のため（旧コードが参照している場合）
FEATURE_SPEC: Sequence[str] = STANDARD_FEATURE_ORDER


# =====================================================================
# サンプル DataFrame（仕様確認用）
# =====================================================================
SAMPLE_PLAN_DF = pd.DataFrame([
    {
        "Date": "2025-08-01", "tag": "bull_trend", "strategy": "v2-ma-cross",
        "USDJPY_Close": 155.23, "USDJPY_Volume": 4000, "USDJPY_Return": 0.002,
        "USDJPY_Volatility_5d": 0.007, "USDJPY_Volatility_20d": 0.009, "USDJPY_RSI_14d": 72.4,
        "USDJPY_GC_Flag": 1, "USDJPY_PO_UP": 1, "USDJPY_PO_DOWN": 0,
        "sp500_close": 5588.5, "vix_close": 14.2,
        "News_Count": 21, "News_Positive": 9, "News_Negative": 6,
        "News_Positive_Ratio": 0.428, "News_Negative_Ratio": 0.286, "News_Spike_Flag": 0,
        "CPIAUCSL_Value": 310.12, "CPIAUCSL_Diff": 0.13, "CPIAUCSL_Spike_Flag": 0,
        "FEDFUNDS_Value": 5.25, "FEDFUNDS_Diff": 0.00, "FEDFUNDS_Spike_Flag": 0,
        "unrate_value": 4.1,
        "FOMC": 1, "NFP": 0,
        "win_rate": 0.81, "max_dd": -7.4, "num_trades": 32,
    },
    {
        "Date": "2025-08-02", "tag": "range", "strategy": "v2-ma-cross",
        "USDJPY_Close": 154.88, "USDJPY_Volume": 3100, "USDJPY_Return": -0.0023,
        "USDJPY_Volatility_5d": 0.008, "USDJPY_Volatility_20d": 0.010, "USDJPY_RSI_14d": 60.5,
        "USDJPY_GC_Flag": 0, "USDJPY_PO_UP": 0, "USDJPY_PO_DOWN": 0,
        "sp500_close": 5592.3, "vix_close": 13.9,
        "News_Count": 16, "News_Positive": 3, "News_Negative": 7,
        "News_Positive_Ratio": 0.188, "News_Negative_Ratio": 0.438, "News_Spike_Flag": 0,
        "CPIAUCSL_Value": 310.13, "CPIAUCSL_Diff": 0.01, "CPIAUCSL_Spike_Flag": 0,
        "FEDFUNDS_Value": 5.25, "FEDFUNDS_Diff": 0.00, "FEDFUNDS_Spike_Flag": 0,
        "unrate_value": 4.1,
        "FOMC": 0, "NFP": 1,
        "win_rate": 0.75, "max_dd": -8.9, "num_trades": 28,
    },
])


# =====================================================================
# CamelCase → snake_case の公式リネーム表（SAMPLE_PLAN_DF 由来）
# =====================================================================
_SNAKE_RENAMES = {
    "Date": "date",
    "USDJPY_Close": "usdjpy_close",
    "USDJPY_Volume": "usdjpy_volume",
    "USDJPY_Return": "usdjpy_return",
    "USDJPY_Volatility_5d": "usdjpy_volatility_5d",
    "USDJPY_Volatility_20d": "usdjpy_volatility_20d",
    "USDJPY_RSI_14d": "usdjpy_rsi_14d",
    "USDJPY_GC_Flag": "usdjpy_gc_flag",
    "USDJPY_PO_UP": "usdjpy_po_up",
    "USDJPY_PO_DOWN": "usdjpy_po_down",

    "News_Count": "news_count",
    "News_Positive": "news_positive",
    "News_Negative": "news_negative",
    "News_Positive_Ratio": "news_positive_ratio",
    "News_Negative_Ratio": "news_negative_ratio",
    "News_Spike_Flag": "news_spike_flag",

    "CPIAUCSL_Value": "cpiaucsl_value",
    "CPIAUCSL_Diff": "cpiaucsl_diff",
    "CPIAUCSL_Spike_Flag": "cpiaucsl_spike_flag",

    "FEDFUNDS_Value": "fedfunds_value",
    "FEDFUNDS_Diff": "fedfunds_diff",
    "FEDFUNDS_Spike_Flag": "fedfunds_spike_flag",

    "FOMC": "fomc",
    "NFP": "nfp",
    # すでに snake_case のもの（sp500_close, vix_close 等）はそのまま
}


# =====================================================================
# 整形ユーティリティ
# =====================================================================
def align_to_feature_spec(
    df: pd.DataFrame,
    required: Optional[Iterable[str]] = None,
    fill_value: float = 0.0,
) -> pd.DataFrame:
    """
    入力 DataFrame を Plan 仕様にアラインするヘルパー。

    1) 既知の CamelCase 列を snake_case に改名（未定義はそのまま）
    2) required（既定は STANDARD_FEATURE_ORDER）に含まれる列を補完（不足は fill_value）
    3) required の順序に並べ替え
    4) 数値列は float32 化し、NaN/Inf を安全に除去（ffill/bfill→fillna(fill_value)）

    注意:
    - 'date' はタイムキーとして基本は object/datetime を許容。数値化対象から除外。
    """
    work = df.copy()

    # 1) リネーム（既知マッピングのみ置換）
    if _SNAKE_RENAMES:
        rename_map = {c: _SNAKE_RENAMES.get(c, c) for c in work.columns}
        work = work.rename(columns=rename_map)

    # 2) 必須列セット
    req = list(required) if required is not None else list(STANDARD_FEATURE_ORDER)

    # 3) 不足列は補完
    for col in req:
        if col not in work.columns:
            work[col] = np.nan if col == "date" else fill_value

    # 4) 並べ替え（ここで列は req のみになる）
    work = work[req]

    # 5) 数値化と安全化
    numeric_cols = [c for c in work.columns if c != "date"]
    if numeric_cols:
        work[numeric_cols] = (
            work[numeric_cols]
            .apply(pd.to_numeric, errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .ffill().bfill().fillna(fill_value)
            .astype(np.float32)
        )
    return work


def select_standard_8(df: pd.DataFrame) -> pd.DataFrame:
    """
    “標準8列”（STANDARD_FEATURE_ORDER）だけに絞って返すショートカット。
      - 列の欠損は 0.0 で補完
      - 列順は STANDARD_FEATURE_ORDER に合わせる
      - float32 / NaN・Inf 除去済み
    """
    return align_to_feature_spec(df, required=STANDARD_FEATURE_ORDER, fill_value=0.0)


# 追加拡張候補（“標準8列”を超えるときに優先的に採用する列）
_FALLBACK_NUMERIC_ORDER: List[str] = [
    # 市況系
    "sp500_close", "vix_close",
    # ニュース代表
    "news_count",
    # マクロ代表（NaN 許容）
    "cpiaucsl_value", "fedfunds_value", "unrate_value",
]

# 文字列・メタ系は除外
_EXCLUDE_FROM_NUMERIC = {"date", "tag", "strategy"}


def get_plan_feature_order(obs_dim: int) -> List[str]:
    """
    観測次元に応じて使用する特徴量の順序（snake_case）を返す。
    - 基本は STANDARD_FEATURE_ORDER（“標準8列”）
    - 8を超える場合は _FALLBACK_NUMERIC_ORDER から順に拡張
    - それでも足りなければ PLAN_FEATURE_COLUMNS から数値候補を追加
    """
    if obs_dim < 1:
        raise ValueError(f"obs_dim must be >= 1 (got {obs_dim})")

    base: List[str] = list(STANDARD_FEATURE_ORDER)

    if obs_dim <= len(base):
        return base[:obs_dim]

    # 追加候補で拡張
    extended = base + [c for c in _FALLBACK_NUMERIC_ORDER if c not in base]
    if obs_dim <= len(extended):
        return extended[:obs_dim]

    # さらに足りなければ、仕様カタログから数値らしいカラムを追加
    for col in PLAN_FEATURE_COLUMNS:
        if col in extended or col in _EXCLUDE_FROM_NUMERIC:
            continue
        extended.append(col)
        if len(extended) >= obs_dim:
            break

    if len(extended) < obs_dim:
        raise ValueError(
            f"Requested obs_dim={obs_dim} exceeds available numeric features ({len(extended)}). "
            f"Consider extending _FALLBACK_NUMERIC_ORDER or PLAN_FEATURE_COLUMNS."
        )

    return extended[:obs_dim]


def align_to_plan_features(
    df: pd.DataFrame,
    required_features: Optional[Iterable[str]] = None,
    **kwargs,
) -> pd.DataFrame:
    """
    後方互換ラッパ：
    - `align_to_feature_spec` を呼び出し、列名は snake_case ベースで揃える
    - `required_features` が None の場合は STANDARD_FEATURE_ORDER（標準8列）
    """
    req = list(required_features) if required_features is not None else list(STANDARD_FEATURE_ORDER)
    return align_to_feature_spec(df, required=req, fill_value=float(kwargs.pop("fill_value", 0.0)))


# --- スクリプト実行時の簡易ドキュメント出力 ---
if __name__ == "__main__":
    print("■ Plan層 仕様カタログ（代表列）")
    print(PLAN_FEATURE_COLUMNS)

    print("\n■ 標準8列（順序固定）")
    print(STANDARD_FEATURE_ORDER)

    print("\n■ サンプル → 標準8列への整形結果（先頭2行）")
    print(select_standard_8(SAMPLE_PLAN_DF).head(2))

    print("\n■ get_plan_feature_order(6):")
    print(get_plan_feature_order(6))

    print("\n■ get_plan_feature_order(12):")
    print(get_plan_feature_order(12))


__all__ = [
    "PLAN_FEATURE_COLUMNS",
    "STANDARD_FEATURE_ORDER",
    "FEATURE_SPEC",
    "align_to_feature_spec",
    "select_standard_8",
    "get_plan_feature_order",
    "align_to_plan_features",
]
