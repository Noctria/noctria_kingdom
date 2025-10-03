from __future__ import annotations

import glob
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.core.path_config import GOALS_DIR

try:
    import yaml  # pyyaml
except Exception:  # pragma: no cover
    yaml = None


@dataclass
class GoalDoc:
    file: str
    north_star: str
    agent: str
    scope: Dict[str, Any] = field(default_factory=dict)
    success_metrics: List[Dict[str, Any]] = field(default_factory=list)
    reward_rules: Dict[str, float] = field(default_factory=dict)
    guardrails: List[str] = field(default_factory=list)
    outputs: List[Dict[str, str]] = field(default_factory=list)
    handoff: Dict[str, Any] = field(default_factory=dict)
    decision_policy: Dict[str, Any] = field(default_factory=dict)


def _load_yaml(path: str) -> Dict[str, Any]:
    if not yaml:
        raise RuntimeError("PyYAMLが必要です: pip install pyyaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_goals(goal_dir: Optional[str] = None) -> Dict[str, GoalDoc]:
    """
    goal_dir が未指定なら path_config.GOALS_DIR を使う。
    """
    if goal_dir is None:
        goal_dir = str(GOALS_DIR)
    goals: Dict[str, GoalDoc] = {}
    for path in sorted(glob.glob(os.path.join(goal_dir, "*.yaml"))):
        data = _load_yaml(path)
        agent = data.get("agent") or os.path.splitext(os.path.basename(path))[0]
        north_star = data.get("north_star") or ""
        if not north_star.strip():
            raise ValueError(f"{path}: north_star が空です")
        doc = GoalDoc(
            file=path,
            north_star=north_star.strip(),
            agent=agent,
            scope=data.get("scope", {}),
            success_metrics=data.get("success_metrics", []),
            reward_rules=data.get("reward_rules", {}),
            guardrails=data.get("guardrails", []),
            outputs=data.get("outputs", []),
            handoff=data.get("handoff", {}),
            decision_policy=data.get("decision_policy", {}),
        )
        goals[agent] = doc
    return goals


def as_jsonable(goals: Dict[str, GoalDoc]) -> Dict[str, Any]:
    # dataclass を json 可に
    def to_dict(g: GoalDoc):
        return {
            "file": g.file,
            "north_star": g.north_star,
            "agent": g.agent,
            "scope": g.scope,
            "success_metrics": g.success_metrics,
            "reward_rules": g.reward_rules,
            "guardrails": g.guardrails,
            "outputs": g.outputs,
            "handoff": g.handoff,
            "decision_policy": g.decision_policy,
        }

    return {k: to_dict(v) for k, v in goals.items()}
