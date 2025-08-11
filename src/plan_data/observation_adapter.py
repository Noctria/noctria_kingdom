# src/plan_data/observation_adapter.py
# coding: utf-8
"""
Observation Adapter
-------------------
Plan層のDataFrame -> 学習/Env向けの観測ベクトル(np.float32)に整形するユーティリティ。

- 既定: 6次元（既存SB3モデル互換）
- 標準: 8次元（STANDARD_FEATURE_ORDERに準拠）
- >8次元: feature_spec.get_plan_feature_order() に従って拡張（後方互換）
- 環境変数で次元や列セットを上書き可能
    NOCTRIA_ENV_OBS_DIM / PROMETHEUS_OBS_DIM   ... 観測次元
    PROMETHEUS_OBS_COLUMNS_6 (JSON配列)        ... 6次元時の列選択
"""

from __future__ import annotations

import json
import os
from typing import Iterable, List, Optional, Sequence

import numpy as np
import pandas as pd

from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER
from src.plan_data.feature_spec import (
    align_to_plan_features,  # 後方互換ラッパ（snake化・数値化・欠損処理）
    get_plan_feature_order,  # obs_dimに応じた列順を返す
)


# ---- 環境変数ヘルパ ---------------------------------------------------------

def _to_int_or_none(x: Optional[str]) -> Optional[int]:
    if x is None:
        return None
    try:
        return int(x.strip())
    except Exception:
        return None


def _get_obs_dim(default: int = 6) -> int:
    """
    観測次元の決定（環境変数 → 既定）。
    """
    return (
        _to_int_or_none(os.environ.get("NOCTRIA_ENV_OBS_DIM"))
        or _to_int_or_none(os.environ.get("PROMETHEUS_OBS_DIM"))
        or default
    )


def _get_override_obs6() -> Optional[List[str]]:
    """
    6次元時の列セットを環境変数で上書き（JSON配列）。
    ex) export PROMETHEUS_OBS_COLUMNS_6='["usdjpy_close","usdjpy_volatility_5d","sp500_close","vix_close","cpiaucsl_value","unrate_value"]'
    """
    raw = os.environ.get("PROMETHEUS_OBS_COLUMNS_6")
    if not raw:
        return None
    try:
        cols = json.loads(raw)
        if isinstance(cols, list) and all(isinstance(c, str) for c in cols):
            return cols
    except Exception:
        pass
    return None


# ---- 列セットの解決 ---------------------------------------------------------

# 6次元のデフォルト（既存モデル互換を想定、必要なら環境変数で調整可）
DEFAULT_OBS6: List[str] = [
    "usdjpy_close",
    "usdjpy_volatility_5d",
    "sp500_close",
    "vix_close",
    "cpiaucsl_value",
    "unrate_value",
]


def resolve_observation_columns(obs_dim: int) -> List[str]:
    """
    観測次元に応じて使用する列名リストを返す（snake_case）。
      - obs_dim == 6: 既定は DEFAULT_OBS6（環境変数で上書き可）
      - それ以外: feature_spec.get_plan_feature_order(obs_dim) に委譲（8以上も可）
    """
    if obs_dim == 6:
        return _get_override_obs6() or list(DEFAULT_OBS6)
    return list(get_plan_feature_order(obs_dim))


# ---- メイン変換 -------------------------------------------------------------

def _coerce_float_safe(v) -> float:
    try:
        v = float(v)
    except Exception:
        return 0.0
    if not np.isfinite(v):
        return 0.0
    return v


def adapt_observation(
    df: pd.DataFrame,
    *,
    obs_dim: Optional[int] = None,
    row: str | int | None = -1,
    ensure_float32: bool = True,
) -> np.ndarray:
    """
    Plan層DataFrameから「1サンプル」の観測ベクトル(np.float32, shape=(obs_dim,))を作る。

    Parameters
    ----------
    df : pd.DataFrame
        Plan層の生/混在DataFrame（カラム名の大文字/スネーク混在OK）
    obs_dim : Optional[int]
        観測次元。未指定なら環境変数→既定6。
    row : str | int | None
        どの行を使うか。-1 なら末尾、"latest" でも末尾扱い、intで0起点indexも可。
    ensure_float32 : bool
        True なら np.float32 に強制変換。
    """
    k = obs_dim or _get_obs_dim(default=6)
    if df is None or len(df) == 0:
        raise ValueError("adapt_observation: empty DataFrame given.")

    # 列セット決定（>8 次元も get_plan_feature_order が返す）
    cols = resolve_observation_columns(k)

    # Plan仕様へ正規化（必要列のみ・順序通り）
    aligned = align_to_plan_features(df, required_features=cols)

    # 行の決定
    if row in (-1, "latest", None):
        series = aligned.iloc[-1]
    else:
        idx = int(row)
        if not (-len(aligned) <= idx < len(aligned)):
            raise IndexError(f"adapt_observation: row index out of range: {row}")
        series = aligned.iloc[idx]

    # 値の抽出
    values = [_coerce_float_safe(series.get(c, 0.0)) for c in cols]

    vec = np.array(values, dtype=np.float32 if ensure_float32 else np.float64)

    # 念のため長さ調整（通常は cols と一致する）
    if vec.shape[0] < k:
        pad = np.zeros(k - vec.shape[0], dtype=vec.dtype)
        vec = np.concatenate([vec, pad], axis=0)
    elif vec.shape[0] > k:
        vec = vec[:k]

    if ensure_float32 and vec.dtype != np.float32:
        vec = vec.astype(np.float32, copy=False)
    return vec


def adapt_batch(
    df: pd.DataFrame,
    *,
    obs_dim: Optional[int] = None,
    ensure_float32: bool = True,
) -> np.ndarray:
    """
    Plan層DataFrameから「複数行」を観測行列にする。
    shape=(N, obs_dim)
    """
    k = obs_dim or _get_obs_dim(default=6)
    if df is None or len(df) == 0:
        # 空行列（0, k）を返す方が扱いやすい
        return np.zeros((0, k), dtype=np.float32 if ensure_float32 else np.float64)

    cols = resolve_observation_columns(k)
    aligned = align_to_plan_features(df, required_features=cols)

    # 欠損/非数は 0.0、float32/64
    X = (
        aligned.reindex(columns=cols, fill_value=0.0)
        .apply(pd.to_numeric, errors="coerce")
        .replace([np.inf, -np.inf], np.nan)
        .fillna(0.0)
    )
    mat = X.to_numpy(dtype=np.float32 if ensure_float32 else np.float64)

    # 念のため列長調整
    if mat.shape[1] < k:
        pad = np.zeros((mat.shape[0], k - mat.shape[1]), dtype=mat.dtype)
        mat = np.concatenate([mat, pad], axis=1)
    elif mat.shape[1] > k:
        mat = mat[:, :k]

    if ensure_float32 and mat.dtype != np.float32:
        mat = mat.astype(np.float32, copy=False)
    return mat


def adapt_sequence(
    frames: Iterable[pd.DataFrame],
    *,
    obs_dim: Optional[int] = None,
    ensure_float32: bool = True,
) -> np.ndarray:
    """
    複数のDataFrame（ウィンドウ分割等）を連結して1本の観測行列にする。
    """
    k = obs_dim or _get_obs_dim(default=6)
    cols = resolve_observation_columns(k)

    mats: List[np.ndarray] = []
    for df in frames:
        if df is None or len(df) == 0:
            continue
        aligned = align_to_plan_features(df, required_features=cols)
        X = (
            aligned.reindex(columns=cols, fill_value=0.0)
            .apply(pd.to_numeric, errors="coerce")
            .replace([np.inf, -np.inf], np.nan)
            .fillna(0.0)
        )
        mats.append(X.to_numpy(dtype=np.float32 if ensure_float32 else np.float64))

    if not mats:
        return np.zeros((0, k), dtype=np.float32 if ensure_float32 else np.float64)
    return np.vstack(mats)
