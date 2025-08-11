# src/utils/model_io.py
# -*- coding: utf-8 -*-
"""
モデル保存ユーティリティ
- build_model_path: 保存先ディレクトリの構築
- infer_obs_dim_from_env: 環境から観測次元を推定
- atomic_save_model: SB3モデルのアトミック保存＋メタデータ出力＋latest更新
"""

from __future__ import annotations

import json
import math
import os
import shutil
import tempfile
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Union

# gymnasium がある前提だが、保険で try
try:
    from gymnasium import spaces as gym_spaces  # type: ignore
except Exception:  # pragma: no cover
    gym_spaces = None  # type: ignore

# numpy もJSON安全化に使う
try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None  # type: ignore


# ========== JSON セーフ化ユーティリティ ==========

def _finite_to_string(x: float) -> Union[float, str]:
    """inf/NaN を JSON セーフな文字列に変換（規格準拠）。"""
    if isinstance(x, float):
        if math.isnan(x):
            return "NaN"
        if math.isinf(x):
            return "Infinity" if x > 0 else "-Infinity"
    return x


def _np_to_base(obj: Any) -> Any:
    """numpy 型を素の Python に変換。"""
    if np is None:
        return obj
    if isinstance(obj, np.generic):
        return obj.item()
    if isinstance(obj, np.ndarray):
        # 配列は大きくなる可能性があるため、サイズが大きい場合は要約
        if obj.size <= 64:
            return [_finite_to_string(float(v)) if isinstance(v, (float, np.floating)) else _np_to_base(v) for v in obj.tolist()]
        # 要約（min/max/shape）
        try:
            _min = float(np.nanmin(obj))
            _max = float(np.nanmax(obj))
        except Exception:
            _min, _max = None, None
        return {
            "summary": True,
            "shape": list(obj.shape),
            "dtype": str(obj.dtype),
            "min": _finite_to_string(_min) if _min is not None else None,
            "max": _finite_to_string(_max) if _max is not None else None,
        }
    return obj


def _space_to_spec(space: Any) -> Dict[str, Any]:
    """Gym/Gymnasium の Space を JSON セーフな辞書へ."""
    if gym_spaces is None:
        return {"space": str(space)}

    if isinstance(space, gym_spaces.Box):
        low = getattr(space, "low", None)
        high = getattr(space, "high", None)
        if np is not None:
            if isinstance(low, np.ndarray):
                low = _np_to_base(low)
            if isinstance(high, np.ndarray):
                high = _np_to_base(high)
        return {
            "space": "Box",
            "shape": list(space.shape),
            "dtype": str(space.dtype),
            "low": low,
            "high": high,
        }
    if isinstance(space, gym_spaces.Discrete):
        return {"space": "Discrete", "n": int(space.n)}
    if hasattr(gym_spaces, "MultiBinary") and isinstance(space, gym_spaces.MultiBinary):
        return {"space": "MultiBinary", "n": int(space.n)}
    if hasattr(gym_spaces, "MultiDiscrete") and isinstance(space, gym_spaces.MultiDiscrete):
        nvec = getattr(space, "nvec", None)
        if np is not None and isinstance(nvec, np.ndarray):
            nvec = [int(v) for v in nvec.tolist()]
        return {"space": "MultiDiscrete", "nvec": nvec}
    if isinstance(space, gym_spaces.Dict):
        return {"space": "Dict", "spaces": {k: _space_to_spec(v) for k, v in space.spaces.items()}}
    if isinstance(space, gym_spaces.Tuple):
        return {"space": "Tuple", "spaces": [_space_to_spec(s) for s in space.spaces]}
    # その他は文字列で
    return {"space": str(space)}


def _to_jsonsafe(obj: Any) -> Any:
    """さまざまなオブジェクトを JSON セーフへ変換する default callable."""
    # dataclass
    if is_dataclass(obj):
        return asdict(obj)

    # numpy 系
    try:
        if np is not None:
            if isinstance(obj, np.generic):
                return obj.item()
            if isinstance(obj, np.ndarray):
                return _np_to_base(obj)
    except Exception:
        pass

    # Gym/Gymnasium Space
    try:
        if gym_spaces is not None and isinstance(obj, gym_spaces.Space):  # type: ignore
            return _space_to_spec(obj)
    except Exception:
        pass

    # Path
    if isinstance(obj, (Path, )):
        return str(obj)

    # datetime
    if isinstance(obj, datetime):
        return obj.isoformat()

    # 基本型 or 反復可能
    if isinstance(obj, (str, int, float, bool)) or obj is None:
        return _finite_to_string(obj) if isinstance(obj, float) else obj

    # dict
    if isinstance(obj, dict):
        return {str(k): _to_jsonsafe(v) for k, v in obj.items()}

    # list/tuple/set
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonsafe(v) for v in obj]

    # fallback: 文字列化
    return str(obj)


# ========== パス構築/観測次元推定 ==========

def build_model_path(
    base_dir: Union[str, Path],
    project: str,
    algo: str,
    obs_dim: int,
    tag: Optional[str] = None,
) -> Path:
    """
    例: /opt/airflow/data/models/prometheus/PPO/obs8/<tag or timestamp>/
    """
    base = Path(base_dir)
    stamp = tag or datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    return base / project / str(algo) / f"obs{obs_dim}" / stamp


def _flatten_obs_dim(space: Any) -> int:
    """観測空間の一次元サイズを推定。Dictは総和、Boxはshape積。"""
    if gym_spaces is None:
        # 最低限のフォールバック
        shape = getattr(space, "shape", None)
        if shape:
            n = 1
            for s in shape:
                n *= int(s)
            return int(n)
        return int(getattr(space, "n", 0))

    if isinstance(space, gym_spaces.Box):
        n = 1
        for s in space.shape:
            n *= int(s)
        return int(n)
    if isinstance(space, gym_spaces.Discrete):
        return 1
    if hasattr(gym_spaces, "MultiBinary") and isinstance(space, gym_spaces.MultiBinary):
        return int(space.n)
    if hasattr(gym_spaces, "MultiDiscrete") and isinstance(space, gym_spaces.MultiDiscrete):
        # 各離散次元を one-hot 等と仮定するなら要件に応じて調整
        # ここでは次元数（長さ）を返す
        return int(len(space.nvec))
    if isinstance(space, gym_spaces.Dict):
        return int(sum(_flatten_obs_dim(s) for s in space.spaces.values()))
    if isinstance(space, gym_spaces.Tuple):
        return int(sum(_flatten_obs_dim(s) for s in space.spaces))
    # fallback
    shape = getattr(space, "shape", None)
    if shape:
        n = 1
        for s in shape:
            n *= int(s)
        return int(n)
    return int(getattr(space, "n", 0))


def infer_obs_dim_from_env(env: Any) -> int:
    """
    環境から観測次元を推定。env.observation_space を想定。
    SB3でVector化される前の生envを渡す想定。
    """
    space = getattr(env, "observation_space", None)
    if space is None:
        # 一部のEnvは属性名が違う可能性
        space = getattr(getattr(env, "unwrapped", env), "observation_space", None)
    if space is None:
        raise ValueError("env has no observation_space")
    return _flatten_obs_dim(space)


# ========== メタデータ書き込み/アトミック保存 ==========

def _write_metadata(meta_path: Union[str, Path], payload: Dict[str, Any]) -> None:
    meta_path = Path(meta_path)
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=_to_jsonsafe)


def _safe_symlink_latest(latest_link: Path, target_dir: Path) -> None:
    """
    latest シンボリックリンクを更新（失敗したらコピーにフォールバック）
    """
    try:
        if latest_link.exists() or latest_link.is_symlink():
            try:
                latest_link.unlink()
            except Exception:
                pass
        latest_link.parent.mkdir(parents=True, exist_ok=True)
        latest_link.symlink_to(target_dir, target_is_directory=True)
    except Exception:
        # Windows/FS都合でsymlink不可の場合は shallow copy
        try:
            if latest_link.exists():
                shutil.rmtree(latest_link)
        except Exception:
            pass
        try:
            shutil.copytree(target_dir, latest_link)
        except Exception:
            # どうしてもダメなら諦める
            pass


def atomic_save_model(
    model: Any,
    save_path: Union[str, Path],
    metadata_extra: Optional[Dict[str, Any]] = None,
    env: Optional[Any] = None,
    project: Optional[str] = None,
) -> Path:
    """
    SB3モデルを一時ディレクトリに保存 → 最終ディレクトリへアトミック移動。
    併せて metadata.json を JSON セーフで書き出し、latest を更新する。

    Returns:
        final_dir (Path): 保存先ディレクトリ
    """
    save_dir = Path(save_path)
    save_dir.mkdir(parents=True, exist_ok=True)

    # 一時領域
    tmp_root = save_dir.parent
    tmp_dir = Path(tempfile.mkdtemp(prefix="model_tmp_", dir=str(tmp_root)))

    try:
        # --- モデル本体保存（SB3は .zip を作る） ---
        tmp_model_stem = tmp_dir / "model"
        # SB3: model.save("path_without_ext") → "path_without_ext.zip" を出力
        if hasattr(model, "save"):
            model.save(str(tmp_model_stem))
        else:
            raise RuntimeError("model has no .save() method compatible with SB3")

        # --- メタ生成（JSON セーフ） ---
        algo_name = getattr(model, "__class__", type(model)).__name__
        obs_dim = None
        env_info: Dict[str, Any] = {}
        if env is not None:
            try:
                obs_dim = infer_obs_dim_from_env(env)
            except Exception as e:
                obs_dim = None
                env_info["obs_dim_error"] = str(e)

            env_info.update({
                "env_class": f"{env.__class__.__module__}:{env.__class__.__name__}",
                "observation_space": _to_jsonsafe(getattr(env, "observation_space", None)),
                "action_space": _to_jsonsafe(getattr(env, "action_space", None)),
            })

            # 任意で env 側に config があれば拾う
            for k in ("config", "kwargs", "params"):
                if hasattr(env, k):
                    try:
                        env_info[k] = _to_jsonsafe(getattr(env, k))
                    except Exception:
                        pass

        meta: Dict[str, Any] = {
            "project": project,
            "algo": algo_name,
            "saved_at_utc": datetime.utcnow().isoformat(),
            "save_dir": str(save_dir),
            "files": {
                "model_zip": "model.zip",
                "metadata": "metadata.json",
            },
            "environment": env_info,
        }
        if obs_dim is not None:
            meta["obs_dim"] = int(obs_dim)
        if metadata_extra:
            # ユーザ追加情報を上書きマージ
            meta.update(metadata_extra)

        # --- 最終配置 ---
        # 1) tmp から final へ model.zip を移動
        final_model_zip = save_dir / "model.zip"
        tmp_model_zip = tmp_model_stem.with_suffix(".zip")
        shutil.move(str(tmp_model_zip), str(final_model_zip))

        # 2) metadata.json を書き込み（JSONセーフ）
        _write_metadata(save_dir / "metadata.json", meta)

        # 3) latest 更新（<base>/project/<algo>/obsX/latest → save_dir）
        try:
            # 推奨パス構造: .../<project>/<algo>/obs<obs_dim>/<tag>/
            # obs_dim が None の場合も、親から latest を張る
            latest_link = save_dir.parent / "latest"
            _safe_symlink_latest(latest_link, save_dir)
        except Exception:
            pass

        return save_dir

    finally:
        # 一時領域クリーンアップ
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
