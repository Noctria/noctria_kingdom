# src/codex/goal_utils.py
from __future__ import annotations

from typing import Any

from src.codex.goals import load_goals


def get_goal(agent: str) -> dict:
    """Agent名で GoalDoc を dict で返す（存在しなければ空）"""
    g = load_goals().get(agent)
    return (
        {}
        if g is None
        else {
            "north_star": g.north_star,
            "scope": g.scope,
            "success_metrics": g.success_metrics,
            "reward_rules": g.reward_rules,
            "guardrails": g.guardrails,
            "outputs": g.outputs,
            "handoff": g.handoff,
            "decision_policy": g.decision_policy,
        }
    )


def scope_int(agent: str, dotted: str, default: int) -> int:
    """scope.autonomy.max_candidates_per_cycle のような値を取り出す"""
    g = get_goal(agent)
    cur: Any = g.get("scope", {})
    for k in dotted.split("."):
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return int(cur) if isinstance(cur, (int, float, str)) and str(cur).isdigit() else default
