# src/core/policy_engine.py
#!/usr/bin/env python3
# coding: utf-8
from __future__ import annotations
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any

# 環境変数で上書き可（例: WINRATE_MIN=62.5）
import os

@dataclass
class Policy:
    version: str
    winrate_min_pct: float      # 60.0 = 60%
    maxdd_max_pct: float        # 20.0 = 20%
    comment: str

def current_policy() -> Policy:
    return Policy(
        version=datetime.utcnow().strftime("v%Y.%m.%d"),
        winrate_min_pct=float(os.getenv("WINRATE_MIN", "60.0")),
        maxdd_max_pct=float(os.getenv("MAXDD_MAX", "20.0")),
        comment="Default kingdom policy thresholds",
    )

def get_snapshot() -> Dict[str, Any]:
    return asdict(current_policy())

def meets_criteria(winrate_pct: float, maxdd_pct: float) -> bool:
    p = current_policy()
    return (winrate_pct >= p.winrate_min_pct) and (maxdd_pct <= p.maxdd_max_pct)
