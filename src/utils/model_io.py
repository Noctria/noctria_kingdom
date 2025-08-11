# src/utils/model_io.py
# coding: utf-8
"""
SB3モデルの保存/読込を、安全&一貫した規約で行うユーティリティ。
- 保存パスに obs_dim を刻む: .../prometheus/obs{obs_dim}/{algo}/model_obs{obs_dim}d_{algo}_{ts}[_{tag}].zip
- サイドカーのメタ情報: 同名 .meta.json （obs_dim, algo, env情報, git情報 など）
- "latest" シンボリックリンクを更新（同ディレクトリ内）

使い方（学習コード側）:
    from pathlib import Path
    from src.utils.model_io import (
        infer_obs_dim_from_env, build_model_path, atomic_save_model
    )

    obs_dim = infer_obs_dim_from_env(env)  # env から推定（無ければ環境変数/8にフォールバック）
    save_path = build_model_path(
        base_dir=Path("/opt/airflow/data/models"),  # マウント済みの永続領域
        project="prometheus",
        algo=model.__class__.__name__,             # 例: "PPO" / "A2C" / "DQN"
        obs_dim=obs_dim,
        tag=run_id_or_trial_id,                    # 任意
    )
    atomic_save_model(model, save_path, metadata_extra={"train_params": params})
"""

from __future__ import annotations
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

def _safe_int(x: Optional[str]) -> Optional[int]:
    if not x:
        return None
    try:
        return int(str(x).strip())
    except Exception:
        return None

def infer_obs_dim_from_env(env: Any = None, *, default: int = 8) -> int:
    """
    Env があれば observation_space から、無ければ環境変数から obs_dim を推定。
    最後の手段として default を返す（標準は8）。
    """
    # 1) Env から推定
    try:
        if env is not None and hasattr(env, "observation_space"):
            shp = getattr(env.observation_space, "shape", None)
            if shp and len(shp) == 1 and shp[0] > 0:
                return int(shp[0])
    except Exception:
        pass

    # 2) 環境変数から
    for key in ("NOCTRIA_ENV_OBS_DIM", "PROMETHEUS_OBS_DIM"):
        v = _safe_int(os.environ.get(key))
        if v and v > 0:
            return v

    return int(default)

def _git_info() -> Dict[str, Optional[str]]:
    """
    コンテナ内で /opt/airflow がgitワークツリーならコミットID等を拾う。
    取れなくてもエラーにはしない。
    """
    def _run(cmd):
        try:
            out = subprocess.check_output(cmd, cwd="/opt/airflow", text=True, stderr=subprocess.DEVNULL)
            return out.strip()
        except Exception:
            return None

    return {
        "commit": _run(["git", "rev-parse", "HEAD"]),
        "branch": _run(["git", "rev-parse", "--abbrev-ref", "HEAD"]),
        "status": _run(["git", "status", "--porcelain"]),
        "remote": _run(["git", "remote", "get-url", "origin"]),
    }

def build_model_path(
    *,
    base_dir: Path,
    project: str,
    algo: str,
    obs_dim: int,
    tag: Optional[str] = None,
    timestamp: Optional[datetime] = None,
) -> Path:
    """
    保存先パスを組み立てる（まだ作成はしない）。
    例: /opt/airflow/data/models/prometheus/obs8/PPO/model_obs8d_PPO_20250811_071530_trial123.zip
    """
    ts = (timestamp or datetime.now()).strftime("%Y%m%d_%H%M%S")
    safe_algo = str(algo).upper()
    parts = [f"model_obs{obs_dim}d_{safe_algo}_{ts}"]
    if tag:
        parts.append(str(tag))
    fname = "_".join(parts) + ".zip"

    model_dir = base_dir / project / f"obs{obs_dim}" / safe_algo
    return model_dir / fname

def _write_metadata(meta_path: Path, payload: Dict[str, Any]) -> None:
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

def _symlink_latest(target: Path) -> None:
    """
    同ディレクトリに latest.zip / latest.meta.json のシンボリックリンクを張り直す。
    Windows ホストでも、コンテナ内（Linux）なら symlink 可能。
    失敗しても致命ではないので握り潰す。
    """
    try:
        d = target.parent
        latest_zip = d / "latest.zip"
        latest_meta = d / "latest.meta.json"
        for p in (latest_zip, latest_meta):
            if p.exists() or p.is_symlink():
                p.unlink(missing_ok=True)
        # zip
        latest_zip.symlink_to(target.name)
        # meta
        meta = target.with_suffix(".meta.json")
        if meta.exists():
            latest_meta.symlink_to(meta.name)
    except Exception:
        pass

def atomic_save_model(
    model: Any,
    save_path: Path,
    *,
    metadata_extra: Optional[Dict[str, Any]] = None,
    env: Any = None,
    project: str = "prometheus",
) -> Path:
    """
    SB3モデルを安全に保存:
      1) 一時ファイルに保存 → rename
      2) 同名 .meta.json を出力
      3) latest シンボリックリンクを更新

    Returns: 実際に保存した ZIP の Path
    """
    save_path = Path(save_path)
    save_path.parent.mkdir(parents=True, exist_ok=True)

    # 1) モデル保存（atomicに近い運用: tmp名→rename）
    tmp_path = save_path.with_suffix(".zip.tmp")
    if tmp_path.exists():
        tmp_path.unlink()
    model.save(str(tmp_path))
    tmp_path.replace(save_path)

    # 2) メタ情報
    obs_dim = infer_obs_dim_from_env(env)
    meta = {
        "created_at": datetime.now().isoformat(),
        "project": project,
        "algo": getattr(model, "__class__", type("X",(object,),{})).__name__ if model else None,
        "obs_dim": obs_dim,
        "env_class": env.__class__.__name__ if env is not None else None,
        "env_kwargs": getattr(env, "__dict__", None),
        "git": _git_info(),
        "file": save_path.name,
    }
    if metadata_extra:
        meta.update(metadata_extra)

    meta_path = save_path.with_suffix(".meta.json")
    _write_metadata(meta_path, meta)

    # 3) latest リンク
    _symlink_latest(save_path)

    return save_path

def read_metadata(path: Path) -> Dict[str, Any]:
    """
    メタを読む。path は .zip でも .meta.json でも可。
    """
    p = Path(path)
    if p.suffix == ".zip":
        p = p.with_suffix(".meta.json")
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)

def assert_obs_dim_compatible(path: Path, required_obs_dim: int) -> None:
    """
    ロード前の互換チェック。obs_dim が一致しなければ ValueError。
    """
    meta = read_metadata(path)
    have = int(meta.get("obs_dim", -1))
    if have != int(required_obs_dim):
        raise ValueError(
            f"Model obs_dim mismatch: required {required_obs_dim}, but model has {have} "
            f"({path})"
        )
