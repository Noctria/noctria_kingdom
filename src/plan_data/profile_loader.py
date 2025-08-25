# src/plan_data/profile_loader.py
from __future__ import annotations

from typing import Optional, Mapping, Any
import os
import pathlib
import yaml

# DecisionEngineConfig は decision パッケージ配下にあります
from decision.decision_engine import DecisionEngineConfig


def _repo_root() -> pathlib.Path:
    """
    リポジトリのルートを推定（.../src/plan_data/profile_loader.py → repo_root/src/plan_data）
    """
    return pathlib.Path(__file__).resolve().parents[2]


def _default_profiles_path() -> pathlib.Path:
    """
    既定の profiles.yaml 位置: <repo_root>/configs/profiles.yaml
    """
    return _repo_root() / "configs" / "profiles.yaml"


def _normalize_cfg(cfg: DecisionEngineConfig) -> DecisionEngineConfig:
    """
    DecisionEngineConfig に normalized() があれば呼ぶ。
    （後方互換のため getattr で存在チェック）
    """
    normalizer = getattr(cfg, "normalized", None)
    return normalizer() if callable(normalizer) else cfg


def _as_float_map(m: Any) -> Mapping[str, float]:
    if not isinstance(m, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in m.items():
        try:
            out[str(k)] = float(v)
        except Exception:
            # 数値化できないものはスキップ
            continue
    return out


def load_engine_config(path: str | pathlib.Path | None = None) -> DecisionEngineConfig:
    """
    profiles.yaml を読み込んで DecisionEngineConfig を返す。
    - path が None の場合は <repo_root>/configs/profiles.yaml を探す
    - ファイルが無ければ DecisionEngineConfig.default() で安全にフォールバック
    - 不正な値は可能な限り丸めて読み込む
    """
    p = pathlib.Path(path) if path is not None else _default_profiles_path()

    if not p.exists():
        # ファイル無しでも起動可能に
        return _normalize_cfg(DecisionEngineConfig.default())

    with open(p, "r", encoding="utf-8") as f:
        y = yaml.safe_load(f) or {}

    default_section = y.get("default", {}) or {}
    weights = _as_float_map(y.get("weights", {}) or {})

    cfg = DecisionEngineConfig(
        weights=weights,
        rollout_percent=int(default_section.get("rollout_percent", 100)),
        min_confidence=float(default_section.get("min_confidence", 0.35)),
        combine=str(default_section.get("combine", "best_one")),
        alpha_risk=float(default_section.get("alpha_risk", 0.30)),
    )
    return _normalize_cfg(cfg)


__all__ = ["load_engine_config"]
