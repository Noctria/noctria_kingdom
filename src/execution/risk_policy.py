# =========================
# File: src/execution/risk_policy.py
# =========================
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Any, Dict

try:
    import yaml  # type: ignore
except Exception:
    yaml = None  # YAML が無くてもデフォルトで動作

@dataclass
class RiskPolicy:
    max_order_qty: float = 1000.0          # これを超えたら clamp
    severity_overflow: str = "LOW"         # clamp した時の ALERT severity

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RiskPolicy":
        return cls(
            max_order_qty=float(d.get("max_order_qty", 1000.0)),
            severity_overflow=str(d.get("severity_overflow", "LOW")),
        )

def load_policy(path: Optional[str] = None) -> RiskPolicy:
    """
    YAML が無ければデフォルトで返す。
    例 YAML:
      max_order_qty: 2000
      severity_overflow: MEDIUM
    """
    if not path:
        return RiskPolicy()
    p = Path(path)
    if not p.exists():
        return RiskPolicy()
    if yaml is None:
        return RiskPolicy()  # PyYAML 未導入でも動かす
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # ネスト無（シンプル）を想定。必要なら data.get("risk", {}) などに拡張
    return RiskPolicy.from_dict(data)
