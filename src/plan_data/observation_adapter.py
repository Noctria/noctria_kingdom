# src/plan_data/observation_adapter.py
# coding: utf-8
"""
Plan層のDataFrameを SB3/他モデルが受け取れる観測ベクトルに整形するアダプタ。
- STANDARD_FEATURE_ORDER に合わせて列を補完・数値化・クレンジング
- 最新行から obs_dim 長の観測ベクトル(np.ndarray, float32)を作る
- 列指定(PROMETHEUS_OBS_COLUMNS)や obs_dim(6/8など)に対応
"""

from __future__ import annotations

from typing import Optional, Sequence, List
import numpy as np
import pandas as pd
from pathlib import Path

from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER


def align_to_standard(df: pd.DataFrame,
                      order: Sequence[str] = STANDARD_FEATURE_ORDER) -> pd.DataFrame:
    """
    指定order（標準8列）に列を合わせ、数値化・補完する。
    - 欠損列は0.0で追加
    - 数値化（非数値→NaN→ffill/bfill→0.0）
    - Inf/NaNを0.0に
    """
    work = df.copy()
    for col in order:
        if col not in work.columns:
            work[col] = 0.0

    # 数値化 & クレンジング
    work[list(order)] = (
        work[list(order)]
        .apply(pd.to_numeric, errors="coerce")
        .ffill()
        .bfill()
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
        .astype(np.float32)
    )

    # date列があれば先頭に寄せる
    cols = (["date"] + list(order)) if "date" in work.columns else list(order)
    return work[cols]


def get_latest_observation(df: pd.DataFrame,
                           obs_dim: int = 6,
                           use_columns: Optional[List[str]] = None) -> np.ndarray:
    """
    標準8列にアライン → 最新行から観測ベクトル(obs_dim,)を作る。
    use_columns が None の場合、STANDARD_FEATURE_ORDER の先頭から obs_dim 個を使用。
    """
    aligned = align_to_standard(df)
    feature_cols = STANDARD_FEATURE_ORDER

    cols = use_columns if use_columns else feature_cols[:obs_dim]
    # 安全のため存在しない列はスキップせず0詰め
    vec: List[float] = []
    last = aligned.iloc[-1] if len(aligned) else pd.Series(dtype=np.float32)

    for c in cols[:obs_dim]:
        val = float(last.get(c, 0.0)) if not last.empty else 0.0
        vec.append(val)

    # パディング（指定列がobs_dim未満のとき）
    while len(vec) < obs_dim:
        vec.append(0.0)

    arr = np.asarray(vec, dtype=np.float32)
    if not np.all(np.isfinite(arr)):
        arr = np.nan_to_num(arr, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)
    return arr


def load_plan_from_path(path: str | Path) -> pd.DataFrame:
    """
    CSV/JSON/Parquet の単一ファイルを読み込む簡易ローダ。
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Planファイルが見つかりません: {p}")

    suffix = p.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(p)
    if suffix == ".json":
        return pd.read_json(p)
    if suffix in (".parquet", ".pq"):
        return pd.read_parquet(p)

    # デフォルトはCSV扱い
    return pd.read_csv(p)
