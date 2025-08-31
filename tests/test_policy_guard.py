import os
os.environ["NOCTRIA_POLICY_FILE"] = "docs/codex/codex_noctria_policy.yaml"

from agents.guardrails.policy_guard import enforce, GuardrailError, load_policy

def test_inventor_can_propose_patch_basic():
    policy = load_policy()
    ctx = {
        "changed_files": 2,
        "patch_lines": 120,
        "has_tests": True,
        "requested_reviewers": ["harmonia_ordinis"],
        "obs_logged": True,
        "roadmap_alignment": 0.9,
        "failing_tests": 0,
    }
    enforce("inventor_scriptus", "propose_patch", ctx)

def test_inventor_blocked_when_no_tests():
    ctx = {
        "changed_files": 1,
        "patch_lines": 10,
        "has_tests": False,  # 必須
        "requested_reviewers": ["harmonia_ordinis"],
        "obs_logged": True,
        "roadmap_alignment": 0.9,
        "failing_tests": 0,
    }
    try:
        enforce("inventor_scriptus", "propose_patch", ctx)
        assert False, "should raise GuardrailError"
    except GuardrailError as e:
        assert "Tests required" in str(e)

def test_governance_alignment_boundary_blocks():
    # しきい値 0.75 を 0.74 で割り込む境界
    ctx = {
        "changed_files": 1,
        "patch_lines": 10,
        "has_tests": True,
        "requested_reviewers": ["harmonia_ordinis"],
        "obs_logged": True,
        "roadmap_alignment": 0.74,  # NG
        "failing_tests": 0,
    }
    try:
        enforce("inventor_scriptus", "propose_patch", ctx)
        assert False
    except GuardrailError as e:
        assert "roadmap_alignment < 0.75" in str(e) or "Blocked by governance rule" in str(e)

def test_governance_failing_tests_blocks():
    ctx = {
        "changed_files": 1,
        "patch_lines": 10,
        "has_tests": True,
        "requested_reviewers": ["harmonia_ordinis"],
        "obs_logged": True,
        "roadmap_alignment": 0.9,
        "failing_tests": 1,  # NG
    }
    try:
        enforce("inventor_scriptus", "propose_patch", ctx)
        assert False
    except GuardrailError:
        pass

def test_harmonia_alignment_required():
    # レビュワー側の整合性スコアしきい値チェック
    ctx = {"alignment_score": 0.79, "obs_logged": True}
    try:
        enforce("harmonia_ordinis", "review_patch", ctx)
        assert False
    except GuardrailError:
        pass

def test_harmonia_alignment_ok():
    ctx = {"alignment_score": 0.81, "obs_logged": True}
    enforce("harmonia_ordinis", "review_patch", ctx)
