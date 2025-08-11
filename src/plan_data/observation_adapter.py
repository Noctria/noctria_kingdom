# src/plan_data/observation_adapter.py
# coding: utf-8
"""
Observation Adapter
-------------------
Plan層のDataFrame -> SB3/Env向けの観測ベクトル(np.float32)に整形するユーティリティ。

- 既定: 6次元（既存SB3モデル互換）
- 将来: 8次元（STANDARD_FEATURE_ORDERに完全準拠）
- 環境変数で次元や列セットを上書き可能
    NOCTRIA_ENV_OBS_DIM / PROMETHEUS_OBS_DIM   ... 観測次元
    PROMETHEUS_OBS_COLUMNS_6 (JSON配列)        ... 6次元時の列選択（任意）
"""

from __future__ import annotations

import json
import os
from typing import Iterable, List, Optional, Sequence, Tuple

import numpy as np
import pandas as pd

from src.plan_data.standard_feature_schema import STANDARD_FEATURE_ORDER
# ※ 前段で実装済みの「8列標準へ揃える」関数を使います
from src.plan_data.feature_spec import align_to_plan_features


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
    観測次元に応じて使用する列名リストを返す。

    - obs_dim == len(STANDARD_FEATURE_ORDER)=8: → 標準8列をそのまま採用
    - obs_dim == 6: → 既定は DEFAULT_OBS6（環境変数で上書き可）
    - それ以外:
        - obs_dim < 8: STANDARD_FEATURE_ORDER の先頭から obs_dim 個
        - obs_dim > 8: STANDARD_FEATURE_ORDER + 余りはゼロ埋め（列名は返せないので先頭8列を返す）
                        ※ 実運用では8列以内に揃えることを推奨
    """
    if obs_dim == len(STANDARD_FEATURE_ORDER):
        return list(STANDARD_FEATURE_ORDER)

    if obs_dim == 6:
        return _get_override_obs6() or list(DEFAULT_OBS6)

    if obs_dim < len(STANDARD_FEATURE_ORDER):
        return list(STANDARD_FEATURE_ORDER[:obs_dim])

    # obs_dim > 8 の場合は先頭8列を返す（実際の長さ拡張はゼロ埋めで対応）
    return list(STANDARD_FEATURE_ORDER)


# ---- メイン変換 -------------------------------------------------------------

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
        どの行を使うか。-1 なら末尾、"latest" でも末尾扱い。
    ensure_float32 : bool
        True なら np.float32 に強制変換。

    Returns
    -------
    np.ndarray
        shape=(obs_dim,), dtype=float32（ensure_float32=Trueのとき）
    """
    k = obs_dim or _get_obs_dim(default=6)

    # まずPlan仕様に正規化（ここで "date" や標準列がsnake_caseで揃う想定）
    aligned = align_to_plan_features(df)

    # 使う行の決定
    if row in (-1, "latest", None):
        series = aligned.iloc[-1]
    else:
        series = aligned.iloc[int(row)]

    # 列セットの決定
    cols = resolve_observation_columns(k)

    # 値の抽出（欠損/非数は 0.0 で埋め）
    values = []
    for c in cols:
        v = series.get(c, 0.0)
        try:
            v = float(v)
        except Exception:
            v = 0.0
        if not np.isfinite(v):
            v = 0.0
        values.append(v)

    vec = np.array(values, dtype=np.float32 if ensure_float32 else np.float64)

    # obs_dim が 8 より大きい場合は残りをゼロ埋め
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
    cols = resolve_observation_columns(k)
    aligned = align_to_plan_features(df)

    # 欠損/非数は 0.0、float32
    X = aligned.reindex(columns=cols, fill_value=0.0).apply(
        pd.to_numeric, errors="coerce"
    ).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    mat = X.to_numpy(dtype=np.float32 if ensure_float32 else np.float64)

    # もし k > len(cols)（=8超）なら右側にゼロ列を足す
    if mat.shape[1] < k:
        pad = np.zeros((mat.shape[0], k - mat.shape[1]), dtype=mat.dtype)
        mat = np.concatenate([mat, pad], axis=1)
    elif mat.shape[1] > k:
        mat = mat[:, :k]

    if ensure_float32 and mat.dtype != np.float32:
        mat = mat.astype(np.float32, copy=False)

    return mat
