from __future__ import annotations
import yaml, os
from typing import Dict, Any, Optional

class Policy:
    def __init__(self, d: Dict[str, Any]):
        self.d = d

    def agent_rules(self, name: str) -> Dict[str, Any]:
        return self.d["agents"][name]

    def can(self, name: str, action: str) -> bool:
        rules = self.agent_rules(name)
        if action in rules.get("forbidden_actions", []):
            return False
        return action in rules.get("allowed_actions", [])

    def constraints(self, name: str) -> Dict[str, Any]:
        return self.agent_rules(name).get("constraints", {})

    def governance(self) -> Dict[str, Any]:
        return self.d.get("governance", {})

    def version(self) -> str:
        return str(self.d.get("policy_version", "0"))

def load_policy(path: Optional[str] = None) -> Policy:
    path = path or os.getenv("NOCTRIA_POLICY_FILE", "docs/codex/codex_noctria_policy.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return Policy(yaml.safe_load(f))

POLICY = load_policy()

class GuardrailError(Exception):
    pass

def _check_governance(context: Dict[str, Any]):
    gov = POLICY.governance()
    if gov.get("observability_required") and not context.get("obs_logged", False):
        raise GuardrailError("Observability logging required")
    for rule in gov.get("block_if", []):
        metric, op, value = rule["metric"], rule["op"], rule["value"]
        x = context.get(metric)
        if x is None:
            continue
        if (op == "<" and x < value) or (op == ">" and x > value):
            raise GuardrailError(f"Blocked by governance rule: {metric} {op} {value} (actual={x})")

def enforce(agent: str, action: str, context: Dict[str, Any]):
    """
    代理AIがアクションする直前に必ず呼ぶ。
    policy違反なら GuardrailError を送出して実行を止める。
    """
    if not POLICY.can(agent, action):
        raise GuardrailError(f"{agent} is not allowed to perform {action}")

    cons = POLICY.constraints(agent)

    # アクション別チェック
    if action == "propose_patch":
        if context.get("changed_files", 0) > cons.get("max_changed_files", 1_000_000):
            raise GuardrailError("Too many changed files")
        if context.get("patch_lines", 0) > cons.get("max_patch_lines", 10_000_000):
            raise GuardrailError("Patch too large")
        if cons.get("require_tests_for_code", False) and not context.get("has_tests", False):
            raise GuardrailError("Tests required for code changes")
        reviewers = set(cons.get("require_review_by", []))
        if reviewers and not reviewers.issubset(set(context.get("requested_reviewers", []))):
            raise GuardrailError("Required reviewers not requested")

    if action == "review_patch":
        min_align = cons.get("require_alignment_score_min")
        if min_align is not None:
            if context.get("alignment_score") is None:
                raise GuardrailError("alignment_score not provided")
            if float(context["alignment_score"]) < float(min_align):
                raise GuardrailError("alignment_score below required minimum")

    # 全体ガバナンス
    _check_governance(context)
