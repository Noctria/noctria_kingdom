# src/plan_data/profile_loader.py
from __future__ import annotations

from typing import Optional
import pathlib, yaml
from .decision_engine import DecisionEngineConfig

def load_engine_config(path: str | pathlib.Path = "configs/profiles.yaml") -> DecisionEngineConfig:
    p = pathlib.Path(path)
    if not p.exists():
        # ファイルが無くても動く安全策（デフォルト値で起動）
        return DecisionEngineConfig.default()
    with open(p, "r", encoding="utf-8") as f:
        y = yaml.safe_load(f) or {}
    dflt = y.get("default", {}) or {}
    cfg = DecisionEngineConfig(
        weights=y.get("weights", {}) or {},
        rollout_percent=int(dflt.get("rollout_percent", 100)),
        min_confidence=float(dflt.get("min_confidence", 0.35)),
        combine=str(dflt.get("combine", "best_one")),
        alpha_risk=float(dflt.get("alpha_risk", 0.30)),
    )
    return cfg.normalized()
