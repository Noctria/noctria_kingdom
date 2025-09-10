# -*- coding: utf-8 -*-
"""
PDCA Agent: 本番戦略の recheck / adopt 自動化
- 既定は DRYRUN。環境変数で切替:
    PDCA_DRYRUN=true|false
    PDCA_AUTO_ADOPT=true|false
    PDCA_MIN_LIFT=0.0
- やること:
  1) 最新 decision/metrics を取得（既存スクリプト or 既知パス）
  2) しきい値に基づいて採用可否を判断
  3) adopt 方針: 自動PR or 直接 push + tag（AUTO_ADOPT=true かつ DRYRUN=false）
"""

from __future__ import annotations
import os, json, subprocess, sys, datetime, pathlib, textwrap

REPO = pathlib.Path(__file__).resolve().parents[1]
DRYRUN = os.getenv("PDCA_DRYRUN", "true").lower() == "true"
AUTO_ADOPT = os.getenv("PDCA_AUTO_ADOPT", "false").lower() == "true"
MIN_LIFT = float(os.getenv("PDCA_MIN_LIFT", "0.0"))
REQUIRE_TESTS = os.getenv("PDCA_REQUIRE_TESTS", "true").lower() == "true"

# 1) 最新の decision を取得（既存の show_last_inventor_decision を活用）
def load_latest_decision() -> dict | None:
    py = sys.executable or "python3"
    cmd = [py, "-m", "scripts.show_last_inventor_decision", "--json"]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True, timeout=15).strip()
        if out:
            data = json.loads(out)
            if isinstance(data, dict) and "decision" in data and isinstance(data["decision"], dict):
                return data["decision"]
            return data
    except Exception as e:
        print(f"::warning:: failed to load decision via script: {e}")
    # 代替: 既知の成果物パス
    for p in [
        REPO / "codex_reports/latest_inventor_decision.json",
        REPO / "reports/latest_inventor_decision.json",
        REPO / "airflow_docker/codex_reports/inventor_last.json",
    ]:
        try:
            if p.is_file():
                return json.loads(p.read_text(encoding="utf-8")).get("decision")
        except Exception as e:
            print(f"::warning:: failed to read {p}: {e}")
    return None

# 2) 指標（例: lift/size/score）で採用判定を行うダミー基準
def should_adopt(decision: dict) -> tuple[bool, str]:
    # ここは本番ロジックに差し替え可。最低限の安全弁だけ入れる
    size = float(decision.get("size", 0) or 0)
    reason = str(decision.get("reason") or "")
    lift = float(decision.get("lift", 0) or 0)

    if REQUIRE_TESTS and reason == "fallback:size" and size <= 0:
        return False, "fallback size invalid"

    if lift < MIN_LIFT:
        return False, f"lift {lift} < min {MIN_LIFT}"

    return True, f"ok: lift {lift}, size {size}, reason {reason}"

# 3) 採用に向けた変更を生成（PR方式が基本。強制採用は branch 直 push + tag）
def ensure_git_config():
    subprocess.run(["git", "config", "user.name", "noctria-bot"], check=False)
    subprocess.run(["git", "config", "user.email", "noctria-bot@example.com"], check=False)

def create_adopt_branch_and_commit(decision: dict) -> tuple[str, list[str]]:
    ts = datetime.datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    branch = f"auto/adopt-{ts}"
    subprocess.check_call(["git", "checkout", "-b", branch])

    # 例: decision_registry に追記（なければ生成）
    reg = REPO / "codex_reports" / "decision_registry.jsonl"
    reg.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps({"ts": ts, "decision": decision}, ensure_ascii=False)
    old = reg.read_text("utf-8").splitlines() if reg.exists() else []
    old.append(line)
    reg.write_text("\n".join(old) + "\n", encoding="utf-8")

    subprocess.check_call(["git", "add", str(reg)])
    msg = f"feat(pdca): adopt decision at {ts}"
    subprocess.check_call(["git", "commit", "-m", msg])
    return branch, [str(reg)]

def open_pr(branch: str, title: str, body: str):
    # gh CLI が runner には入っている。なければ fallback で push のみ。
    try:
        subprocess.check_call(["git", "push", "-u", "origin", branch])
        subprocess.check_call([
            "gh", "pr", "create",
            "--title", title,
            "--body", body,
            "--base", "main",
            "--head", branch
        ])
        print("::notice:: opened PR:", title)
    except Exception as e:
        print(f"::warning:: failed to open PR via gh: {e}\nPushing branch only.")
        subprocess.run(["git", "push", "-u", "origin", branch], check=False)

def merge_and_tag(branch: str, decision: dict):
    # 危険操作: AUTO_ADOPT=true かつ DRYRUN=false のときのみ
    subprocess.check_call(["git", "push", "-u", "origin", branch])
    # マージは GitHub API/gh で実行（squash）
    try:
        title = f"auto(adopt): {decision.get('intent','strategy')}"
        subprocess.check_call(["gh", "pr", "create", "--title", title, "--body", "auto adopt", "--base", "main", "--head", branch])
        subprocess.check_call(["gh", "pr", "merge", "--squash", "--delete-branch", "--auto"])
    except Exception as e:
        print(f"::warning:: gh pr merge failed: {e}. Trying direct fast-forward.")
        # 直 push (保護があると失敗する想定)
        subprocess.check_call(["git", "checkout", "main"])
        subprocess.check_call(["git", "pull", "--ff-only"])
        subprocess.check_call(["git", "merge", "--ff-only", branch])
        subprocess.check_call(["git", "push"])

    # タグ付け
    tag = f"adopted/{decision.get('intent','strategy','unknown')}-{datetime.datetime.utcnow().strftime('%Y%m%d')}"
    subprocess.check_call(["git", "tag", "-a", tag, "-m", "adopted-by-pdca-agent"])
    subprocess.check_call(["git", "push", "origin", tag])
    print("::notice:: tagged", tag)

def main():
    ensure_git_config()
    decision = load_latest_decision()
    if not decision:
        print("::notice:: no decision found; exiting successfully.")
        return

    ok, why = should_adopt(decision)
    print(f"::notice:: adopt decision? {ok} ({why})")

    if not ok:
        print("::notice:: not adopting (criteria unmet).")
        return

    if DRYRUN and not AUTO_ADOPT:
        print("::notice:: DRYRUN=on; reporting only.")
        print(json.dumps({"decision": decision, "why": why}, ensure_ascii=False, indent=2))
        return

    # 変更を生成して PR or 直接採用
    branch, files = create_adopt_branch_and_commit(decision)
    title = f"PDCA adopt: {decision.get('intent','strategy')} ({why})"
    body = textwrap.dedent(f"""
    This PR was created by PDCA agent.

    - decision: `{json.dumps(decision, ensure_ascii=False)}`
    - reason: {why}
    - files: {files}

    Merge policy:
    - CI must be green
    - Optional manual review (branch protection)
    """)

    if AUTO_ADOPT and not DRYRUN:
        merge_and_tag(branch, decision)
    else:
        open_pr(branch, title, body)

if __name__ == "__main__":
    main()
